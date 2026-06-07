"""
社交分享模块
支持微信、QQ、钉钉、企业微信等
"""
import os
import sys
import subprocess
import tempfile
import webbrowser
from typing import Optional, Tuple, Dict
from datetime import datetime
from pathlib import Path
from PySide6.QtGui import QPixmap, QClipboard, QImage
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal
from core.i18n import tr


class SocialShareManager(QObject):
    """社交分享管理器"""
    
    share_completed = Signal(bool, str)  # 成功/失败, 消息
    
    def __init__(self):
        super().__init__()
        self._clipboard_history = []
        self._max_history = 20
    
    # ========== 客户端检测 ==========
    
    @staticmethod
    def detect_installed_apps() -> Dict[str, bool]:
        """检测已安装的社交应用"""
        apps = {
            'wechat': False,
            'qq': False,
            'dingtalk': False,
            'wecom': False,  # 企业微信
            'outlook': False
        }
        
        if sys.platform == 'win32':
            # Windows检测
            import winreg
            
            # 微信
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                    r"Software\Tencent\WeChat")
                apps['wechat'] = True
                winreg.CloseKey(key)
            except:
                # 检查常见安装路径
                wechat_paths = [
                    os.path.expandvars(r"%LOCALAPPDATA%\WeChat\WeChat.exe"),
                    r"C:\Program Files (x86)\Tencent\WeChat\WeChat.exe",
                    r"C:\Program Files\Tencent\WeChat\WeChat.exe"
                ]
                apps['wechat'] = any(os.path.exists(p) for p in wechat_paths)
            
            # QQ
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Tencent\QQ")
                apps['qq'] = True
                winreg.CloseKey(key)
            except:
                qq_paths = [
                    r"C:\Program Files (x86)\Tencent\QQ\Bin\QQ.exe",
                    r"C:\Program Files\Tencent\QQ\Bin\QQ.exe"
                ]
                apps['qq'] = any(os.path.exists(p) for p in qq_paths)
            
            # 钉钉
            dingtalk_paths = [
                os.path.expandvars(r"%LOCALAPPDATA%\DingTalk\DingTalk.exe"),
                r"C:\Program Files (x86)\DingTalk\DingTalk.exe"
            ]
            apps['dingtalk'] = any(os.path.exists(p) for p in dingtalk_paths)
            
            # 企业微信
            wecom_paths = [
                os.path.expandvars(r"%LOCALAPPDATA%\WXWork\WXWork.exe"),
                r"C:\Program Files (x86)\WXWork\WXWork.exe"
            ]
            apps['wecom'] = any(os.path.exists(p) for p in wecom_paths)
            
            # Outlook
            outlook_paths = [
                r"C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE",
                r"C:\Program Files (x86)\Microsoft Office\root\Office16\OUTLOOK.EXE"
            ]
            apps['outlook'] = any(os.path.exists(p) for p in outlook_paths)
        
        elif sys.platform == 'darwin':
            # macOS检测
            apps['wechat'] = os.path.exists("/Applications/WeChat.app")
            apps['qq'] = os.path.exists("/Applications/QQ.app")
            apps['dingtalk'] = os.path.exists("/Applications/DingTalk.app")
            apps['wecom'] = os.path.exists("/Applications/企业微信.app")
            apps['outlook'] = os.path.exists("/Applications/Microsoft Outlook.app")
        
        return apps
    
    # ========== 邮件分享 ==========
    
    def share_via_email(self, pixmap: QPixmap, subject: str = None) -> Tuple[bool, str]:
        """通过邮件分享"""
        try:
            # 保存临时图片
            temp_file = tempfile.mktemp(suffix='.png')
            pixmap.save(temp_file, "PNG")
            
            # 生成主题
            if not subject:
                date_str = datetime.now().strftime("%Y-%m-%d")
                subject = f"分享内容-{date_str}"
            
            if sys.platform == 'win32':
                # Windows: 使用MAPI或mailto
                try:
                    import win32com.client
                    outlook = win32com.client.Dispatch("Outlook.Application")
                    mail = outlook.CreateItem(0)
                    mail.Subject = subject
                    mail.Body = tr("请查看附件中的截图内容。")
                    mail.Attachments.Add(temp_file)
                    mail.Display()
                    return True, tr("已打开邮件客户端")
                except:
                    # 回退到mailto
                    import urllib.parse
                    mailto_url = f"mailto:?subject={urllib.parse.quote(subject)}"
                    webbrowser.open(mailto_url)
                    return True, tr("已打开邮件客户端，请手动添加附件: {temp_file}").format(temp_file=temp_file)
            
            elif sys.platform == 'darwin':
                # macOS: 使用AppleScript
                body_text = tr("请查看附件中的截图内容。")
                script = f'''
                tell application "Mail"
                    set newMessage to make new outgoing message with properties {{subject:"{subject}", content:"{body_text}"}}
                    tell newMessage
                        make new attachment with properties {{file name:POSIX file "{temp_file}"}}
                    end tell
                    activate
                end tell
                '''
                subprocess.run(['osascript', '-e', script])
                return True, "已打开邮件客户端"
            
            else:
                # Linux: 使用xdg-email
                subprocess.run(['xdg-email', '--subject', subject, '--attach', temp_file])
                return True, "已打开邮件客户端"
                
        except Exception as e:
            return False, f"打开邮件客户端失败: {str(e)}"
    
    # ========== 微信分享 ==========
    
    def share_to_wechat(self, pixmap: QPixmap) -> Tuple[bool, str]:
        """分享到微信"""
        try:
            # 复制图片到剪贴板
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(pixmap)
            
            # 打开微信
            if sys.platform == 'win32':
                wechat_paths = [
                    os.path.expandvars(r"%LOCALAPPDATA%\WeChat\WeChat.exe"),
                    r"C:\Program Files (x86)\Tencent\WeChat\WeChat.exe",
                    r"C:\Program Files\Tencent\WeChat\WeChat.exe"
                ]
                for path in wechat_paths:
                    if os.path.exists(path):
                        subprocess.Popen([path])
                        return True, "已复制到剪贴板并打开微信，请在聊天窗口中粘贴(Ctrl+V)"
            
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', '-a', 'WeChat'])
                return True, "已复制到剪贴板并打开微信，请在聊天窗口中粘贴(Cmd+V)"
            
            return True, tr("已复制到剪贴板，请手动打开微信并粘贴")
            
        except Exception as e:
            return False, f"分享失败: {str(e)}"
    
    # ========== QQ分享 ==========
    
    def share_to_qq(self, pixmap: QPixmap) -> Tuple[bool, str]:
        """分享到QQ"""
        try:
            # 复制图片到剪贴板
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(pixmap)
            
            # 打开QQ
            if sys.platform == 'win32':
                qq_paths = [
                    r"C:\Program Files (x86)\Tencent\QQ\Bin\QQ.exe",
                    r"C:\Program Files\Tencent\QQ\Bin\QQ.exe"
                ]
                for path in qq_paths:
                    if os.path.exists(path):
                        subprocess.Popen([path])
                        return True, "已复制到剪贴板并打开QQ，请在聊天窗口中粘贴(Ctrl+V)"
            
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', '-a', 'QQ'])
                return True, "已复制到剪贴板并打开QQ，请在聊天窗口中粘贴(Cmd+V)"
            
            return True, "已复制到剪贴板，请手动打开QQ并粘贴"
            
        except Exception as e:
            return False, f"分享失败: {str(e)}"
    
    # ========== 钉钉分享 ==========
    
    def share_to_dingtalk(self, pixmap: QPixmap) -> Tuple[bool, str]:
        """分享到钉钉"""
        try:
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(pixmap)
            
            if sys.platform == 'win32':
                dingtalk_paths = [
                    os.path.expandvars(r"%LOCALAPPDATA%\DingTalk\DingTalk.exe"),
                    r"C:\Program Files (x86)\DingTalk\DingTalk.exe"
                ]
                for path in dingtalk_paths:
                    if os.path.exists(path):
                        subprocess.Popen([path])
                        return True, "已复制到剪贴板并打开钉钉，请在聊天窗口中粘贴"
            
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', '-a', 'DingTalk'])
                return True, "已复制到剪贴板并打开钉钉，请在聊天窗口中粘贴"
            
            return True, "已复制到剪贴板，请手动打开钉钉并粘贴"
            
        except Exception as e:
            return False, f"分享失败: {str(e)}"
    
    # ========== 企业微信分享 ==========
    
    def share_to_wecom(self, pixmap: QPixmap) -> Tuple[bool, str]:
        """分享到企业微信"""
        try:
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(pixmap)
            
            if sys.platform == 'win32':
                wecom_paths = [
                    os.path.expandvars(r"%LOCALAPPDATA%\WXWork\WXWork.exe"),
                    r"C:\Program Files (x86)\WXWork\WXWork.exe"
                ]
                for path in wecom_paths:
                    if os.path.exists(path):
                        subprocess.Popen([path])
                        return True, "已复制到剪贴板并打开企业微信，请在聊天窗口中粘贴"
            
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', '-a', '企业微信'])
                return True, "已复制到剪贴板并打开企业微信，请在聊天窗口中粘贴"
            
            return True, "已复制到剪贴板，请手动打开企业微信并粘贴"
            
        except Exception as e:
            return False, f"分享失败: {str(e)}"
    
    # ========== 剪贴板功能 ==========
    
    def copy_to_clipboard(self, pixmap: QPixmap) -> Tuple[bool, str]:
        """复制到剪贴板"""
        try:
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(pixmap)
            
            # 添加到历史
            self._add_to_history(pixmap)
            
            return True, "已复制到剪贴板"
        except Exception as e:
            return False, f"复制失败: {str(e)}"
    
    def _add_to_history(self, pixmap: QPixmap):
        """添加到剪贴板历史"""
        # 缩略图
        thumbnail = pixmap.scaled(100, 100)
        
        self._clipboard_history.insert(0, {
            'pixmap': pixmap,
            'thumbnail': thumbnail,
            'timestamp': datetime.now()
        })
        
        # 限制历史数量
        if len(self._clipboard_history) > self._max_history:
            self._clipboard_history = self._clipboard_history[:self._max_history]
    
    def get_clipboard_history(self) -> list:
        """获取剪贴板历史"""
        return self._clipboard_history
    
    def clear_clipboard_history(self):
        """清空剪贴板历史"""
        self._clipboard_history.clear()
    
    def paste_from_history(self, index: int) -> Optional[QPixmap]:
        """从历史中粘贴"""
        if 0 <= index < len(self._clipboard_history):
            pixmap = self._clipboard_history[index]['pixmap']
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(pixmap)
            return pixmap
        return None
    
    # ========== 网络URL分享 ==========
    
    def share_to_web_url(self, pixmap: QPixmap, upload_url: str) -> Tuple[bool, str]:
        """上传到Web服务器并获取URL"""
        try:
            import requests
            import tempfile
            
            # 保存临时文件
            temp_file = tempfile.mktemp(suffix='.png')
            pixmap.save(temp_file, "PNG")
            
            # 上传
            with open(temp_file, 'rb') as f:
                files = {'file': f}
                response = requests.post(upload_url, files=files, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                url = result.get('url', '')
                return True, url
            else:
                return False, f"上传失败: {response.status_code}"
                
        except Exception as e:
            return False, f"上传失败: {str(e)}"


# 全局实例
_social_manager = None

def get_social_manager() -> SocialShareManager:
    """获取社交分享管理器单例"""
    global _social_manager
    if _social_manager is None:
        _social_manager = SocialShareManager()
    return _social_manager
