"""
预览缓存管理 - 存储预览状态和截屏文件
"""
from datetime import datetime, timedelta
from PySide6.QtGui import QPixmap
from typing import Optional, Dict, Any


class PreviewCacheItem:
    """预览缓存项"""
    
    def __init__(self, pixmap: QPixmap, scroll_position: tuple = (0, 0), 
                 zoom_level: float = 1.0, metadata: Dict[str, Any] = None):
        self.pixmap = pixmap.copy() if pixmap else None
        self.scroll_position = scroll_position  # (x, y)
        self.zoom_level = zoom_level
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.expires_at = datetime.now() + timedelta(hours=24)
    
    def is_expired(self) -> bool:
        """检查缓存是否过期"""
        return datetime.now() > self.expires_at
    
    def get_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        return {
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "scroll_position": self.scroll_position,
            "zoom_level": self.zoom_level,
            "metadata": self.metadata,
            "is_expired": self.is_expired()
        }


class PreviewCacheManager:
    """预览缓存管理器"""
    
    def __init__(self):
        self.cache: Dict[str, PreviewCacheItem] = {}
        self.current_cache_id: Optional[str] = None
    
    def save_preview(self, cache_id: str, pixmap: QPixmap, 
                    scroll_position: tuple = (0, 0), 
                    zoom_level: float = 1.0,
                    metadata: Dict[str, Any] = None) -> bool:
        """保存预览状态到缓存"""
        try:
            self.cache[cache_id] = PreviewCacheItem(
                pixmap, scroll_position, zoom_level, metadata
            )
            self.current_cache_id = cache_id
            return True
        except Exception as e:
            print(f"保存预览缓存失败: {e}")
            return False
    
    def load_preview(self, cache_id: str) -> Optional[PreviewCacheItem]:
        """从缓存加载预览状态"""
        if cache_id not in self.cache:
            return None
        
        item = self.cache[cache_id]
        if item.is_expired():
            del self.cache[cache_id]
            return None
        
        return item
    
    def get_current_preview(self) -> Optional[PreviewCacheItem]:
        """获取当前预览缓存"""
        if not self.current_cache_id:
            return None
        return self.load_preview(self.current_cache_id)
    
    def delete_preview(self, cache_id: str) -> bool:
        """删除预览缓存"""
        if cache_id in self.cache:
            del self.cache[cache_id]
            if self.current_cache_id == cache_id:
                self.current_cache_id = None
            return True
        return False
    
    def clear_expired(self):
        """清理过期的缓存"""
        expired_ids = [
            cache_id for cache_id, item in self.cache.items()
            if item.is_expired()
        ]
        for cache_id in expired_ids:
            del self.cache[cache_id]
    
    def clear_all(self):
        """清空所有缓存"""
        self.cache.clear()
        self.current_cache_id = None
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        self.clear_expired()
        return {
            "total_items": len(self.cache),
            "current_cache_id": self.current_cache_id,
            "items": {
                cache_id: item.get_info()
                for cache_id, item in self.cache.items()
            }
        }
    
    def has_preview(self, cache_id: str) -> bool:
        """检查是否有指定的预览缓存"""
        if cache_id not in self.cache:
            return False
        item = self.cache[cache_id]
        if item.is_expired():
            del self.cache[cache_id]
            return False
        return True


# 全局缓存管理器实例
_preview_cache_manager = PreviewCacheManager()


def get_preview_cache_manager() -> PreviewCacheManager:
    """获取全局预览缓存管理器"""
    return _preview_cache_manager
