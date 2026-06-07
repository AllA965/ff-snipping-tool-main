"""
鲲穹AI网页同步登录核心逻辑
实现签名生成、接口调用、轮询机制及Token持久化
"""
import time
import uuid
import hmac
import hashlib
import base64
import json
import requests
import webbrowser
from typing import Optional, Dict, Any, Callable
from PySide6.QtCore import QObject, Signal, QThread, QTimer

from core.credential_manager import CredentialManager

class LoginPollingThread(QThread):
    """登录状态轮询线程"""
    token_received = Signal(str)
    error_occurred = Signal(str)
    timeout_occurred = Signal()
    cancelled = Signal()

    def __init__(self, client_nonce: str, timeout: int = 300):
        super().__init__()
        self.client_nonce = client_nonce
        self.timeout = timeout
        self._is_running = True
        self._start_time = 0

    def stop(self):
        self._is_running = False

    def run(self):
        self._start_time = time.time()
        url = "https://api-web.kunqiongai.com/user/desktop_get_token"
        
        while self._is_running:
            # 检查超时
            if time.time() - self._start_time > self.timeout:
                self.timeout_occurred.emit()
                break

            try:
                # 按照文档示例，参数放在 params (Query String) 中
                params = {
                    "client_type": "desktop",
                    "client_nonce": self.client_nonce
                }
                response = requests.post(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 1:
                        token = data.get("data", {}).get("token")
                        if token:
                            self.token_received.emit(token)
                            break
                    # 如果 code 不为 1，说明还没登录，继续轮询
                else:
                    # 接口错误但不停止，可能网络抖动
                    pass
            except Exception as e:
                # 网络异常继续尝试，直到超时
                pass

            # 轮询间隔 2 秒
            time.sleep(2)

        if not self._is_running:
            self.cancelled.emit()

class KunqiongLoginManager(QObject):
    """鲲穹AI登录管理器"""
    
    login_success = Signal(dict)  # 发送用户信息
    login_failed = Signal(str)
    logout_success = Signal()
    
    API_BASE = "https://api-web.kunqiongai.com"
    SECRET_KEY = b"7530bfb1ad6c41627b0f0620078fa5ed"

    def __init__(self, credential_manager=None):
        super().__init__()
        self.cred_manager = credential_manager or CredentialManager()
        self.polling_thread = None
        self.current_user_info = None
        
        # 初始检查本地登录
        self.check_local_login()

    def is_logged_in(self) -> bool:
        """是否已登录"""
        return self.current_user_info is not None

    def get_user_info(self) -> dict:
        """获取当前用户信息"""
        return self.current_user_info or {}

    def generate_signed_nonce(self) -> str:
        """生成带签名的临时会话ID（nonce）并进行URL安全编码"""
        # 1. 生成随机nonce
        nonce = str(uuid.uuid4()).replace("-", "")
        
        # 2. 生成时间戳
        timestamp = int(time.time())
        
        # 3. 构造待签名的字符串
        message = f"{nonce}|{timestamp}".encode("utf-8")
        
        # 4. HMAC-SHA256签名
        hmac_obj = hmac.new(self.SECRET_KEY, message, hashlib.sha256)
        signature = base64.b64encode(hmac_obj.digest()).decode("utf-8")
        
        # 5. 组合数据
        signed_nonce = {
            "nonce": nonce,
            "timestamp": timestamp,
            "signature": signature
        }
        
        # 6. URL安全编码 (JSON -> Base64 -> URL Safe)
        json_str = json.dumps(signed_nonce, separators=(",", ":"))
        url_safe_str = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
        url_safe_str = url_safe_str.replace("+", "-").replace("/", "_").rstrip("=")
        
        return url_safe_str

    def get_web_login_url(self) -> Optional[str]:
        """获取网页端登录地址"""
        url = f"{self.API_BASE}/soft_desktop/get_web_login_url"
        try:
            response = requests.post(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 1:
                    return data.get("data", {}).get("login_url")
        except Exception as e:
            print(f"获取登录URL失败: {e}")
        return None

    def get_custom_url(self) -> Optional[str]:
        """获取需求定制页面链接"""
        url = f"{self.API_BASE}/soft_desktop/get_custom_url"
        try:
            response = requests.post(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 1:
                    return data.get("data", {}).get("url")
        except Exception as e:
            print(f"获取需求定制链接失败: {e}")
        return None

    def get_feedback_url(self) -> Optional[str]:
        """获取软件问题反馈页面链接"""
        from core.config import Config
        url = f"{self.API_BASE}/soft_desktop/get_feedback_url"
        try:
            # 根据文档，请求方式为 POST，Content-Type 为 none
            response = requests.post(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 1:
                    base_url = data.get("data", {}).get("url", "")
                    if base_url:
                        # 拼接软件编号
                        return f"{base_url}{Config.SOFT_NUMBER}"
        except Exception as e:
            print(f"获取反馈链接失败: {e}")
        return None

    def start_login(self):
        """开始登录流程"""
        login_url = self.get_web_login_url()
        if not login_url:
            self.login_failed.emit("无法连接到登录服务器")
            return

        client_nonce = self.generate_signed_nonce()
        
        # 拼接登录URL
        separator = "&" if "?" in login_url else "?"
        full_login_url = f"{login_url}{separator}client_type=desktop&client_nonce={client_nonce}"

        # 唤起浏览器
        try:
            if not webbrowser.open(full_login_url):
                self.login_failed.emit("无法打开系统浏览器")
                return
        except Exception as e:
            self.login_failed.emit(f"启动浏览器失败: {e}")
            return

        # 启动轮询
        self.stop_polling()
        self.polling_thread = LoginPollingThread(client_nonce)
        self.polling_thread.token_received.connect(self._on_token_received)
        self.polling_thread.timeout_occurred.connect(lambda: self.login_failed.emit("登录超时"))
        self.polling_thread.error_occurred.connect(self.login_failed.emit)
        self.polling_thread.start()

    def stop_polling(self):
        """停止轮询"""
        if self.polling_thread and self.polling_thread.isRunning():
            self.polling_thread.stop()
            self.polling_thread.wait()
        self.polling_thread = None

    def _on_token_received(self, token: str):
        """处理获取到的 Token"""
        user_info = self.fetch_user_info(token)
        if user_info:
            # 持久化存储
            token_data = {
                "token": token,
                "user_info": user_info,
                "login_time": time.time()
            }
            self.cred_manager.save_cloud_token("kunqiong_ai", token_data)
            self.current_user_info = user_info
            self.login_success.emit(user_info)
        else:
            self.login_failed.emit("获取用户信息失败")

    def fetch_user_info(self, token: str) -> Optional[dict]:
        """获取用户信息"""
        url = f"{self.API_BASE}/soft_desktop/get_user_info"
        headers = {"token": token}
        try:
            # 接口要求 POST 且 token 放在 Header
            response = requests.post(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 1:
                    return data.get("data", {}).get("user_info")
        except Exception as e:
            print(f"获取用户信息异常: {e}")
        return None

    def check_local_login(self) -> Optional[dict]:
        """检查本地存储的登录状态"""
        token_data = self.cred_manager.get_cloud_token("kunqiong_ai")
        if token_data and "token" in token_data:
            token = token_data["token"]
            
            # 按照文档规范，应先调用 check_login 接口
            if self._verify_token_online(token):
                # 验证通过后，再获取用户信息（如果本地没存或者想更新）
                user_info = self.fetch_user_info(token)
                if user_info:
                    self.current_user_info = user_info
                    return user_info
            
            # 验证失败或获取信息失败，清理
            self.cred_manager.delete_cloud_token("kunqiong_ai")
        return None

    def _verify_token_online(self, token: str) -> bool:
        """调用接口验证 token 是否有效"""
        url = f"{self.API_BASE}/user/check_login"
        data = {"token": token}
        try:
            # Content-Type: urlencoded, Body 传参
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("code") == 1
        except Exception as e:
            print(f"验证Token异常: {e}")
        return False

    def logout(self):
        """退出登录"""
        token_data = self.cred_manager.get_cloud_token("kunqiong_ai")
        if token_data and "token" in token_data:
            token = token_data["token"]
            url = f"{self.API_BASE}/logout"
            headers = {"token": token}
            try:
                # Header 传参
                requests.post(url, headers=headers, timeout=10)
            except:
                pass
        
        # 无论接口是否成功，都清理本地
        self.cred_manager.delete_cloud_token("kunqiong_ai")
        self.current_user_info = None
        self.logout_success.emit()
