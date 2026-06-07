"""
截图历史记录管理模块
"""
import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QByteArray, QBuffer, QIODevice


class HistoryManager:
    """截图历史记录管理器"""
    
    MAX_HISTORY = 30
    THUMBNAIL_SIZE = 120
    
    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path.home() / ".pyscreenshot"
        self.history_dir = self.config_dir / "history"
        self.thumbnails_dir = self.history_dir / "thumbnails"
        self.history_file = self.history_dir / "history.json"
        
        # 确保目录存在
        os.makedirs(self.thumbnails_dir, exist_ok=True)
        
        self.history = self._load_history()
    
    def _load_history(self) -> list:
        """加载历史记录"""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []
    
    def _save_history(self):
        """保存历史记录"""
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)
    
    def add_record(self, file_path: str, pixmap: QPixmap = None) -> dict:
        """添加历史记录"""
        record_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        
        # 生成缩略图
        thumbnail_path = ""
        if pixmap and not pixmap.isNull():
            thumbnail_path = str(self.thumbnails_dir / f"{record_id}.png")
            from PySide6.QtCore import Qt
            thumbnail = pixmap.scaled(
                self.THUMBNAIL_SIZE, self.THUMBNAIL_SIZE,
                aspectMode=Qt.AspectRatioMode.KeepAspectRatio,
                mode=Qt.TransformationMode.SmoothTransformation
            )
            thumbnail.save(thumbnail_path)
        
        record = {
            "id": record_id,
            "file_path": file_path,
            "thumbnail_path": thumbnail_path,
            "created_at": datetime.now().isoformat(),
            "file_name": os.path.basename(file_path),
            "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0
        }
        
        # 添加到历史记录开头
        self.history.insert(0, record)
        
        # 限制历史记录数量
        while len(self.history) > self.MAX_HISTORY:
            old_record = self.history.pop()
            self._delete_thumbnail(old_record)
        
        self._save_history()
        return record
    
    def _delete_thumbnail(self, record: dict):
        """删除缩略图"""
        thumbnail_path = record.get("thumbnail_path", "")
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                os.remove(thumbnail_path)
            except Exception:
                pass
    
    def delete_record(self, record_id: str):
        """删除历史记录"""
        for i, record in enumerate(self.history):
            if record["id"] == record_id:
                self._delete_thumbnail(record)
                self.history.pop(i)
                self._save_history()
                return True
        return False
    
    def get_all_records(self) -> list:
        """获取所有历史记录"""
        return self.history.copy()
    
    def get_record(self, record_id: str) -> dict:
        """获取单条历史记录"""
        for record in self.history:
            if record["id"] == record_id:
                return record
        return None
    
    def clear_history(self):
        """清空历史记录"""
        for record in self.history:
            self._delete_thumbnail(record)
        self.history = []
        self._save_history()
    
    def update_record_path(self, record_id: str, new_path: str):
        """更新记录的文件路径"""
        for record in self.history:
            if record["id"] == record_id:
                record["file_path"] = new_path
                record["file_name"] = os.path.basename(new_path)
                self._save_history()
                return True
        return False


class RecentFoldersManager:
    """最近访问文件夹管理器"""
    
    MAX_FOLDERS = 5
    
    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path.home() / ".pyscreenshot"
        self.folders_file = self.config_dir / "recent_folders.json"
        self.folders = self._load_folders()
    
    def _load_folders(self) -> list:
        """加载最近文件夹"""
        if self.folders_file.exists():
            try:
                with open(self.folders_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []
    
    def _save_folders(self):
        """保存最近文件夹"""
        os.makedirs(self.config_dir, exist_ok=True)
        with open(self.folders_file, "w", encoding="utf-8") as f:
            json.dump(self.folders, f, indent=2, ensure_ascii=False)
    
    def add_folder(self, folder_path: str):
        """添加文件夹到最近列表"""
        folder_path = os.path.normpath(folder_path)
        
        # 如果已存在，移到最前面
        if folder_path in self.folders:
            self.folders.remove(folder_path)
        
        self.folders.insert(0, folder_path)
        
        # 限制数量
        self.folders = self.folders[:self.MAX_FOLDERS]
        self._save_folders()
    
    def get_recent_folders(self, count: int = 3) -> list:
        """获取最近的文件夹"""
        # 过滤掉不存在的文件夹
        valid_folders = [f for f in self.folders if os.path.isdir(f)]
        return valid_folders[:count]
    
    def clear(self):
        """清空最近文件夹"""
        self.folders = []
        self._save_folders()
