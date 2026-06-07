"""
白板工具 - 透明桌面标注版
功能：覆盖在桌面上的透明画板，可在桌面和其他应用上直接绘图标注
支持：所有绘图工具、背景色切换、放大缩小、临时保存和导出
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QToolButton, QSpinBox, QLabel,
    QFileDialog, QApplication, QFrame, QSlider,
    QMenu, QPushButton, QInputDialog, QWidgetAction
)
from PySide6.QtCore import Qt, QPoint, QSize, Signal, QRect, QRectF, QPointF, QTimer
from PySide6.QtGui import (
    QPainter, QColor, QPen, QPixmap, QCursor,
    QGuiApplication, QBrush, QFont, QScreen, QPainterPath,
    QAction
)
from datetime import datetime
import math
import os
from ui.modern_dialog import ModernMessageBox
from ui.icons import set_window_icon
from ui.text_box import TextBoxWidget
from ui.text_manager import TextManagerMixin
from tools.palette import PaletteWindow


class TransparentCanvas(QWidget, TextManagerMixin):
    """透明画布 - 覆盖在桌面上"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_text_manager()

        # 获取屏幕尺寸
        screen = QGuiApplication.primaryScreen().geometry()
        self.canvas_size = QSize(screen.width(), screen.height())

        # 背景模式: transparent, white, black, gray
        self.background_mode = "transparent"

        # 绘图状态
        self.drawing = False
        self.last_point = QPointF()
        self.current_path = None  # 当前绘图路径

        # 工具设置
        self.current_tool = 'pen'
        self.pen_color = QColor(255, 0, 0)  # 默认红色
        self.pen_width = 3
        self.font_size = 16
        
        # 橡皮擦相关
        self.eraser_mode = 'stroke'  # 'stroke' = 擦除整条线条, 'area' = 擦除覆盖区域
        self.eraser_size = 20  # 橡皮大小（仅用于区域擦除模式）
        self.eraser_path = []  # 用于区域擦除的路径记录

        # 形状绘制
        self.shape_start = QPoint()
        self.temp_layer = None

        # 历史记录 (改为存储 annotations 列表)
        self.annotations = []
        self.current_annotation = None
        self.history = [[]]  # 初始为空列表
        self.history_index = 0
        self.max_history = 50

        # 缓存层 - 性能优化
        self.cache_pixmap = QPixmap(self.canvas_size)
        self.cache_pixmap.fill(Qt.GlobalColor.transparent)
        self.needs_update_cache = True

        self.setMouseTracking(True)

    def set_background(self, mode: str):
        """设置背景模式"""
        self.background_mode = mode
        self.update()

    def get_background_color(self) -> QColor:
        """获取背景颜色"""
        if self.background_mode == "white":
            return QColor(255, 255, 255, 230)
        elif self.background_mode == "black":
            return QColor(30, 30, 30, 230)
        elif self.background_mode == "gray":
            return QColor(128, 128, 128, 230)
        else:
            return QColor(0, 0, 0, 1)  # 几乎完全透明

    def set_tool(self, tool: str):
        self.current_tool = tool
        # 清除缓存
        if hasattr(self, '_pen_cache'):
            self._pen_cache.clear()
        if hasattr(self, '_brush_cache'):
            self._brush_cache.clear()
            
        if tool == 'pan':
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)

    def set_color(self, color: QColor):
        self.pen_color = color
        # 清除缓存
        if hasattr(self, '_pen_cache'):
            self._pen_cache.clear()
        if hasattr(self, '_brush_cache'):
            self._brush_cache.clear()

    def set_width(self, width: int):
        self.pen_width = width
        # 清除缓存
        if hasattr(self, '_pen_cache'):
            self._pen_cache.clear()

    def set_font_size(self, size: int):
        self.font_size = size

    def set_eraser_mode(self, mode: str):
        """设置橡皮擦模式: 'stroke' = 擦除整条线条, 'area' = 擦除覆盖区域"""
        self.eraser_mode = mode
        self.update()

    def set_eraser_size(self, size: int):
        """设置橡皮擦大小（仅用于区域擦除模式）"""
        self.eraser_size = max(5, min(100, size))
        self.update()

    def clear(self):
        """清空画布"""
        self.annotations = []
        self.needs_update_cache = True
        self._save_history()
        self.update()

    def undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            # 恢复历史状态并深拷贝
            self.annotations = [ann.copy() for ann in self.history[self.history_index]]
            self.needs_update_cache = True
            self.update()
            return True
        return False

    def _save_history(self):
        self.history = self.history[:self.history_index + 1]
        # 保存当前 annotations 的深拷贝
        self.history.append([ann.copy() for ann in self.annotations])
        self.history_index = len(self.history) - 1
        if len(self.history) > self.max_history:
            self.history.pop(0)
            self.history_index -= 1

    def paintEvent(self, event):
        painter = QPainter(self)
        
        # 仅在非移动/非绘图状态或标注数量较少时开启抗锯齿，提升交互流畅度
        if not getattr(self, 'moving', False) and (not self.drawing or len(self.annotations) < 100):
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制背景
        painter.fillRect(self.rect(), self.get_background_color())

        # 如果需要，更新缓存层
        if self.needs_update_cache:
            self._update_cache_pixmap()
            self.needs_update_cache = False
            
        # 绘制缓存层
        painter.drawPixmap(0, 0, self.cache_pixmap)

        # 绘制文本框拖拽预览
        if self.creating_text_box and self.text_box_preview_rect:
            self._draw_text_box_preview(painter, self.text_box_preview_rect)

        # 预先创建通用的 Pen 缓存，减少循环内对象创建
        if not hasattr(self, '_pen_cache'):
            self._pen_cache = {}
        if not hasattr(self, '_brush_cache'):
            self._brush_cache = {}
            
        # 绘制当前正在编辑的标注
        if self.current_annotation:
            self._draw_annotation_optimized(painter, self.current_annotation, self._pen_cache, self._brush_cache)

        # 绘制橡皮擦预览 (仅在区域擦除模式下显示圆形预览)
        if self.current_tool == 'eraser' and getattr(self, 'eraser_mode', 'stroke') == 'area' and hasattr(self, 'mouse_pos'):
            # 绘制橡皮擦圆形预览
            eraser_size = self.eraser_size
            rect = QRectF(
                self.mouse_pos.x() - eraser_size / 2,
                self.mouse_pos.y() - eraser_size / 2,
                eraser_size,
                eraser_size
            )
            
            # 开启抗锯齿绘制预览圆
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            # 绘制外边框（浅色）
            painter.setPen(QPen(QColor(0, 0, 0, 180), 1))
            painter.drawEllipse(rect)
            
            # 绘制内边框（深色，增加对比度）
            painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
            painter.drawEllipse(rect.adjusted(1, 1, -1, -1))

    def _update_cache_pixmap(self):
        """更新缓存层"""
        self.cache_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(self.cache_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen_cache = {}
        brush_cache = {}
        for ann in self.annotations:
            self._draw_annotation_optimized(painter, ann, pen_cache, brush_cache)
        painter.end()

    def _draw_annotation_optimized(self, painter: QPainter, ann: dict, pen_cache: dict, brush_cache: dict):
        """绘制单个标注对象 - 性能优化版"""
        tool = ann.get('type')
        color = ann.get('color', self.pen_color)
        width = ann.get('width', self.pen_width)
        
        # 处理画笔缓存
        is_highlighter = tool == 'highlighter'
        if is_highlighter:
            c = QColor(color)
            c.setAlpha(80)
            cache_color = c.rgba()
            cache_width = width * 3
        else:
            cache_color = color.rgba() if hasattr(color, 'rgba') else QColor(color).rgba()
            cache_width = width
            
        pen_key = (cache_color, cache_width, tool == 'arrow')
        if pen_key not in pen_cache:
            pen = QPen(QColor.fromRgba(cache_color), cache_width, Qt.PenStyle.SolidLine, 
                      Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            pen_cache[pen_key] = pen
        
        painter.setPen(pen_cache[pen_key])
        
        if tool in ['pen', 'highlighter']:
            points = ann.get('points', [])
            if len(points) > 1:
                path = QPainterPath()
                path.moveTo(points[0])
                for pt in points[1:]:
                    path.lineTo(pt)
                painter.drawPath(path)
            elif len(points) == 1:
                painter.drawPoint(points[0])
        elif tool in ['rect', 'filled_rect', 'ellipse', 'filled_ellipse', 'line', 'arrow']:
            rect = QRect(ann['start'], ann['end']).normalized()
            
            if tool == 'rect':
                painter.drawRect(rect)
            elif tool == 'filled_rect':
                brush_key = cache_color
                if brush_key not in brush_cache:
                    brush_cache[brush_key] = QBrush(QColor.fromRgba(cache_color))
                painter.setBrush(brush_cache[brush_key])
                painter.drawRect(rect)
                painter.setBrush(Qt.BrushStyle.NoBrush)
            elif tool == 'ellipse':
                painter.drawEllipse(rect)
            elif tool == 'filled_ellipse':
                brush_key = cache_color
                if brush_key not in brush_cache:
                    brush_cache[brush_key] = QBrush(QColor.fromRgba(cache_color))
                painter.setBrush(brush_cache[brush_key])
                painter.drawEllipse(rect)
                painter.setBrush(Qt.BrushStyle.NoBrush)
            elif tool == 'line':
                painter.drawLine(ann['start'], ann['end'])
            elif tool == 'arrow':
                self._draw_arrow_optimized(painter, ann['start'], ann['end'], pen_cache[pen_key])
        elif tool == 'text':
            font = QFont("Microsoft YaHei", ann.get('font_size', self.font_size))
            painter.setFont(font)
            painter.setPen(QColor.fromRgba(cache_color))
            
            rect = ann.get('rect')
            if rect:
                margin = 6
                padding_x = 6
                padding_y = 4
                text_rect = rect.adjusted(margin + padding_x, margin + padding_y, -margin - padding_x, -margin - padding_y)
            else:
                text_rect = QRectF(ann['start'].x(), ann['start'].y(), 200, 60)
            
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, ann.get('text', ''))

    def _draw_arrow_optimized(self, painter: QPainter, start: QPoint, end: QPoint, pen: QPen):
        """绘制箭头 - 优化版"""
        painter.drawLine(start, end)
        angle = math.atan2(end.y() - start.y(), end.x() - start.x())
        arrow_size = 15
        p1 = QPoint(
            int(end.x() - arrow_size * math.cos(angle - math.pi / 6)),
            int(end.y() - arrow_size * math.sin(angle - math.pi / 6))
        )
        p2 = QPoint(
            int(end.x() - arrow_size * math.cos(angle + math.pi / 6)),
            int(end.y() - arrow_size * math.sin(angle + math.pi / 6))
        )
        # 直接使用传入的画笔颜色作为填充色，避免重新创建 QBrush
        painter.setBrush(QBrush(pen.color()))
        painter.drawPolygon([end, p1, p2])
        painter.setBrush(Qt.BrushStyle.NoBrush)

    def _draw_annotation(self, painter: QPainter, ann: dict):
        # 此方法已被 _draw_annotation_optimized 替代，保留空实现或直接移除
        pass

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 1. 文本工具逻辑
            if self.current_tool == 'text':
                # 检查是否点击在现有文本框上
                if self._check_click_on_text_box(event.pos()):
                    return
                
                # 开始拖拽创建文本框
                self.creating_text_box = True
                self.text_box_start_pos = event.pos()
                self.text_box_preview_rect = QRect(event.pos(), QSize(1, 1))
                return

            # 2. 其他工具逻辑
            self.drawing = True
            pos = event.position()
            self.last_point = pos
            self.shape_start = event.pos()
            
            if self.current_tool == 'eraser':
                self._erase(event.pos())
            elif self.current_tool == 'text':
                # 这里不应该再进入，上面已经处理了
                pass
            else:
                # 创建新标注
                self.current_annotation = {
                    'type': self.current_tool,
                    'color': QColor(self.pen_color),
                    'width': self.pen_width,
                    'start': event.pos(),
                    'end': event.pos(),
                    'points': [pos],
                    'font_size': self.font_size
                }
            self.update()

    def mouseMoveEvent(self, event):
        pos = event.position()
        self.mouse_pos = event.pos()
        
        # 文本框拖拽预览
        if self.creating_text_box and event.buttons() & Qt.MouseButton.LeftButton:
            self.text_box_preview_rect = QRect(self.text_box_start_pos, event.pos()).normalized()
            # 确保最小尺寸
            if self.text_box_preview_rect.width() < 20:
                self.text_box_preview_rect.setWidth(20)
            if self.text_box_preview_rect.height() < 20:
                self.text_box_preview_rect.setHeight(20)
            self.update()
            return

        if self.current_tool == 'eraser':
            self.update()

        if self.drawing and event.buttons() & Qt.MouseButton.LeftButton:
            if self.current_tool == 'eraser':
                self._erase(event.pos())
            elif self.current_annotation:
                self.current_annotation['end'] = event.pos()
                if self.current_tool in ['pen', 'highlighter']:
                    self.current_annotation['points'].append(pos)
                self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 文本框创建结束
            if self.creating_text_box:
                self.creating_text_box = False
                if self.text_box_preview_rect and self.text_box_preview_rect.width() >= 30 and self.text_box_preview_rect.height() >= 30:
                    self._add_text_with_rect(self.text_box_preview_rect)
                else:
                    self._add_text_at(event.pos())
                self.text_box_preview_rect = None
                self.update()
                return

            if self.drawing:
                self.drawing = False
                if self.current_annotation:
                    self.annotations.append(self.current_annotation)
                    self.current_annotation = None
                    self.needs_update_cache = True
                    self._save_history()
                elif self.current_tool == 'eraser':
                    # 橡皮擦结束也保存一次历史
                    self._save_history()
                self.update()

    def _point_to_segment_dist_sq(self, p, a, b):
        """计算点 p 到线段 ab 的距离平方"""
        px, py = p.x(), p.y()
        ax, ay = a.x(), a.y()
        bx, by = b.x(), b.y()
        
        l2 = (ax - bx)**2 + (ay - by)**2
        if l2 == 0:
            return (px - ax)**2 + (py - ay)**2
            
        t = ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / l2
        t = max(0, min(1, t))
        
        dx = px - (ax + t * (bx - ax))
        dy = py - (ay + t * (by - ay))
        return dx*dx + dy*dy

    def _get_annotation_rect(self, ann):
        """获取并缓存标注的包围矩形"""
        if 'bbox' in ann:
            return ann['bbox']
            
        tool = ann.get('type')
        if tool in ['rect', 'ellipse', 'filled_rect', 'filled_ellipse', 'arrow', 'line']:
            rect = QRect(ann['start'], ann['end']).normalized()
        elif tool == 'text':
            rect = ann.get('rect', QRect(ann['start'], QSize(100, 30)))
        elif tool in ['pen', 'highlighter']:
            points = ann.get('points', [])
            if not points:
                rect = QRect()
            else:
                min_x = min_y = float('inf')
                max_x = max_y = float('-inf')
                for p in points:
                    x, y = p.x(), p.y()
                    if x < min_x: min_x = x
                    if x > max_x: max_x = x
                    if y < min_y: min_y = y
                    if y > max_y: max_y = y
                rect = QRect(int(min_x), int(min_y), int(max_x - min_x), int(max_y - min_y))
        else:
            rect = QRect()
            
        width = ann.get('width', 2)
        rect = rect.adjusted(-width - 5, -width - 5, width + 5, width + 5)
        ann['bbox'] = rect
        return rect

    def _get_annotation_rect(self, ann):
        """获取并缓存标注的包围矩形 (性能优化关键)"""
        if 'bbox' in ann:
            return ann['bbox']
            
        tool = ann.get('type')
        if tool in ['rect', 'ellipse', 'filled_rect', 'filled_ellipse', 'arrow', 'line']:
            rect = QRect(ann['start'], ann['end']).normalized()
        elif tool == 'text':
            # 文本框位置和大小
            rect = ann.get('rect', QRect(ann['start'], QSize(100, 30)))
        elif tool in ['pen', 'highlighter']:
            points = ann.get('points', [])
            if not points:
                rect = QRect()
            else:
                min_x = min_y = float('inf')
                max_x = max_y = float('-inf')
                for p in points:
                    p_pt = p.toPoint() if hasattr(p, 'toPoint') else p
                    x, y = p_pt.x(), p_pt.y()
                    if x < min_x: min_x = x
                    if x > max_x: max_x = x
                    if y < min_y: min_y = y
                    if y > max_y: max_y = y
                rect = QRect(int(min_x), int(min_y), int(max_x - min_x), int(max_y - min_y))
        else:
            rect = QRect()
            
        # 考虑画笔宽度和一些边距
        width = ann.get('width', 2)
        rect = rect.adjusted(-width - 5, -width - 5, width + 5, width + 5)
        ann['bbox'] = rect
        return rect

    def _point_to_segment_dist_sq(self, p, a, b):
        """计算点 p 到线段 ab 的距离平方 (避免 sqrt 提升性能)"""
        px, py = p.x(), p.y()
        ax, ay = a.x(), a.y()
        bx, by = b.x(), b.y()
        
        l2 = (ax - bx)**2 + (ay - by)**2
        if l2 == 0:
            return (px - ax)**2 + (py - ay)**2
            
        t = ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / l2
        t = max(0, min(1, t))
        
        dx = px - (ax + t * (bx - ax))
        dy = py - (ay + t * (by - ay))
        return dx*dx + dy*dy

    def _erase(self, pos: QPoint):
        """橡皮擦 - 根据模式擦除 (增加路径插值以提高灵敏度)"""
        if not self.annotations:
            return

        # 计算距离
        last_p = getattr(self, 'last_point', pos)
        dist_sq = (pos.x() - last_p.x())**2 + (pos.y() - last_p.y())**2
        
        # 决定插值步长：对象擦除使用较小步长，区域擦除根据橡皮大小调整
        step_size = 5 if self.eraser_mode == 'stroke' else max(2, self.eraser_size / 5)
        step_size_sq = step_size ** 2
        
        self.any_erased = False
        
        # 如果移动距离较大，进行插值处理
        if dist_sq > step_size_sq:
            dist = math.sqrt(dist_sq)
            steps = int(dist / step_size) + 1
            for i in range(1, steps + 1):
                interp_pos = QPoint(
                    int(last_p.x() + (pos.x() - last_p.x()) * i / steps),
                    int(last_p.y() + (pos.y() - last_p.y()) * i / steps)
                )
                if self.eraser_mode == 'area':
                    self._erase_area(interp_pos, should_update=False)
                else:
                    self._erase_stroke(interp_pos, should_update=False)
        else:
            if self.eraser_mode == 'area':
                self._erase_area(pos, should_update=False)
            else:
                self._erase_stroke(pos, should_update=False)
        
        if self.any_erased:
            # 清除缓存并通知更新
            if hasattr(self, '_pen_cache'): self._pen_cache.clear()
            if hasattr(self, '_brush_cache'): self._brush_cache.clear()
            self.needs_update_cache = True
            self.update()
            
        self.last_point = pos

    def _erase_stroke(self, pos: QPoint, should_update=True):
        """擦除整条线条模式 - 优化碰撞检测"""
        sensitivity = max(15, self.pen_width * 2.5)
        sensitivity_sq = sensitivity ** 2
        
        removed_any = False
        new_annotations = []
        
        # 预先创建检测区域
        check_rect = QRect(pos.x() - sensitivity, pos.y() - sensitivity, sensitivity * 2, sensitivity * 2)
        
        for ann in self.annotations:
            # 使用包围盒快速过滤
            ann_rect = self._get_annotation_rect(ann)
            if not ann_rect.intersects(check_rect):
                new_annotations.append(ann)
                continue
                
            should_remove = False
            tool = ann.get('type')
            
            if tool in ['rect', 'ellipse', 'arrow', 'line', 'filled_rect', 'filled_ellipse', 'text']:
                # 包围盒已经交叉，且这些是简单图形，直接删除
                should_remove = True
            elif tool in ['pen', 'highlighter']:
                points = ann.get('points', [])
                for i in range(1, len(points)):
                    p_prev = points[i-1].toPoint() if hasattr(points[i-1], 'toPoint') else points[i-1]
                    p_curr = points[i].toPoint() if hasattr(points[i], 'toPoint') else points[i]
                    if self._point_to_segment_dist_sq(pos, p_prev, p_curr) < sensitivity_sq:
                        should_remove = True
                        break
                if not should_remove and len(points) == 1:
                    p = points[0].toPoint() if hasattr(points[0], 'toPoint') else points[0]
                    if (p.x() - pos.x())**2 + (p.y() - pos.y())**2 < sensitivity_sq:
                        should_remove = True
            
            if should_remove:
                removed_any = True
                self.any_erased = True
            else:
                new_annotations.append(ann)
        
        if removed_any:
            self.annotations = new_annotations
            if should_update:
                if hasattr(self, '_pen_cache'): self._pen_cache.clear()
                if hasattr(self, '_brush_cache'): self._brush_cache.clear()
                self.needs_update_cache = True
                self.update()

    def _on_text_confirmed(self, text: str, text_box):
        """文本确认后的回调 - 保存为标注"""
        if not text.strip():
            self._remove_text_box(text_box)
            return

        # 获取文本框位置和大小
        rect = text_box.geometry()
        
        # 计算实际文本内容区域（去除手柄边距）
        margin = text_box._handle_radius + 2
        top_margin = text_box._rotate_handle_distance + margin
        
        # 调整为实际显示文本的区域
        content_rect = rect.adjusted(margin, top_margin, -margin, -margin)
        
        # 创建标注数据
        annotation = {
            'type': 'text',
            'text': text,
            'color': text_box.text_color,
            'font_size': text_box.font_size,
            'rect': content_rect,  # 保存内容区域用于绘制
            'start': content_rect.topLeft(),
            'end': content_rect.bottomRight(),
            'points': [content_rect.topLeft()]  # 兼容性
        }
        
        self.annotations.append(annotation)
        self.needs_update_cache = True
        self._save_history()
        
        # 移除文本框控件
        self._remove_text_box(text_box)


    def _get_line_circle_intersections(self, p1, p2, center, radius):
        """计算线段 p1p2 与圆 (center, radius) 的交点"""
        p1_pt = p1.toPoint() if hasattr(p1, 'toPoint') else p1
        p2_pt = p2.toPoint() if hasattr(p2, 'toPoint') else p2
        
        dx = p2_pt.x() - p1_pt.x()
        dy = p2_pt.y() - p1_pt.y()
        a = dx*dx + dy*dy
        if a == 0:
            return []
            
        fx = p1_pt.x() - center.x()
        fy = p1_pt.y() - center.y()
        
        b = 2 * (fx * dx + fy * dy)
        c = (fx * fx + fy * fy) - radius * radius
        
        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            return []
            
        discriminant = math.sqrt(discriminant)
        t1 = (-b - discriminant) / (2 * a)
        t2 = (-b + discriminant) / (2 * a)
        
        intersections = []
        if 0 <= t1 <= 1:
            intersections.append(QPoint(int(p1_pt.x() + t1 * dx), int(p1_pt.y() + t1 * dy)))
        if 0 <= t2 <= 1:
            intersections.append(QPoint(int(p1_pt.x() + t2 * dx), int(p1_pt.y() + t2 * dy)))
            
        if len(intersections) == 2 and t1 > t2:
            intersections.reverse()
            
        return intersections

    def _erase_area(self, pos: QPoint, should_update=True):
        """局部擦除模式 - 擦除标注内容 (像素级精确裁剪版)"""
        eraser_radius = self.eraser_size / 2
        eraser_radius_sq = eraser_radius ** 2
        new_annotations = []
        removed_any = False
        
        # 预先计算擦除区域矩形
        erase_rect = QRect(
            int(pos.x() - eraser_radius),
            int(pos.y() - eraser_radius),
            int(self.eraser_size),
            int(self.eraser_size)
        )
        
        for ann in self.annotations:
            # 使用包围盒快速过滤
            ann_rect = self._get_annotation_rect(ann)
            if not ann_rect.intersects(erase_rect):
                new_annotations.append(ann)
                continue
            
            tool = ann.get('type')
            if tool in ['rect', 'ellipse', 'arrow', 'line', 'filled_rect', 'filled_ellipse', 'text']:
                # 简单图形一旦相交就整块删除
                removed_any = True
                self.any_erased = True
                continue

            if tool in ['pen', 'highlighter']:
                points = ann.get('points', [])
                if not points: continue
                
                segments = []
                current_segment = []
                hit_in_this_ann = False
                
                # 检查点序列
                for i in range(len(points)):
                    p_curr = points[i]
                    p_curr_pt = p_curr.toPoint() if hasattr(p_curr, 'toPoint') else p_curr
                    dist_sq = (p_curr_pt.x() - pos.x())**2 + (p_curr_pt.y() - pos.y())**2
                    in_curr = dist_sq < eraser_radius_sq
                    
                    if not in_curr:
                        if i > 0:
                            p_prev = points[i-1]
                            p_prev_pt = p_prev.toPoint() if hasattr(p_prev, 'toPoint') else p_prev
                            dist_prev_sq = (p_prev_pt.x() - pos.x())**2 + (p_prev_pt.y() - pos.y())**2
                            if dist_prev_sq < eraser_radius_sq:
                                # 从圆内出圆外，找交点作为新线段起点
                                hit_in_this_ann = True
                                intersections = self._get_line_circle_intersections(p_prev, p_curr, pos, eraser_radius)
                                if intersections: current_segment.append(intersections[0])
                        current_segment.append(p_curr)
                    else:
                        hit_in_this_ann = True
                        if i > 0:
                            p_prev = points[i-1]
                            p_prev_pt = p_prev.toPoint() if hasattr(p_prev, 'toPoint') else p_prev
                            dist_prev_sq = (p_prev_pt.x() - pos.x())**2 + (p_prev_pt.y() - pos.y())**2
                            if dist_prev_sq >= eraser_radius_sq:
                                # 从圆外进圆内，找交点作为旧线段终点
                                intersections = self._get_line_circle_intersections(p_prev, p_curr, pos, eraser_radius)
                                if intersections: current_segment.append(intersections[0])
                        if current_segment:
                            segments.append(current_segment)
                            current_segment = []
                
                if current_segment:
                    segments.append(current_segment)
                
                if hit_in_this_ann:
                    removed_any = True
                    self.any_erased = True
                    for seg in segments:
                        if len(seg) >= 1:
                            new_ann = ann.copy()
                            new_ann['points'] = seg
                            # 重新计算新段的 bbox
                            if 'bbox' in new_ann: del new_ann['bbox']
                            self._get_annotation_rect(new_ann)
                            new_annotations.append(new_ann)
                else:
                    new_annotations.append(ann)
            else:
                new_annotations.append(ann)
        
        if removed_any:
            self.annotations = new_annotations
            if should_update:
                if hasattr(self, '_pen_cache'): self._pen_cache.clear()
                if hasattr(self, '_brush_cache'): self._brush_cache.clear()
                self.needs_update_cache = True
                self.update()

    def _on_text_confirmed(self, text: str, text_box: TextBoxWidget):
        """文本确认后保存到标注列表"""
        if text.strip():
            ann = {
                'type': 'text',
                'color': text_box.text_color,
                'start': text_box.pos(),
                'rect': text_box.geometry(),
                'text': text,
                'font_size': text_box.font_size
            }
            self.annotations.append(ann)
            self.needs_update_cache = True
            self._save_history()
        
        self._remove_text_box(text_box)
        self.update()
    
    def _on_text_deleted(self, text_box: TextBoxWidget):
        """处理文本框删除信号"""
        self._remove_text_box(text_box)
        self.update()

    def get_pixmap(self) -> QPixmap:
        """获取当前绘图内容（带背景）"""
        result = QPixmap(self.canvas_size)
        result.fill(self.get_background_color())
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 使用本地缓存，不干扰成员变量缓存
        pen_cache = {}
        brush_cache = {}
        for ann in self.annotations:
            self._draw_annotation_optimized(painter, ann, pen_cache, brush_cache)
        painter.end()
        return result

    def get_drawing_only(self) -> QPixmap:
        """仅获取绘图内容（透明背景）"""
        result = QPixmap(self.canvas_size)
        result.fill(Qt.GlobalColor.transparent)
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 使用本地缓存，不干扰成员变量缓存
        pen_cache = {}
        brush_cache = {}
        for ann in self.annotations:
            self._draw_annotation_optimized(painter, ann, pen_cache, brush_cache)
        painter.end()
        return result


class FullscreenWhiteboard(QMainWindow):
    """全屏透明白板"""

    closed = Signal()

    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self._is_minimized = False
        self._normal_geometry = None
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("白板")
        set_window_icon(self)
        # 无边框、置顶、透明背景
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 全屏
        screen = QGuiApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        central = QWidget()
        central.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 先创建画布（工具栏需要引用它）
        self.canvas = TransparentCanvas()

        # 再创建工具栏
        self.toolbar = self._create_toolbar()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, 1)

    def _create_toolbar(self) -> QFrame:
        toolbar = QFrame()
        toolbar.setFixedHeight(50)
        toolbar.setObjectName("whiteboardToolbar")
        toolbar.setStyleSheet("""
            QFrame#whiteboardToolbar {
                background: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(0, 0, 0, 0.05);
                border-radius: 12px;
            }
            QToolButton {
                background: transparent;
                border: none;
                border-radius: 8px;
                padding: 6px;
                color: #333;
                min-width: 32px;
                font-size: 14px;
                font-family: "Segoe UI Emoji", "Apple Color Emoji";
            }
            QToolButton:hover { 
                background: rgba(0, 0, 0, 0.05); 
                margin-top: -2px;
            }
            QToolButton:checked { 
                background: #0078D7; 
                color: white; 
            }
            QSpinBox {
                background: #f0f0f0;
                color: #333;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 2px 5px;
                min-width: 45px;
                font-size: 12px;
            }
            QSpinBox:hover { border-color: #0078D7; }
            QLabel { color: #666; font-size: 11px; font-weight: bold; }
        """)

        # 为工具栏添加阴影
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        toolbar.setGraphicsEffect(shadow)

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)

        # 移动手柄
        move_label = QLabel("⋮⋮")
        move_label.setStyleSheet("color: #aaa; font-size: 16px; padding: 0 5px;")
        move_label.setCursor(Qt.CursorShape.SizeAllCursor)
        layout.addWidget(move_label)
        self._move_handle = move_label

        # 绘图工具分组
        tools_group = QHBoxLayout()
        tools_group.setSpacing(4)
        self.tool_buttons = {}
        tools = [
            ("✏", "画笔", "pen"),
            ("🖍", "荧光笔", "highlighter"),
            ("—", "直线", "line"),
            ("▢", "矩形", "rect"),
            ("■", "填充矩形", "filled_rect"),
            ("○", "椭圆", "ellipse"),
            ("→", "箭头", "arrow"),
            ("T", "文字", "text"),
        ]
        for icon, tooltip, tool in tools:
            btn = QToolButton()
            btn.setText(icon)
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, t=tool: self._set_tool(t))
            tools_group.addWidget(btn)
            self.tool_buttons[tool] = btn
        
        # 橡皮擦按钮 - 带选项菜单
        eraser_btn = QToolButton()
        eraser_btn.setText("◯")
        eraser_btn.setToolTip("橡皮擦")
        eraser_btn.setCheckable(True)
        # 使用 InstantPopup 模式，点击即弹出菜单，并隐藏指示器箭头
        eraser_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        eraser_btn.setStyleSheet("QToolButton::menu-indicator { image: none; }")
        eraser_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # 点击按钮时立即选择橡皮擦工具
        eraser_btn.pressed.connect(lambda: self._set_tool('eraser'))
        tools_group.addWidget(eraser_btn)
        self.tool_buttons['eraser'] = eraser_btn
        
        # 创建橡皮选项菜单
        self._create_eraser_options_menu(eraser_btn)
        
        layout.addLayout(tools_group)

        self.tool_buttons['pen'].setChecked(True)
        self._add_separator(layout)

        # 颜色分组
        color_group = QHBoxLayout()
        color_group.setSpacing(6)
        colors = ["#FF4D4F", "#52C41A", "#1890FF", "#FADB14", "#722ED1", "#000000", "#FFFFFF"]
        for color in colors:
            btn = QToolButton()
            btn.setFixedSize(22, 22)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QToolButton {{
                    background: {color}; 
                    border: 2px solid rgba(0,0,0,0.1); 
                    border-radius: 11px;
                }}
                QToolButton:hover {{
                    border-color: white;
                    margin: -2px;
                }}
            """)
            btn.clicked.connect(lambda checked, c=color: self._set_color(c))
            color_group.addWidget(btn)
        
        # 自定义颜色选择器 (彩色色块)
        custom_color_btn = QToolButton()
        custom_color_btn.setFixedSize(22, 22)
        custom_color_btn.setToolTip("更多颜色...")
        custom_color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        custom_color_btn.setStyleSheet("""
            QToolButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #ff0000, stop:0.2 #ffff00, stop:0.4 #00ff00, 
                    stop:0.6 #00ffff, stop:0.8 #0000ff, stop:1 #ff00ff);
                border: 2px solid rgba(0,0,0,0.1);
                border-radius: 11px;
            }
            QToolButton:hover {
                border-color: white;
                margin: -2px;
            }
        """)
        custom_color_btn.clicked.connect(self._choose_custom_color)
        color_group.addWidget(custom_color_btn)
        
        layout.addLayout(color_group)

        self._add_separator(layout)

        # 宽度控制
        size_layout = QHBoxLayout()
        size_layout.setSpacing(5)
        size_layout.addWidget(QLabel("SIZE"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 30)
        self.width_spin.setValue(3)
        self.width_spin.valueChanged.connect(self.canvas.set_width)
        size_layout.addWidget(self.width_spin)
        layout.addLayout(size_layout)

        self._add_separator(layout)

        # 背景模式
        bg_layout = QHBoxLayout()
        bg_layout.setSpacing(4)
        bg_modes = [
            ("💠", "透明", "transparent"),
            ("⬜", "白色", "white"),
            ("⬛", "黑色", "black"),
        ]
        for icon, tooltip, mode in bg_modes:
            btn = QToolButton()
            btn.setText(icon)
            btn.setToolTip(f"{tooltip}背景")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, m=mode: self.canvas.set_background(m))
            bg_layout.addWidget(btn)
        layout.addLayout(bg_layout)

        self._add_separator(layout)

        # 操作工具（撤销、清空等）
        ops_layout = QHBoxLayout()
        ops_layout.setSpacing(4)
        
        undo_btn = QToolButton()
        undo_btn.setText("↩")
        undo_btn.setToolTip("撤销")
        undo_btn.clicked.connect(self.canvas.undo)
        ops_layout.addWidget(undo_btn)

        clear_btn = QToolButton()
        clear_btn.setText("🗑")
        clear_btn.setToolTip("清空")
        clear_btn.clicked.connect(self.canvas.clear)
        ops_layout.addWidget(clear_btn)
        layout.addLayout(ops_layout)

        layout.addStretch()

        # 功能区（最小化、保存、退出）
        func_layout = QHBoxLayout()
        func_layout.setSpacing(8)

        self.minimize_btn = QToolButton()
        self.minimize_btn.setText("🗕")
        self.minimize_btn.setToolTip("缩小工具栏")
        self.minimize_btn.clicked.connect(self._toggle_minimize)
        func_layout.addWidget(self.minimize_btn)

        save_btn = QToolButton()
        save_btn.setText("💾")
        save_btn.setToolTip("保存")
        save_btn.setStyleSheet("""
            QToolButton { 
                background: #0078D7; 
                color: white; 
                border-radius: 8px; 
                padding: 6px 12px;
                font-weight: bold;
            }
            QToolButton:hover { background: #005A9E; }
        """)
        save_btn.clicked.connect(self._save)
        func_layout.addWidget(save_btn)

        exit_btn = QToolButton()
        exit_btn.setText("✕")
        exit_btn.setToolTip("退出")
        exit_btn.setStyleSheet("""
            QToolButton { 
                background: #F44336; 
                color: white; 
                border-radius: 8px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QToolButton:hover { background: #D32F2F; }
        """)
        exit_btn.clicked.connect(self.close)
        func_layout.addWidget(exit_btn)
        layout.addLayout(func_layout)

        return toolbar

    def _add_separator(self, layout):
        sep = QFrame()
        sep.setFixedSize(1, 20)
        sep.setStyleSheet("background: rgba(0, 0, 0, 0.1);")
        layout.addWidget(sep)

    def _create_eraser_options_menu(self, parent_btn: QToolButton):
        """创建橡皮擦选项菜单"""
        menu = QMenu(parent_btn)
        menu.setStyleSheet("""
            QMenu {
                background: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 15px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #0078D7;
                color: white;
            }
        """)
        
        stroke_action = QAction("对象擦除", menu)
        stroke_action.setCheckable(True)
        stroke_action.setChecked(True)
        stroke_action.triggered.connect(lambda: self._on_eraser_mode_changed('stroke', menu, stroke_action, area_action))
        menu.addAction(stroke_action)
        
        area_action = QAction("局部擦除", menu)
        area_action.setCheckable(True)
        area_action.triggered.connect(lambda: self._on_eraser_mode_changed('area', menu, stroke_action, area_action))
        menu.addAction(area_action)
        
        menu.addSeparator()
        
        size_widget = QWidget(menu)
        size_layout = QHBoxLayout(size_widget)
        size_layout.setContentsMargins(5, 5, 5, 5)
        size_layout.setSpacing(5)
        
        size_layout.addWidget(QLabel("大小:"))
        self.eraser_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.eraser_size_slider.setRange(5, 100)
        self.eraser_size_slider.setValue(20)
        self.eraser_size_slider.setFixedWidth(100)
        self.eraser_size_slider.valueChanged.connect(self._on_eraser_size_changed)
        size_layout.addWidget(self.eraser_size_slider)
        
        self.eraser_size_label = QLabel("20")
        self.eraser_size_label.setFixedWidth(25)
        size_layout.addWidget(self.eraser_size_label)
        
        size_action = QWidgetAction(menu)
        size_action.setDefaultWidget(size_widget)
        menu.addAction(size_action)
        
        parent_btn.setMenu(menu)
        
        self._eraser_stroke_action = stroke_action
        self._eraser_area_action = area_action

    def _on_eraser_mode_changed(self, mode: str, menu: QMenu, stroke_action: QAction, area_action: QAction):
        """橡皮擦模式切换"""
        if mode == 'stroke':
            stroke_action.setChecked(True)
            area_action.setChecked(False)
        else:
            stroke_action.setChecked(False)
            area_action.setChecked(True)
        
        self.canvas.set_eraser_mode(mode)
        self._set_tool('eraser')
        menu.hide()

    def _on_eraser_size_changed(self, value: int):
        """橡皮擦大小改变"""
        self.eraser_size_label.setText(str(value))
        self.canvas.set_eraser_size(value)

    def _set_tool(self, tool: str):
        for name, btn in self.tool_buttons.items():
            btn.setChecked(name == tool)
        self.canvas.set_tool(tool)

    def _set_color(self, color: str):
        self.canvas.set_color(QColor(color))
        if self.canvas.current_tool == 'eraser':
            self._set_tool('pen')

    def _choose_custom_color(self):
        """打开颜色对话框选择自定义颜色"""
        color = PaletteWindow.getColor(self.canvas.pen_color, self, "调色板")
        if color.isValid():
            self.canvas.set_color(color)
            if self.canvas.current_tool == 'eraser':
                self._set_tool('pen')

    def _toggle_minimize(self):
        """切换缩小/放大状态"""
        if self._is_minimized:
            # 恢复全屏
            screen = QGuiApplication.primaryScreen().geometry()
            self.setGeometry(screen)
            self.canvas.show()
            self.minimize_btn.setText("🗕")
            self.minimize_btn.setToolTip("缩小工具栏")
            self._is_minimized = False
        else:
            # 缩小为工具栏
            self._normal_geometry = self.geometry()
            self.canvas.hide()
            # 调整窗口大小为工具栏大小
            self.setFixedHeight(40)
            self.resize(self.toolbar.sizeHint().width() + 20, 40)
            # 移动到屏幕顶部中央
            screen = QGuiApplication.primaryScreen().geometry()
            self.move((screen.width() - self.width()) // 2, 0)
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16777215, 16777215)
            self.minimize_btn.setText("🗖")
            self.minimize_btn.setToolTip("展开白板")
            self._is_minimized = True

    def _save(self):
        """保存白板内容"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存白板",
            f"whiteboard_{timestamp}.png",
            "PNG图像 (*.png);;PDF文件 (*.pdf)"
        )
        if file_path:
            if file_path.lower().endswith('.pdf'):
                self._save_pdf(file_path)
            else:
                self.canvas.get_pixmap().save(file_path)
            self._show_toast(f"已保存: {os.path.basename(file_path)}")

    def _save_pdf(self, path: str):
        """保存为PDF"""
        try:
            from PySide6.QtGui import QPdfWriter, QPageSize
            pm = self.canvas.get_pixmap()
            writer = QPdfWriter(path)
            writer.setPageSize(QPageSize(pm.size()))
            painter = QPainter(writer)
            painter.drawPixmap(0, 0, pm)
            painter.end()
        except Exception as e:
            ModernMessageBox.error(self, "保存失败", f"无法保存PDF: {str(e)}")

    def _show_toast(self, message: str):
        """显示Toast提示"""
        toast = QLabel(message, self)
        toast.setStyleSheet("""
            QLabel {
                background: rgba(0, 120, 215, 0.95);
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 12px;
            }
        """)
        toast.adjustSize()
        toast.move((self.width() - toast.width()) // 2, self.height() - 60)
        toast.show()
        QTimer.singleShot(2000, toast.deleteLater)

    def mousePressEvent(self, event):
        """支持拖动工具栏移动窗口"""
        if self._is_minimized and event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """拖动移动"""
        if self._is_minimized and event.buttons() & Qt.MouseButton.LeftButton:
            if hasattr(self, '_drag_pos'):
                self.move(event.globalPosition().toPoint() - self._drag_pos)
                event.accept()
        else:
            super().mouseMoveEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Z:
                self.canvas.undo()
            elif event.key() == Qt.Key.Key_S:
                self._save()

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)


# 兼容旧接口
class RegionWhiteboard(FullscreenWhiteboard):
    """区域白板"""
    def __init__(self, rect: QRect = None, config=None):
        super().__init__(config)
        if rect:
            self.setGeometry(rect)


WhiteboardWindow = FullscreenWhiteboard
