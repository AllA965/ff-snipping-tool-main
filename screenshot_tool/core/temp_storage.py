"""
临时存储管理 - 自动暂存编辑中的图片
"""
import os
import json
import tempfile
from pathlib import Path
from datetime import datetime
from PySide6.QtGui import QPixmap


class TempStorageManager:
    """临时存储管理器"""
    
    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path.home() / ".pyscreenshot"
        self.temp_dir = self.config_dir / "temp"
        self.temp_index_file = self.temp_dir / "index.json"
        
        # 确保临时目录存在
        os.makedirs(self.temp_dir, exist_ok=True)
        
        self.temp_files = self._load_index()
    
    def _load_index(self) -> dict:
        """加载临时文件索引"""
        if self.temp_index_file.exists():
            try:
                with open(self.temp_index_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_index(self):
        """保存临时文件索引"""
        with open(self.temp_index_file, "w", encoding="utf-8") as f:
            json.dump(self.temp_files, f, indent=2, ensure_ascii=False)
    
    def save_temp(self, pixmap: QPixmap, tab_id: str, title: str = "") -> str:
        """保存临时图片"""
        if pixmap.isNull():
            return ""
        
        # 生成临时文件名
        temp_filename = f"temp_{tab_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
        temp_path = str(self.temp_dir / temp_filename)
        
        # 保存图片
        if pixmap.save(temp_path):
            # 记录到索引
            self.temp_files[tab_id] = {
                "path": temp_path,
                "title": title,
                "saved_at": datetime.now().isoformat(),
                "size": os.path.getsize(temp_path)
            }
            self._save_index()
            return temp_path
        
        return ""
    
    def get_temp(self, tab_id: str) -> str:
        """获取临时文件路径"""
        if tab_id in self.temp_files:
            path = self.temp_files[tab_id].get("path", "")
            if path and os.path.exists(path):
                return path
        return ""
    
    def load_temp(self, tab_id: str) -> QPixmap:
        """加载临时图片"""
        path = self.get_temp(tab_id)
        if path:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                return pixmap
        return QPixmap()
    
    def delete_temp(self, tab_id: str):
        """删除临时文件"""
        if tab_id in self.temp_files:
            path = self.temp_files[tab_id].get("path", "")
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
            del self.temp_files[tab_id]
            self._save_index()
    
    def clear_all_temp(self):
        """清空所有临时文件"""
        for tab_id in list(self.temp_files.keys()):
            self.delete_temp(tab_id)
    
    def cleanup_old_temp(self, max_age_hours: int = 24):
        """清理旧的临时文件"""
        import time
        current_time = time.time()
        
        for tab_id in list(self.temp_files.keys()):
            path = self.temp_files[tab_id].get("path", "")
            if path and os.path.exists(path):
                file_age = (current_time - os.path.getmtime(path)) / 3600
                if file_age > max_age_hours:
                    self.delete_temp(tab_id)
