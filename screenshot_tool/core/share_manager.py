"""
分享管理核心模块
统一管理所有分享功能
"""
import os
import json
import logging
from typing import Optional, Dict, List, Callable
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPixmap

from core.credential_manager import get_credential_manager
from core.ftp_manager import get_ftp_manager, FTPServerConfig, FTPProtocol
from core.office_export import OfficeExporter
from core.cloud_storage import get_cloud_manager, CloudProvider
from core.social_share import get_social_manager


class ShareType(Enum):
    """分享类型"""
    # 本地程序
    OFFICE_WORD = "office_word"
    OFFICE_EXCEL = "office_excel"
    OFFICE_POWERPOINT = "office_powerpoint"
    PAINT = "paint"
    PHOTOSHOP = "photoshop"
    GIMP = "gimp"
    
    # 网络分享
    FTP = "ftp"
    EMAIL = "email"
    WEB_URL = "web_url"
    
    # 社交分享
    WECHAT = "wechat"
    QQ = "qq"
    DINGTALK = "dingtalk"
    WECOM = "wecom"
    
    # 云存储
    ONEDRIVE = "onedrive"
    BAIDU_PAN = "baidu_pan"
    ALIYUN = "aliyun"
    GOOGLE_DRIVE = "google_drive"
    DROPBOX = "dropbox"
    
    # 剪贴板
    CLIPBOARD = "clipboard"


@dataclass
class ShareTask:
    """分享任务"""
    id: str
    share_type: ShareType
    status: str  # pending, running, completed, failed
    progress: int  # 0-100
    message: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    result_url: Optional[str] = None


class ShareLog:
    """分享日志记录"""
    
    def __init__(self):
        self.log_dir = Path.home() / ".pyscreenshot" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "share.log"
        
        # 配置日志
        self.logger = logging.getLogger("share")
        self.logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler(self.log_file, encoding='utf-8')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
    
    def log(self, level: str, log_msg: str, **kwargs):
        """记录日志"""
        extra = json.dumps(kwargs, ensure_ascii=False) if kwargs else ""
        log_message = f"{log_msg} {extra}".strip()
        
        if level == "info":
            self.logger.info(log_message)
        elif level == "error":
            self.logger.error(log_message)
        elif level == "warning":
            self.logger.warning(log_message)
        elif level == "debug":
            self.logger.debug(log_message)
    
    def get_recent_logs(self, count: int = 100) -> List[str]:
        """获取最近的日志"""
        if not self.log_file.exists():
            return []
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        return lines[-count:]


class ShareManager(QObject):
    """分享管理器"""
    
    # 信号
    task_started = Signal(str)  # task_id
    task_progress = Signal(str, int)  # task_id, progress
    task_completed = Signal(str, bool, str)  # task_id, success, message
    
    def __init__(self):
        super().__init__()
        self._tasks: Dict[str, ShareTask] = {}
        self._task_counter = 0
        
        # 子管理器
        self.credential_manager = get_credential_manager()
        self.ftp_manager = get_ftp_manager()
        self.cloud_manager = get_cloud_manager()
        self.social_manager = get_social_manager()
        
        # 日志
        self.share_log = ShareLog()
        
        # 连接FTP信号
        self.ftp_manager.upload_progress.connect(self._on_ftp_progress)
        self.ftp_manager.upload_completed.connect(self._on_ftp_completed)
    
    def _create_task(self, share_type: ShareType) -> ShareTask:
        """创建分享任务"""
        self._task_counter += 1
        task_id = f"share_{self._task_counter}_{datetime.now().strftime('%H%M%S')}"
        
        task = ShareTask(
            id=task_id,
            share_type=share_type,
            status="pending",
            progress=0,
            message="准备中...",
            created_at=datetime.now()
        )
        
        self._tasks[task_id] = task
        return task
    
    def _update_task(self, task_id: str, status: str = None, progress: int = None,
                     message: str = None, result_url: str = None):
        """更新任务状态"""
        if task_id not in self._tasks:
            return
        
        task = self._tasks[task_id]
        
        if status:
            task.status = status
        if progress is not None:
            task.progress = progress
            self.task_progress.emit(task_id, progress)
        if message:
            task.message = message
        if result_url:
            task.result_url = result_url
        
        if status in ["completed", "failed"]:
            task.completed_at = datetime.now()
            success = status == "completed"
            self.task_completed.emit(task_id, success, message or "")
            
            # 记录日志
            self.share_log.log(
                "info" if success else "error",
                f"分享任务 {task.share_type.value}",
                status=status,
                message=message
            )
    
    # ========== Office导出 ==========
    
    def export_to_word(self, pixmap: QPixmap) -> str:
        """导出到Word"""
        task = self._create_task(ShareType.OFFICE_WORD)
        self.task_started.emit(task.id)
        
        self._update_task(task.id, status="running", message="正在导出到Word...")
        
        success, result = OfficeExporter.export_to_word(pixmap)
        
        if success:
            self._update_task(task.id, status="completed", progress=100,
                            message="已导出到Word", result_url=result)
        else:
            self._update_task(task.id, status="failed", message=result)
        
        return task.id
    
    def export_to_excel(self, pixmap: QPixmap) -> str:
        """导出到Excel"""
        task = self._create_task(ShareType.OFFICE_EXCEL)
        self.task_started.emit(task.id)
        
        self._update_task(task.id, status="running", message="正在导出到Excel...")
        
        success, result = OfficeExporter.export_to_excel(pixmap)
        
        if success:
            self._update_task(task.id, status="completed", progress=100,
                            message="已导出到Excel", result_url=result)
        else:
            self._update_task(task.id, status="failed", message=result)
        
        return task.id
    
    def export_to_powerpoint(self, pixmap: QPixmap) -> str:
        """导出到PowerPoint"""
        task = self._create_task(ShareType.OFFICE_POWERPOINT)
        self.task_started.emit(task.id)
        
        self._update_task(task.id, status="running", message="正在导出到PowerPoint...")
        
        success, result = OfficeExporter.export_to_powerpoint(pixmap)
        
        if success:
            self._update_task(task.id, status="completed", progress=100,
                            message="已导出到PowerPoint", result_url=result)
        else:
            self._update_task(task.id, status="failed", message=result)
        
        return task.id
    
    def send_to_paint(self, pixmap: QPixmap) -> str:
        """发送到画图"""
        task = self._create_task(ShareType.PAINT)
        self.task_started.emit(task.id)
        
        success, result = OfficeExporter.send_to_paint(pixmap)
        
        if success:
            self._update_task(task.id, status="completed", progress=100,
                            message="已发送到画图")
        else:
            self._update_task(task.id, status="failed", message=result)
        
        return task.id
    
    def send_to_photoshop(self, pixmap: QPixmap) -> str:
        """发送到Photoshop"""
        task = self._create_task(ShareType.PHOTOSHOP)
        self.task_started.emit(task.id)
        
        success, result = OfficeExporter.send_to_photoshop(pixmap)
        
        if success:
            self._update_task(task.id, status="completed", progress=100,
                            message="已发送到Photoshop")
        else:
            self._update_task(task.id, status="failed", message=result)
        
        return task.id
    
    def send_to_gimp(self, pixmap: QPixmap) -> str:
        """发送到GIMP"""
        task = self._create_task(ShareType.GIMP)
        self.task_started.emit(task.id)
        
        success, result = OfficeExporter.send_to_gimp(pixmap)
        
        if success:
            self._update_task(task.id, status="completed", progress=100,
                            message="已发送到GIMP")
        else:
            self._update_task(task.id, status="failed", message=result)
        
        return task.id
    
    # ========== FTP上传 ==========
    
    def upload_to_ftp(self, pixmap: QPixmap, server_name: str, 
                      filename: str = None) -> str:
        """上传到FTP服务器"""
        task = self._create_task(ShareType.FTP)
        self.task_started.emit(task.id)
        
        # 获取服务器配置
        server_config = self.credential_manager.get_ftp_server(server_name)
        if not server_config:
            self._update_task(task.id, status="failed", 
                            message=f"未找到服务器配置: {server_name}")
            return task.id
        
        # 保存临时文件
        import tempfile
        if not filename:
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        temp_file = tempfile.mktemp(suffix='.png')
        pixmap.save(temp_file, "PNG")
        
        # 创建FTP配置
        ftp_config = FTPServerConfig(
            name=server_name,
            host=server_config['host'],
            port=server_config['port'],
            username=server_config['username'],
            password=server_config['password'],
            path=server_config.get('path', '/')
        )
        
        # 存储任务ID映射
        self._ftp_task_map = getattr(self, '_ftp_task_map', {})
        ftp_task_id = self.ftp_manager.upload_file(ftp_config, temp_file)
        self._ftp_task_map[ftp_task_id] = task.id
        
        self._update_task(task.id, status="running", message="正在上传...")
        
        return task.id
    
    def _on_ftp_progress(self, ftp_task_id: str, uploaded: int, total: int):
        """FTP上传进度回调"""
        task_id = getattr(self, '_ftp_task_map', {}).get(ftp_task_id)
        if task_id:
            progress = int(uploaded / total * 100) if total > 0 else 0
            self._update_task(task_id, progress=progress,
                            message=f"上传中... {uploaded}/{total} 字节")
    
    def _on_ftp_completed(self, ftp_task_id: str, success: bool, message: str):
        """FTP上传完成回调"""
        task_id = getattr(self, '_ftp_task_map', {}).get(ftp_task_id)
        if task_id:
            if success:
                self._update_task(task_id, status="completed", progress=100,
                                message="上传成功")
            else:
                self._update_task(task_id, status="failed", message=message)
    
    # ========== 邮件分享 ==========
    
    def share_via_email(self, pixmap: QPixmap, subject: str = None) -> str:
        """通过邮件分享"""
        task = self._create_task(ShareType.EMAIL)
        self.task_started.emit(task.id)
        
        success, message = self.social_manager.share_via_email(pixmap, subject)
        
        if success:
            self._update_task(task.id, status="completed", progress=100,
                            message=message)
        else:
            self._update_task(task.id, status="failed", message=message)
        
        return task.id
    
    # ========== 社交分享 ==========
    
    def share_to_wechat(self, pixmap: QPixmap) -> str:
        """分享到微信"""
        task = self._create_task(ShareType.WECHAT)
        self.task_started.emit(task.id)
        
        success, message = self.social_manager.share_to_wechat(pixmap)
        
        if success:
            self._update_task(task.id, status="completed", progress=100,
                            message=message)
        else:
            self._update_task(task.id, status="failed", message=message)
        
        return task.id
    
    def share_to_qq(self, pixmap: QPixmap) -> str:
        """分享到QQ"""
        task = self._create_task(ShareType.QQ)
        self.task_started.emit(task.id)
        
        success, message = self.social_manager.share_to_qq(pixmap)
        
        if success:
            self._update_task(task.id, status="completed", progress=100,
                            message=message)
        else:
            self._update_task(task.id, status="failed", message=message)
        
        return task.id
    
    def share_to_dingtalk(self, pixmap: QPixmap) -> str:
        """分享到钉钉"""
        task = self._create_task(ShareType.DINGTALK)
        self.task_started.emit(task.id)
        
        success, message = self.social_manager.share_to_dingtalk(pixmap)
        
        if success:
            self._update_task(task.id, status="completed", progress=100,
                            message=message)
        else:
            self._update_task(task.id, status="failed", message=message)
        
        return task.id
    
    def share_to_wecom(self, pixmap: QPixmap) -> str:
        """分享到企业微信"""
        task = self._create_task(ShareType.WECOM)
        self.task_started.emit(task.id)
        
        success, message = self.social_manager.share_to_wecom(pixmap)
        
        if success:
            self._update_task(task.id, status="completed", progress=100,
                            message=message)
        else:
            self._update_task(task.id, status="failed", message=message)
        
        return task.id
    
    # ========== 云存储 ==========
    
    def upload_to_onedrive(self, pixmap: QPixmap, filename: str = None,
                           remote_path: str = "/") -> str:
        """上传到OneDrive"""
        task = self._create_task(ShareType.ONEDRIVE)
        self.task_started.emit(task.id)
        
        provider = self.cloud_manager.get_provider(CloudProvider.ONEDRIVE)
        
        if not provider or not provider.access_token:
            self._update_task(task.id, status="failed", 
                            message="请先授权OneDrive账号")
            return task.id
        
        if not filename:
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        # 连接信号
        provider.upload_progress.connect(
            lambda u, t: self._update_task(task.id, progress=int(u/t*100) if t > 0 else 0)
        )
        provider.upload_completed.connect(
            lambda s, m: self._update_task(
                task.id, 
                status="completed" if s else "failed",
                progress=100 if s else 0,
                message=m,
                result_url=m if s else None
            )
        )
        
        self._update_task(task.id, status="running", message="正在上传...")
        provider.upload_pixmap(pixmap, filename, remote_path)
        
        return task.id
    
    def upload_to_baidu(self, pixmap: QPixmap, filename: str = None,
                        remote_path: str = "/apps/PyScreenshot") -> str:
        """上传到百度网盘"""
        task = self._create_task(ShareType.BAIDU_PAN)
        self.task_started.emit(task.id)
        
        provider = self.cloud_manager.get_provider(CloudProvider.BAIDU)
        
        if not provider or not provider.access_token:
            self._update_task(task.id, status="failed",
                            message="请先授权百度网盘账号")
            return task.id
        
        if not filename:
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        provider.upload_completed.connect(
            lambda s, m: self._update_task(
                task.id,
                status="completed" if s else "failed",
                progress=100 if s else 0,
                message=m
            )
        )
        
        self._update_task(task.id, status="running", message="正在上传...")
        provider.upload_pixmap(pixmap, filename, remote_path)
        
        return task.id
    
    # ========== 剪贴板 ==========
    
    def copy_to_clipboard(self, pixmap: QPixmap) -> str:
        """复制到剪贴板"""
        task = self._create_task(ShareType.CLIPBOARD)
        self.task_started.emit(task.id)
        
        success, message = self.social_manager.copy_to_clipboard(pixmap)
        
        if success:
            self._update_task(task.id, status="completed", progress=100,
                            message=message)
        else:
            self._update_task(task.id, status="failed", message=message)
        
        return task.id
    
    # ========== 任务管理 ==========
    
    def get_task(self, task_id: str) -> Optional[ShareTask]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[ShareTask]:
        """获取所有任务"""
        return list(self._tasks.values())
    
    def get_recent_tasks(self, count: int = 10) -> List[ShareTask]:
        """获取最近的任务"""
        tasks = sorted(self._tasks.values(), 
                      key=lambda t: t.created_at, reverse=True)
        return tasks[:count]
    
    def clear_completed_tasks(self):
        """清除已完成的任务"""
        self._tasks = {
            k: v for k, v in self._tasks.items() 
            if v.status not in ["completed", "failed"]
        }


# 全局实例
_share_manager = None

def get_share_manager() -> ShareManager:
    """获取分享管理器单例"""
    global _share_manager
    if _share_manager is None:
        _share_manager = ShareManager()
    return _share_manager
