"""
图层管理系统 - 完整实现
支持：多图层管理、透明度、可见性、锁定、对齐、拖拽排序
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSlider, QSpinBox, QLineEdit,
    QMenu, QSizePolicy, QToolButton, QListWidget,
    QListWidgetItem, QAbstractItemView, QStyledItemDelegate
)
from PySide6.QtCore import Qt, Signal, QSize, QRect, QMimeData, QPoint
from PySide6.QtGui import (
    QPixmap, QPainter, QColor, QIcon, QDrag, QPen, QBrush,
    QImage, QTransform
)
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


@dataclass
class Layer:
    """图层数据类"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "图层"
    pixmap: object = field(default_factory=QPixmap)  # 可能是 QPixmap 或 QImage
    visible: bool = True
    locked: bool = False
    opacity: int = 100  # 0-100
    x: int = 0  # 位置偏移
    y: int = 0
    blend_mode: str = "normal"
    created_at: datetime = field(default_factory=datetime.now)
    
    def get_thumbnail(self, size: int = 48) -> QPixmap:
        """生成缩略图"""
        if self.pixmap.isNull():
            thumb = QPixmap(size, size)
            thumb.fill(QColor(200, 200, 200))
            return thumb
            
        # 如果是 QImage，先缩放再转 QPixmap
        if isinstance(self.pixmap, QImage):
            scaled_img = self.pixmap.scaled(
                size, size, 
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            return QPixmap.fromImage(scaled_img)
        
        return self.pixmap.scaled(
            size, size, 
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
    
    def copy(self) -> 'Layer':
        """复制图层"""
        new_layer = Layer(
            name=f"{self.name} 副本",
            pixmap=self.pixmap.copy(),
            visible=self.visible,
            locked=False,
            opacity=self.opacity,
            x=self.x + 10,
            y=self.y + 10,
            blend_mode=self.blend_mode
        )
        return new_layer


class LayerHistoryAction:
    """图层操作历史记录"""
    def __init__(self, action_type: str, data: Dict[str, Any]):
        self.action_type = action_type
        self.data = data
        self.timestamp = datetime.now()


class LayerManager:
    """图层管理器核心类"""
    
    def __init__(self, canvas_size: QSize = None):
        self.layers: List[Layer] = []
        self.active_layer_index: int = -1
        self.canvas_size = canvas_size or QSize(800, 600)
        self.history: List[LayerHistoryAction] = []
        self.history_index: int = -1
        self.max_history: int = 50
        self._selected_indices: List[int] = []
    
    def add_layer(self, pixmap: QPixmap = None, name: str = None, 
                  index: int = None) -> Layer:
        """添加新图层"""
        layer = Layer(
            name=name or f"图层 {len(self.layers) + 1}",
            pixmap=pixmap.copy() if pixmap else QPixmap(self.canvas_size)
        )
        
        if pixmap is None:
            layer.pixmap.fill(Qt.GlobalColor.transparent)
        
        if index is None:
            self.layers.append(layer)
            self.active_layer_index = len(self.layers) - 1
        else:
            self.layers.insert(index, layer)
            self.active_layer_index = index
        
        self._save_history("add_layer", {"layer_id": layer.id, "index": index})
        return layer
    
    def remove_layer(self, index: int) -> Optional[Layer]:
        """删除图层"""
        if 0 <= index < len(self.layers):
            if len(self.layers) <= 1:
                return None  # 至少保留一个图层
            
            layer = self.layers.pop(index)
            self._save_history("remove_layer", {
                "layer_id": layer.id, 
                "index": index,
                "layer_data": layer
            })
            
            if self.active_layer_index >= len(self.layers):
                self.active_layer_index = len(self.layers) - 1
            
            return layer
        return None
    
    def duplicate_layer(self, index: int) -> Optional[Layer]:
        """复制图层"""
        if 0 <= index < len(self.layers):
            new_layer = self.layers[index].copy()
            self.layers.insert(index + 1, new_layer)
            self.active_layer_index = index + 1
            self._save_history("duplicate_layer", {"layer_id": new_layer.id})
            return new_layer
        return None
    
    def move_layer(self, from_index: int, to_index: int) -> bool:
        """移动图层位置"""
        if 0 <= from_index < len(self.layers) and 0 <= to_index < len(self.layers):
            layer = self.layers.pop(from_index)
            self.layers.insert(to_index, layer)
            self.active_layer_index = to_index
            self._save_history("move_layer", {
                "from": from_index, 
                "to": to_index
            })
            return True
        return False
    
    def move_layer_up(self, index: int) -> bool:
        """上移图层"""
        if index < len(self.layers) - 1:
            return self.move_layer(index, index + 1)
        return False
    
    def move_layer_down(self, index: int) -> bool:
        """下移图层"""
        if index > 0:
            return self.move_layer(index, index - 1)
        return False
    
    def move_layer_to_top(self, index: int) -> bool:
        """置顶图层"""
        if index < len(self.layers) - 1:
            return self.move_layer(index, len(self.layers) - 1)
        return False
    
    def move_layer_to_bottom(self, index: int) -> bool:
        """置底图层"""
        if index > 0:
            return self.move_layer(index, 0)
        return False
    
    def set_layer_visibility(self, index: int, visible: bool):
        """设置图层可见性"""
        if 0 <= index < len(self.layers):
            self.layers[index].visible = visible
            self._save_history("visibility", {
                "index": index, 
                "visible": visible
            })
    
    def set_layer_locked(self, index: int, locked: bool):
        """设置图层锁定状态"""
        if 0 <= index < len(self.layers):
            self.layers[index].locked = locked
            self._save_history("locked", {"index": index, "locked": locked})
    
    def set_layer_opacity(self, index: int, opacity: int):
        """设置图层透明度"""
        if 0 <= index < len(self.layers):
            self.layers[index].opacity = max(0, min(100, opacity))
    
    def set_layer_name(self, index: int, name: str):
        """设置图层名称"""
        if 0 <= index < len(self.layers):
            old_name = self.layers[index].name
            self.layers[index].name = name
            self._save_history("rename", {
                "index": index,
                "old_name": old_name,
                "new_name": name
            })
    
    def get_active_layer(self) -> Optional[Layer]:
        """获取当前活动图层"""
        if 0 <= self.active_layer_index < len(self.layers):
            return self.layers[self.active_layer_index]
        return None
    
    def set_active_layer(self, index: int):
        """设置活动图层"""
        if 0 <= index < len(self.layers):
            self.active_layer_index = index
    
    def get_selected_layers(self) -> List[Layer]:
        """获取选中的图层"""
        return [self.layers[i] for i in self._selected_indices 
                if 0 <= i < len(self.layers)]
    
    def set_selected_indices(self, indices: List[int]):
        """设置选中的图层索引"""
        self._selected_indices = [i for i in indices 
                                   if 0 <= i < len(self.layers)]
    
    def merge_down(self, index: int) -> bool:
        """向下合并图层"""
        if index > 0 and index < len(self.layers):
            upper = self.layers[index]
            lower = self.layers[index - 1]
            
            if lower.locked:
                return False
            
            # 合并图像
            merged = lower.pixmap.copy()
            painter = QPainter(merged)
            painter.setOpacity(upper.opacity / 100.0)
            painter.drawPixmap(upper.x, upper.y, upper.pixmap)
            painter.end()
            
            lower.pixmap = merged
            self.layers.pop(index)
            self.active_layer_index = index - 1
            
            self._save_history("merge_down", {"index": index})
            return True
        return False
    
    def flatten(self) -> QImage:
        """合并所有图层 (返回 QImage)"""
        result = QImage(self.canvas_size, QImage.Format.Format_ARGB32)
        result.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(result)
        for layer in self.layers:
            if layer.visible:
                painter.setOpacity(layer.opacity / 100.0)
                # 支持 QImage 和 QPixmap
                if isinstance(layer.pixmap, QImage):
                    painter.drawImage(layer.x, layer.y, layer.pixmap)
                else:
                    painter.drawPixmap(layer.x, layer.y, layer.pixmap)
        painter.end()
        
        return result
    
    def render_preview(self):
        """渲染预览图像 (返回 QImage 或 QPixmap)"""
        return self.flatten()
    
    # ========== 对齐功能 ==========
    
    def align_layers(self, indices: List[int], alignment: str):
        """对齐选中的图层"""
        if len(indices) < 2:
            return
        
        layers = [self.layers[i] for i in indices if 0 <= i < len(self.layers)]
        if len(layers) < 2:
            return
        
        # 计算边界
        min_x = min(l.x for l in layers)
        max_x = max(l.x + l.pixmap.width() for l in layers)
        min_y = min(l.y for l in layers)
        max_y = max(l.y + l.pixmap.height() for l in layers)
        
        center_x = (min_x + max_x) // 2
        center_y = (min_y + max_y) // 2
        
        for layer in layers:
            if layer.locked:
                continue
            
            w, h = layer.pixmap.width(), layer.pixmap.height()
            
            if alignment == "left":
                layer.x = min_x
            elif alignment == "center_h":
                layer.x = center_x - w // 2
            elif alignment == "right":
                layer.x = max_x - w
            elif alignment == "top":
                layer.y = min_y
            elif alignment == "center_v":
                layer.y = center_y - h // 2
            elif alignment == "bottom":
                layer.y = max_y - h
        
        self._save_history("align", {"indices": indices, "alignment": alignment})
    
    def distribute_layers(self, indices: List[int], direction: str):
        """等间距分布图层"""
        if len(indices) < 3:
            return
        
        layers_with_idx = [(i, self.layers[i]) for i in indices 
                          if 0 <= i < len(self.layers)]
        if len(layers_with_idx) < 3:
            return
        
        if direction == "horizontal":
            layers_with_idx.sort(key=lambda x: x[1].x)
            first_x = layers_with_idx[0][1].x
            last_x = layers_with_idx[-1][1].x
            total_width = sum(l.pixmap.width() for _, l in layers_with_idx)
            space = (last_x + layers_with_idx[-1][1].pixmap.width() - 
                    first_x - total_width) / (len(layers_with_idx) - 1)
            
            current_x = first_x
            for _, layer in layers_with_idx:
                if not layer.locked:
                    layer.x = int(current_x)
                current_x += layer.pixmap.width() + space
        
        elif direction == "vertical":
            layers_with_idx.sort(key=lambda x: x[1].y)
            first_y = layers_with_idx[0][1].y
            last_y = layers_with_idx[-1][1].y
            total_height = sum(l.pixmap.height() for _, l in layers_with_idx)
            space = (last_y + layers_with_idx[-1][1].pixmap.height() - 
                    first_y - total_height) / (len(layers_with_idx) - 1)
            
            current_y = first_y
            for _, layer in layers_with_idx:
                if not layer.locked:
                    layer.y = int(current_y)
                current_y += layer.pixmap.height() + space
        
        self._save_history("distribute", {
            "indices": indices, 
            "direction": direction
        })
    
    # ========== 历史记录 ==========
    
    def _save_history(self, action_type: str, data: Dict[str, Any]):
        """保存操作历史"""
        # 清除当前位置之后的历史
        self.history = self.history[:self.history_index + 1]
        
        action = LayerHistoryAction(action_type, data)
        self.history.append(action)
        self.history_index = len(self.history) - 1
        
        # 限制历史记录数量
        if len(self.history) > self.max_history:
            self.history.pop(0)
            self.history_index -= 1
    
    def can_undo(self) -> bool:
        return self.history_index >= 0
