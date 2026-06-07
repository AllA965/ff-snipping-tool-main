"""
预览优化器 - 处理大量截图的性能优化
支持：缩略图缓存、内存管理、异步加载、分页显示
"""
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QThread, QObject, pyqtSignal, QTimer
from typing import Dict, List, Tuple, Optional
import os
from datetime import datetime


class ThumbnailCache:
    """缩略图缓存 - 限制内存占用"""
    
    def __init__(self, max_size: int = 50, thumb_width: int = 120):
        self.max_size = max_size
        self.thumb_width = thumb_width
        self.cache: Dict[str, QPixmap] = {}
        self.access_times: Dict[str, float] = {}
    
    def get(self, tab_id: str) -> Optional[QPixmap]:
        """获取缓存的缩略图"""
        if tab_id in self.cache:
            self.access_times[tab_id] = datetime.now().timestamp()
            return self.cache[tab_id]
        return None
    
    def put(self, tab_id: str, pixmap: QPixmap):
        """缓存缩略图"""
        if len(self.cache) >= self.max_size:
            self._evict_lru()
        
        # 生成缩略图
        thumb = pixmap.scaledToWidth(
            self.thumb_width,
            mode=1  # SmoothTransformation
        )
        
        self.cache[tab_id] = thumb
        self.access_times[tab_id] = datetime.now().timestamp()
    
    def _evict_lru(self):
        """驱逐最少使用的缓存"""
        if not self.access_times:
            return
        
        lru_id = min(self.access_times, key=self.access_times.get)
        del self.cache[lru_id]
        del self.access_times[lru_id]
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.access_times.clear()
    
    def get_memory_usage(self) -> int:
        """获取内存占用（字节）"""
        total = 0
        for pixmap in self.cache.values():
            total += pixmap.width() * pixmap.height() * 4  # RGBA
        return total


class ScreenshotBatch:
    """截图批次 - 支持分页加载"""
    
    def __init__(self, batch_size: int = 20):
        self.batch_size = batch_size
        self.screenshots: Dict[str, Tuple[QPixmap, str]] = {}
        self.sorted_ids: List[str] = []
    
    def add(self, tab_id: str, pixmap: QPixmap, title: str):
        """添加截图"""
        self.screenshots[tab_id] = (pixmap, title)
        self.sorted_ids.append(tab_id)
    
    def remove(self, tab_id: str):
        """移除截图"""
        if tab_id in self.screenshots:
            del self.screenshots[tab_id]
            self.sorted_ids.remove(tab_id)
    
    def get_page(self, page: int) -> List[Tuple[str, QPixmap, str]]:
        """获取指定页的截图"""
        start = page * self.batch_size
        end = start + self.batch_size
        
        result = []
        for tab_id in self.sorted_ids[start:end]:
            pixmap, title = self.screenshots[tab_id]
            result.append((tab_id, pixmap, title))
        
        return result
    
    def get_page_count(self) -> int:
        """获取总页数"""
        return (len(self.screenshots) + self.batch_size - 1) // self.batch_size
    
    def sort_by(self, key: str):
        """按指定键排序"""
        if key == "newest":
            # 按添加顺序倒序
            self.sorted_ids.reverse()
        elif key == "oldest":
            # 按添加顺序正序
            pass
        elif key == "name":
            # 按标题排序
            self.sorted_ids.sort(
                key=lambda tid: self.screenshots[tid][1]
            )
        elif key == "size":
            # 按大小排序
            self.sorted_ids.sort(
                key=lambda tid: self.screenshots[tid][0].width() * 
                                self.screenshots[tid][0].height(),
                reverse=True
            )
    
    def filter_by(self, search: str = "", min_width: int = 0) -> List[str]:
        """按条件筛选"""
        result = []
        for tab_id in self.sorted_ids:
            pixmap, title = self.screenshots[tab_id]
            
            # 搜索条件
            if search and search.lower() not in title.lower():
                continue
            
            # 宽度条件
            if pixmap.width() < min_width:
                continue
            
            result.append(tab_id)
        
        return result


class AsyncImageLoader(QObject):
    """异步图像加载器 - 避免UI阻塞"""
    
    image_loaded = pyqtSignal(str, QPixmap)  # tab_id, pixmap
    progress_updated = pyqtSignal(int, int)  # current, total
    
    def __init__(self):
        super().__init__()
        self.thread = QThread()
        self.moveToThread(self.thread)
        self.thread.started.connect(self._process_queue)
        self.queue: List[Tuple[str, str]] = []  # (tab_id, file_path)
    
    def load_image(self, tab_id: str, file_path: str):
        """加入加载队列"""
        self.queue.append((tab_id, file_path))
        if not self.thread.isRunning():
            self.thread.start()
    
    def _process_queue(self):
        """处理加载队列"""
        total = len(self.queue)
        for i, (tab_id, file_path) in enumerate(self.queue):
            if os.path.exists(file_path):
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    self.image_loaded.emit(tab_id, pixmap)
            
            self.progress_updated.emit(i + 1, total)
        
        self.queue.clear()
        self.thread.quit()


class PreviewOptimizer:
    """预览优化器 - 综合管理"""
    
    def __init__(self, max_thumbnails: int = 50, batch_size: int = 20):
        self.thumbnail_cache = ThumbnailCache(max_size=max_thumbnails)
        self.batch = ScreenshotBatch(batch_size=batch_size)
        self.async_loader = AsyncImageLoader()
        self.current_page = 0
    
    def add_screenshot(self, tab_id: str, pixmap: QPixmap, title: str):
        """添加截图"""
        self.batch.add(tab_id, pixmap, title)
        self.thumbnail_cache.put(tab_id, pixmap)
    
    def remove_screenshot(self, tab_id: str):
        """移除截图"""
        self.batch.remove(tab_id)
    
    def get_current_page(self) -> List[Tuple[str, QPixmap, str]]:
        """获取当前页"""
        return self.batch.get_page(self.current_page)
    
    def next_page(self) -> bool:
        """下一页"""
        if self.current_page < self.batch.get_page_count() - 1:
            self.current_page += 1
            return True
        return False
    
    def prev_page(self) -> bool:
        """上一页"""
        if self.current_page > 0:
            self.current_page -= 1
            return True
        return False
    
    def sort(self, key: str):
        """排序"""
        self.batch.sort_by(key)
        self.current_page = 0
    
    def filter(self, search: str = "", min_width: int = 0) -> List[str]:
        """筛选"""
        return self.batch.filter_by(search, min_width)
    
    def get_memory_usage(self) -> Dict[str, int]:
        """获取内存占用"""
        return {
            "thumbnails": self.thumbnail_cache.get_memory_usage(),
            "total_screenshots": sum(
                p.width() * p.height() * 4
                for p, _ in self.batch.screenshots.values()
            )
        }
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_count": len(self.batch.screenshots),
            "page_count": self.batch.get_page_count(),
            "current_page": self.current_page,
            "batch_size": self.batch.batch_size,
            "memory_usage": self.get_memory_usage()
        }
    
    def clear(self):
        """清空所有数据"""
        self.batch.screenshots.clear()
        self.batch.sorted_ids.clear()
        self.thumbnail_cache.clear()
        self.current_page = 0


# 全局优化器实例
_preview_optimizer = PreviewOptimizer()


def get_preview_optimizer() -> PreviewOptimizer:
    """获取全局预览优化器"""
    return _preview_optimizer
