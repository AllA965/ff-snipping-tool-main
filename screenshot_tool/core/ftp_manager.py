"""
FTP上传管理模块
支持断点续传、进度显示、多服务器配置
"""
import os
import ftplib
import ssl
import threading
from pathlib import Path
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass
from enum import Enum
from PySide6.QtCore import QObject, Signal


class FTPProtocol(Enum):
    """FTP协议类型"""
    FTP = "ftp"
    FTPS = "ftps"  # FTP over SSL/TLS
    SFTP = "sftp"


@dataclass
class FTPServerConfig:
    """FTP服务器配置"""
    name: str
    host: str
    port: int = 21
    username: str = ""
    password: str = ""
    path: str = "/"
    protocol: FTPProtocol = FTPProtocol.FTP
    passive: bool = True
    timeout: int = 30


class FTPUploadTask(QObject):
    """FTP上传任务"""
    
    progress_updated = Signal(int, int)  # 已上传, 总大小
    status_changed = Signal(str)  # 状态消息
    completed = Signal(bool, str)  # 成功/失败, 消息
    
    def __init__(self, server_config: FTPServerConfig, local_file: str, 
                 remote_path: str = None):
        super().__init__()
        self.server_config = server_config
        self.local_file = local_file
        self.remote_path = remote_path or server_config.path
        self.cancelled = False
        self._ftp = None
        self._uploaded_bytes = 0
        self._total_bytes = 0
    
    def cancel(self):
        """取消上传"""
        self.cancelled = True
        if self._ftp:
            try:
                self._ftp.abort()
            except:
                pass
    
    def run(self):
        """执行上传"""
        try:
            self.status_changed.emit("正在连接服务器...")
            self._connect()
            
            if self.cancelled:
                self.completed.emit(False, "上传已取消")
                return
            
            self.status_changed.emit("正在上传文件...")
            self._upload()
            
            if not self.cancelled:
                self.completed.emit(True, "上传成功")
            
        except ftplib.error_perm as e:
            self.completed.emit(False, f"权限错误: {e}")
        except ftplib.error_temp as e:
            self.completed.emit(False, f"临时错误: {e}")
        except ConnectionRefusedError:
            self.completed.emit(False, "连接被拒绝，请检查服务器地址和端口")
        except TimeoutError:
            self.completed.emit(False, "连接超时")
        except Exception as e:
            self.completed.emit(False, f"上传失败: {str(e)}")
        finally:
            self._disconnect()
    
    def _connect(self):
        """连接FTP服务器"""
        config = self.server_config
        
        if config.protocol == FTPProtocol.FTPS:
            # 使用SSL/TLS
            context = ssl.create_default_context()
            self._ftp = ftplib.FTP_TLS(context=context)
            self._ftp.connect(config.host, config.port, timeout=config.timeout)
            self._ftp.auth()
            self._ftp.prot_p()  # 数据连接也使用加密
        else:
            self._ftp = ftplib.FTP()
            self._ftp.connect(config.host, config.port, timeout=config.timeout)
        
        # 登录
        if config.username:
            self._ftp.login(config.username, config.password)
        else:
            self._ftp.login()
        
        # 设置被动模式
        if config.passive:
            self._ftp.set_pasv(True)
        
        # 切换到目标目录
        if self.remote_path and self.remote_path != "/":
            self._ensure_remote_dir(self.remote_path)
            self._ftp.cwd(self.remote_path)
    
    def _ensure_remote_dir(self, path: str):
        """确保远程目录存在"""
        dirs = path.strip('/').split('/')
        current = ""
        for d in dirs:
            if not d:
                continue
            current += "/" + d
            try:
                self._ftp.cwd(current)
            except ftplib.error_perm:
                try:
                    self._ftp.mkd(current)
                except:
                    pass
        self._ftp.cwd("/")
    
    def _upload(self):
        """执行文件上传"""
        filename = os.path.basename(self.local_file)
        self._total_bytes = os.path.getsize(self.local_file)
        self._uploaded_bytes = 0
        
        # 检查是否支持断点续传
        rest_position = 0
        try:
            # 检查远程文件大小
            remote_size = self._ftp.size(filename)
            if remote_size and remote_size < self._total_bytes:
                rest_position = remote_size
                self._uploaded_bytes = remote_size
                self.status_changed.emit(f"断点续传，从 {rest_position} 字节开始...")
        except:
            pass
        
        def callback(data):
            if self.cancelled:
                raise Exception("上传已取消")
            self._uploaded_bytes += len(data)
            self.progress_updated.emit(self._uploaded_bytes, self._total_bytes)
        
        with open(self.local_file, 'rb') as f:
            if rest_position > 0:
                f.seek(rest_position)
                self._ftp.storbinary(f'STOR {filename}', f, 8192, callback, rest_position)
            else:
                self._ftp.storbinary(f'STOR {filename}', f, 8192, callback)
    
    def _disconnect(self):
        """断开连接"""
        if self._ftp:
            try:
                self._ftp.quit()
            except:
                try:
                    self._ftp.close()
                except:
                    pass
            self._ftp = None


class FTPManager(QObject):
    """FTP管理器"""
    
    upload_started = Signal(str)  # 文件名
    upload_progress = Signal(str, int, int)  # 文件名, 已上传, 总大小
    upload_completed = Signal(str, bool, str)  # 文件名, 成功/失败, 消息
    
    def __init__(self):
        super().__init__()
        self._tasks: Dict[str, FTPUploadTask] = {}
        self._threads: Dict[str, threading.Thread] = {}
    
    def test_connection(self, config: FTPServerConfig) -> tuple:
        """测试FTP连接"""
        try:
            if config.protocol == FTPProtocol.FTPS:
                context = ssl.create_default_context()
                ftp = ftplib.FTP_TLS(context=context)
                ftp.connect(config.host, config.port, timeout=config.timeout)
                ftp.auth()
            else:
                ftp = ftplib.FTP()
                ftp.connect(config.host, config.port, timeout=config.timeout)
            
            if config.username:
                ftp.login(config.username, config.password)
            else:
                ftp.login()
            
            ftp.quit()
            return True, "连接成功"
        except ftplib.error_perm as e:
            return False, f"认证失败: {e}"
        except ConnectionRefusedError:
            return False, "连接被拒绝"
        except TimeoutError:
            return False, "连接超时"
        except Exception as e:
            return False, f"连接失败: {str(e)}"
    
    def upload_file(self, config: FTPServerConfig, local_file: str, 
                    remote_path: str = None) -> str:
        """上传文件（异步）"""
        task_id = f"{config.name}_{os.path.basename(local_file)}"
        
        task = FTPUploadTask(config, local_file, remote_path)
        task.progress_updated.connect(
            lambda uploaded, total: self.upload_progress.emit(task_id, uploaded, total)
        )
        task.completed.connect(
            lambda success, msg: self._on_task_completed(task_id, success, msg)
        )
        
        self._tasks[task_id] = task
        
        thread = threading.Thread(target=task.run, daemon=True)
        self._threads[task_id] = thread
        
        self.upload_started.emit(task_id)
        thread.start()
        
        return task_id
    
    def cancel_upload(self, task_id: str):
        """取消上传"""
        if task_id in self._tasks:
            self._tasks[task_id].cancel()
    
    def _on_task_completed(self, task_id: str, success: bool, message: str):
        """任务完成回调"""
        self.upload_completed.emit(task_id, success, message)
        
        # 清理
        if task_id in self._tasks:
            del self._tasks[task_id]
        if task_id in self._threads:
            del self._threads[task_id]
    
    def list_remote_dir(self, config: FTPServerConfig, path: str = "/") -> List[Dict]:
        """列出远程目录内容"""
        files = []
        try:
            if config.protocol == FTPProtocol.FTPS:
                context = ssl.create_default_context()
                ftp = ftplib.FTP_TLS(context=context)
                ftp.connect(config.host, config.port, timeout=config.timeout)
                ftp.auth()
                ftp.prot_p()
            else:
                ftp = ftplib.FTP()
                ftp.connect(config.host, config.port, timeout=config.timeout)
            
            if config.username:
                ftp.login(config.username, config.password)
            else:
                ftp.login()
            
            ftp.cwd(path)
            
            # 获取详细列表
            lines = []
            ftp.retrlines('LIST', lines.append)
            
            for line in lines:
                parts = line.split(None, 8)
                if len(parts) >= 9:
                    is_dir = parts[0].startswith('d')
                    name = parts[8]
                    size = int(parts[4]) if not is_dir else 0
                    files.append({
                        'name': name,
                        'is_dir': is_dir,
                        'size': size
                    })
            
            ftp.quit()
        except Exception as e:
            print(f"列出目录失败: {e}")
        
        return files


# 全局实例
_ftp_manager = None

def get_ftp_manager() -> FTPManager:
    """获取FTP管理器单例"""
    global _ftp_manager
    if _ftp_manager is None:
        _ftp_manager = FTPManager()
    return _ftp_manager
