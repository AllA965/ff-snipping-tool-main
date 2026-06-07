"""
云存储服务集成模块
支持百度云、阿里云、OneDrive等
"""
import os
import sys
import json
import webbrowser
import threading
import http.server
import urllib.parse
from typing import Optional, Dict, Tuple, List, Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPixmap


class CloudProvider(Enum):
    """云存储提供商"""
    BAIDU = "baidu"
    ALIYUN = "aliyun"
    ONEDRIVE = "onedrive"
    GOOGLE_DRIVE = "google_drive"
    DROPBOX = "dropbox"


@dataclass
class CloudConfig:
    """云存储配置"""
    provider: CloudProvider
    client_id: str
    client_secret: str = ""
    redirect_uri: str = "http://localhost:8765/callback"
    scope: str = ""


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    """OAuth回调处理器"""
    
    auth_code = None
    
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        
        if 'code' in params:
            OAuthCallbackHandler.auth_code = params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            response = """
            <html><head><meta charset="utf-8"></head>
            <body style="font-family: Arial; text-align: center; padding-top: 50px;">
            <h2>✓ 授权成功</h2>
            <p>您可以关闭此窗口并返回应用程序</p>
            <script>setTimeout(function(){window.close();}, 2000);</script>
            </body></html>
            """
            self.wfile.write(response.encode('utf-8'))
        else:
            self.send_response(400)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # 禁用日志


class CloudStorageBase(QObject):
    """云存储基类"""
    
    auth_completed = Signal(bool, str)  # 成功/失败, 消息
    upload_progress = Signal(int, int)  # 已上传, 总大小
    upload_completed = Signal(bool, str)  # 成功/失败, 消息/URL
    
    def __init__(self, config: CloudConfig):
        super().__init__()
        self.config = config
        self.access_token = None
        self.refresh_token = None
        self.token_expires = 0
    
    def start_oauth(self):
        """启动OAuth授权流程"""
        raise NotImplementedError
    
    def refresh_access_token(self) -> bool:
        """刷新访问令牌"""
        raise NotImplementedError
    
    def upload_file(self, file_path: str, remote_path: str = "/"):
        """上传文件"""
        raise NotImplementedError
    
    def upload_pixmap(self, pixmap: QPixmap, filename: str, remote_path: str = "/"):
        """上传QPixmap图像"""
        import tempfile
        temp_file = tempfile.mktemp(suffix='.png')
        pixmap.save(temp_file, "PNG")
        self.upload_file(temp_file, os.path.join(remote_path, filename))
    
    def list_files(self, path: str = "/") -> List[Dict]:
        """列出文件"""
        raise NotImplementedError
    
    def set_tokens(self, access_token: str, refresh_token: str = None, expires: int = 0):
        """设置令牌"""
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expires = expires


class OneDriveStorage(CloudStorageBase):
    """OneDrive云存储"""
    
    AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    API_URL = "https://graph.microsoft.com/v1.0"
    
    def __init__(self, client_id: str = ""):
        config = CloudConfig(
            provider=CloudProvider.ONEDRIVE,
            client_id=client_id or "YOUR_CLIENT_ID",
            scope="files.readwrite offline_access"
        )
        super().__init__(config)
    
    def start_oauth(self):
        """启动OAuth授权"""
        params = {
            'client_id': self.config.client_id,
            'response_type': 'code',
            'redirect_uri': self.config.redirect_uri,
            'scope': self.config.scope,
            'response_mode': 'query'
        }
        
        auth_url = f"{self.AUTH_URL}?{urllib.parse.urlencode(params)}"
        
        # 启动本地服务器接收回调
        def run_server():
            server = http.server.HTTPServer(('localhost', 8765), OAuthCallbackHandler)
            server.handle_request()
            
            if OAuthCallbackHandler.auth_code:
                self._exchange_code(OAuthCallbackHandler.auth_code)
        
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        
        # 打开浏览器
        webbrowser.open(auth_url)
    
    def _exchange_code(self, code: str):
        """交换授权码获取令牌"""
        try:
            import requests
            
            data = {
                'client_id': self.config.client_id,
                'code': code,
                'redirect_uri': self.config.redirect_uri,
                'grant_type': 'authorization_code'
            }
            
            response = requests.post(self.TOKEN_URL, data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                self.token_expires = token_data.get('expires_in', 3600)
                self.auth_completed.emit(True, "授权成功")
            else:
                self.auth_completed.emit(False, f"授权失败: {response.text}")
                
        except Exception as e:
            self.auth_completed.emit(False, f"授权失败: {str(e)}")
    
    def refresh_access_token(self) -> bool:
        """刷新访问令牌"""
        if not self.refresh_token:
            return False
        
        try:
            import requests
            
            data = {
                'client_id': self.config.client_id,
                'refresh_token': self.refresh_token,
                'grant_type': 'refresh_token'
            }
            
            response = requests.post(self.TOKEN_URL, data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token', self.refresh_token)
                return True
                
        except Exception:
            pass
        
        return False
    
    def upload_file(self, file_path: str, remote_path: str = "/"):
        """上传文件到OneDrive"""
        def do_upload():
            try:
                import requests
                
                if not self.access_token:
                    self.upload_completed.emit(False, "未授权")
                    return
                
                filename = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                
                headers = {
                    'Authorization': f'Bearer {self.access_token}',
                    'Content-Type': 'application/octet-stream'
                }
                
                # 小文件直接上传
                if file_size < 4 * 1024 * 1024:  # 4MB
                    upload_url = f"{self.API_URL}/me/drive/root:{remote_path}/{filename}:/content"
                    
                    with open(file_path, 'rb') as f:
                        response = requests.put(upload_url, headers=headers, data=f)
                    
                    if response.status_code in [200, 201]:
                        result = response.json()
                        web_url = result.get('webUrl', '')
                        self.upload_completed.emit(True, web_url)
                    else:
                        self.upload_completed.emit(False, f"上传失败: {response.text}")
                else:
                    # 大文件使用分片上传
                    self._upload_large_file(file_path, remote_path, filename)
                    
            except Exception as e:
                self.upload_completed.emit(False, f"上传失败: {str(e)}")
        
        thread = threading.Thread(target=do_upload, daemon=True)
        thread.start()
    
    def _upload_large_file(self, file_path: str, remote_path: str, filename: str):
        """大文件分片上传"""
        import requests
        
        file_size = os.path.getsize(file_path)
        
        # 创建上传会话
        session_url = f"{self.API_URL}/me/drive/root:{remote_path}/{filename}:/createUploadSession"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        
        response = requests.post(session_url, headers=headers, json={})
        
        if response.status_code != 200:
            self.upload_completed.emit(False, "创建上传会话失败")
            return
        
        upload_url = response.json().get('uploadUrl')
        
        # 分片上传
        chunk_size = 10 * 1024 * 1024  # 10MB
        uploaded = 0
        
        with open(file_path, 'rb') as f:
            while uploaded < file_size:
                chunk = f.read(chunk_size)
                chunk_len = len(chunk)
                
                headers = {
                    'Content-Length': str(chunk_len),
                    'Content-Range': f'bytes {uploaded}-{uploaded + chunk_len - 1}/{file_size}'
                }
                
                response = requests.put(upload_url, headers=headers, data=chunk)
                
                if response.status_code not in [200, 201, 202]:
                    self.upload_completed.emit(False, f"分片上传失败: {response.text}")
                    return
                
                uploaded += chunk_len
                self.upload_progress.emit(uploaded, file_size)
        
        self.upload_completed.emit(True, "上传成功")
    
    def list_files(self, path: str = "/") -> List[Dict]:
        """列出OneDrive文件"""
        try:
            import requests
            
            if not self.access_token:
                return []
            
            if path == "/":
                url = f"{self.API_URL}/me/drive/root/children"
            else:
                url = f"{self.API_URL}/me/drive/root:{path}:/children"
            
            headers = {'Authorization': f'Bearer {self.access_token}'}
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                items = response.json().get('value', [])
                return [{
                    'name': item['name'],
                    'is_dir': 'folder' in item,
                    'size': item.get('size', 0),
                    'id': item['id']
                } for item in items]
                
        except Exception:
            pass
        
        return []


class BaiduPanStorage(CloudStorageBase):
    """百度网盘存储"""
    
    AUTH_URL = "https://openapi.baidu.com/oauth/2.0/authorize"
    TOKEN_URL = "https://openapi.baidu.com/oauth/2.0/token"
    API_URL = "https://pan.baidu.com/rest/2.0"
    
    def __init__(self, client_id: str = "", client_secret: str = ""):
        config = CloudConfig(
            provider=CloudProvider.BAIDU,
            client_id=client_id or "YOUR_CLIENT_ID",
            client_secret=client_secret or "YOUR_CLIENT_SECRET",
            scope="basic,netdisk"
        )
        super().__init__(config)
    
    def start_oauth(self):
        """启动OAuth授权"""
        params = {
            'response_type': 'code',
            'client_id': self.config.client_id,
            'redirect_uri': self.config.redirect_uri,
            'scope': self.config.scope,
            'display': 'popup'
        }
        
        auth_url = f"{self.AUTH_URL}?{urllib.parse.urlencode(params)}"
        
        def run_server():
            server = http.server.HTTPServer(('localhost', 8765), OAuthCallbackHandler)
            server.handle_request()
            
            if OAuthCallbackHandler.auth_code:
                self._exchange_code(OAuthCallbackHandler.auth_code)
        
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        
        webbrowser.open(auth_url)
    
    def _exchange_code(self, code: str):
        """交换授权码"""
        try:
            import requests
            
            params = {
                'grant_type': 'authorization_code',
                'code': code,
                'client_id': self.config.client_id,
                'client_secret': self.config.client_secret,
                'redirect_uri': self.config.redirect_uri
            }
            
            response = requests.get(self.TOKEN_URL, params=params)
            
            if response.status_code == 200:
                token_data = response.json()
                if 'access_token' in token_data:
                    self.access_token = token_data['access_token']
                    self.refresh_token = token_data.get('refresh_token')
                    self.auth_completed.emit(True, "授权成功")
                else:
                    self.auth_completed.emit(False, token_data.get('error_description', '授权失败'))
            else:
                self.auth_completed.emit(False, f"授权失败: {response.text}")
                
        except Exception as e:
            self.auth_completed.emit(False, f"授权失败: {str(e)}")
    
    def upload_file(self, file_path: str, remote_path: str = "/apps/PyScreenshot"):
        """上传文件到百度网盘"""
        def do_upload():
            try:
                import requests
                import hashlib
                
                if not self.access_token:
                    self.upload_completed.emit(False, "未授权")
                    return
                
                filename = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                
                # 计算MD5
                with open(file_path, 'rb') as f:
                    content_md5 = hashlib.md5(f.read()).hexdigest()
                
                # 预上传
                precreate_url = f"{self.API_URL}/xpan/file"
                params = {
                    'method': 'precreate',
                    'access_token': self.access_token
                }
                data = {
                    'path': f"{remote_path}/{filename}",
                    'size': file_size,
                    'isdir': 0,
                    'autoinit': 1,
                    'block_list': json.dumps([content_md5])
                }
                
                response = requests.post(precreate_url, params=params, data=data)
                result = response.json()
                
                if result.get('errno') != 0:
                    self.upload_completed.emit(False, f"预上传失败: {result}")
                    return
                
                upload_id = result.get('uploadid')
                
                # 分片上传
                upload_url = "https://d.pcs.baidu.com/rest/2.0/pcs/superfile2"
                params = {
                    'method': 'upload',
                    'access_token': self.access_token,
                    'type': 'tmpfile',
                    'path': f"{remote_path}/{filename}",
                    'uploadid': upload_id,
                    'partseq': 0
                }
                
                with open(file_path, 'rb') as f:
                    files = {'file': f}
                    response = requests.post(upload_url, params=params, files=files)
                
                # 创建文件
                create_url = f"{self.API_URL}/xpan/file"
                params = {
                    'method': 'create',
                    'access_token': self.access_token
                }
                data = {
                    'path': f"{remote_path}/{filename}",
                    'size': file_size,
                    'isdir': 0,
                    'uploadid': upload_id,
                    'block_list': json.dumps([content_md5])
                }
                
                response = requests.post(create_url, params=params, data=data)
                result = response.json()
                
                if result.get('errno') == 0:
                    self.upload_completed.emit(True, f"上传成功: {remote_path}/{filename}")
                else:
                    self.upload_completed.emit(False, f"创建文件失败: {result}")
                    
            except Exception as e:
                self.upload_completed.emit(False, f"上传失败: {str(e)}")
        
        thread = threading.Thread(target=do_upload, daemon=True)
        thread.start()
    
    def list_files(self, path: str = "/apps/PyScreenshot") -> List[Dict]:
        """列出百度网盘文件"""
        try:
            import requests
            
            if not self.access_token:
                return []
            
            url = f"{self.API_URL}/xpan/file"
            params = {
                'method': 'list',
                'access_token': self.access_token,
                'dir': path
            }
            
            response = requests.get(url, params=params)
            result = response.json()
            
            if result.get('errno') == 0:
                return [{
                    'name': item['server_filename'],
                    'is_dir': item['isdir'] == 1,
                    'size': item.get('size', 0),
                    'path': item['path']
                } for item in result.get('list', [])]
                
        except Exception:
            pass
        
        return []


class CloudStorageManager(QObject):
    """云存储管理器"""
    
    def __init__(self):
        super().__init__()
        self._providers: Dict[CloudProvider, CloudStorageBase] = {}
    
    def get_provider(self, provider: CloudProvider) -> Optional[CloudStorageBase]:
        """获取云存储提供商实例"""
        if provider not in self._providers:
            if provider == CloudProvider.ONEDRIVE:
                self._providers[provider] = OneDriveStorage()
            elif provider == CloudProvider.BAIDU:
                self._providers[provider] = BaiduPanStorage()
            # 可以添加更多提供商
        
        return self._providers.get(provider)
    
    def is_authorized(self, provider: CloudProvider) -> bool:
        """检查是否已授权"""
        p = self._providers.get(provider)
        return p is not None and p.access_token is not None


# 全局实例
_cloud_manager = None

def get_cloud_manager() -> CloudStorageManager:
    """获取云存储管理器单例"""
    global _cloud_manager
    if _cloud_manager is None:
        _cloud_manager = CloudStorageManager()
    return _cloud_manager
