from PySide6.QtWidgets import (
    QLabel, QApplication
)
from PySide6.QtCore import Qt, Signal, QPoint, QRect, QRectF, QSize
from PySide6.QtGui import (
    QPixmap, QPainter, QColor, QPen, QBrush, QFont,
    QTransform, QImage, QPainterPath
)
import math
import numpy as np
import cv2

from ui.text_manager import TextManagerMixin

class DrawingCanvas(QLabel, TextManagerMixin):
    """绘图画布"""
    
    # 几何图形固定宽度
    FIXED_SHAPE_WIDTH = 3
    
    # 信号：文本框创建完成后发出，用于通知父窗口取消工具选中状态
    text_box_created = Signal()
    # 信号：OCR 选区完成，参数为选取的 QImage
    ocr_selection_done = Signal(QImage)

    def __init__(self, pixmap_or_image, parent=None):
        super().__init__(parent)
        # 转换为 QImage 以支持超大尺寸，不受 GPU 纹理限制 (QPixmap 通常限制在 32767px)
        if isinstance(pixmap_or_image, QPixmap):
            img = pixmap_or_image.toImage()
        else:
            img = pixmap_or_image
            
        self.initial_pixmap = img
        self.original_pixmap = img.copy()
        self.current_pixmap = img.copy()
        
        self.drawing = False
        self.last_point = QPoint()
        self.current_tool = 'move'  # 默认选择移动工具
        self.pen_color = QColor(255, 0, 0)
        self.pen_width = 3
        self.shape_start = QPoint()
        
        # 橡皮擦相关
        self.eraser_mode = 'stroke'  # 'stroke' = 擦除整条线条, 'area' = 擦除覆盖区域
        self.eraser_size = 20  # 橡皮大小（仅用于区域擦除模式）
        self.temp_pixmap = None
        self.font_size = 16

        # 初始历史记录
        self.history = [{
            'pixmap': self.current_pixmap.copy(),
            'original_pixmap': self.original_pixmap.copy(),
            'annotations': [],
            'rendered_texts': [],
            'adjustments': {"brightness": 0, "contrast": 0, "saturation": 0}
        }]
        self.history_index = 0
        self.max_history = 100
        self.setMouseTracking(True)
        
        # 标注图层
        self.annotations = []  # 存储所有绘图笔触
        self.current_stroke = None
        self.show_annotations = True
        
        # 移动工具相关
        self.moving = False
        self.move_start_pos = QPoint()
        self.image_offset = QPoint(0, 0)  # 图像偏移量
        self.canvas_bg_color = QColor(200, 200, 200)  # 画布背景色
        
        # 缩放相关
        self.zoom_level = 1.0  # 缩放级别 (0.1 - 5.0)
        self.min_zoom = 0.1
        self.max_zoom = 5.0
        
        # 初始化文本管理器 (Mixin)
        self.init_text_manager()
        
        # 裁剪模式相关
        self.crop_mode = False
        self.crop_rect = None  # 裁剪区域
        self.crop_handles = []  # 裁剪手柄
        self.dragging_crop = False
        self.resizing_crop = False
        self.creating_crop = False  # 是否正在创建新裁剪区域
        self.resize_handle = None  # 当前拖动的手柄
        self.crop_start_pos = QPoint()
        
        # OCR 选区相关
        self.ocr_mode = False
        self.ocr_rect = None
        self.ocr_start_pos = QPoint()
        
        # 已渲染文字记录（用于点击编辑）
        # 每项: {'text': str, 'image_pos': QPoint, 'font_size': int, 'color': QColor, 'rect': QRect, 'history_index': int}
        self.rendered_texts = []

        # 降采样预览优化相关
        self._is_previewing = False
        self._preview_scale = 1.0
        self._max_preview_size = 1200  # 预览时的最大长边尺寸
        self._downsampled_original = None
        self._current_adjustments = {"brightness": 0, "contrast": 0, "saturation": 0}
        self._first_show = True
    
    def resizeEvent(self, event):
        """窗口调整大小时，重新渲染图像"""
        super().resizeEvent(event)
        if event.size().width() > 0 and event.size().height() > 0:
            if hasattr(self, '_first_show') and self._first_show:
                self.zoom_fit()
                self._first_show = False
            else:
                if self.crop_mode:
                    self._update_crop_display()
                else:
                    self._update_zoomed_display()
    
    def setPixmap(self, pixmap_or_image):
        """支持设置 QPixmap 或 QImage，并统一触发缩放显示"""
        if isinstance(pixmap_or_image, QPixmap):
            self.current_pixmap = pixmap_or_image.toImage()
        else:
            self.current_pixmap = pixmap_or_image
            
        if self.crop_mode:
            self._update_crop_display()
        elif self.ocr_mode:
            self._update_ocr_display()
        else:
            self._update_zoomed_display()

    def set_tool(self, tool: str):
        self.current_tool = tool
        if self.ocr_mode:
            self.exit_ocr_mode()
        # 更新鼠标样式
        if tool == 'move':
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        elif tool == 'eraser':
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif tool == 'text':
            self.setCursor(Qt.CursorShape.IBeamCursor)
        elif tool == 'crop':
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)

    def set_color(self, color: QColor):
        self.pen_color = color

    def set_pen_width(self, width: int):
        self.pen_width = width
    
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

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # OCR 模式
            if self.ocr_mode:
                pos = self._get_image_pos(event.pos())
                self.ocr_start_pos = pos
                self.ocr_rect = QRect(pos, QSize(1, 1))
                self._update_ocr_display()
                return

            # 裁剪模式
            if self.crop_mode:
                pos = self._get_crop_pos(event.pos())
                handle = self._get_crop_handle_at(pos)
                if handle:
                    # 拖动手柄调整大小
                    self.resizing_crop = True
                    self.resize_handle = handle
                    self.crop_start_pos = pos
                    self.creating_crop = False
                elif self.crop_rect and self.crop_rect.contains(pos):
                    # 拖动裁剪区域
                    self.dragging_crop = True
                    self.crop_start_pos = pos
                    self.creating_crop = False
                else:
                    # 创建新的裁剪区域
                    self.creating_crop = True
                    self.crop_start_pos = pos
                    self.crop_rect = QRect(pos, QSize(1, 1))
                    self.dragging_crop = False
                    self.resizing_crop = False
                self._update_crop_display()
                return
            
            if self.current_tool == 'move':
                # 移动工具 - 先检查是否点击在已渲染的文字上
                image_pos = self._get_image_pos(event.pos())
                clicked_rendered_text = self._get_rendered_text_at(image_pos)
                if clicked_rendered_text:
                    # 点击了已渲染的文字，撤销并重新编辑
                    self._edit_rendered_text(clicked_rendered_text)
                    return
                # 没有点击文字，正常移动
                self.moving = True
                self.move_start_pos = event.pos()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            elif self.current_tool == 'text':
                # 文本工具 - 拖拽创建文本框
                widget_pos = event.pos()  # widget坐标，用于检测文本框
                image_pos = self._get_image_pos(widget_pos)  # 图像坐标，用于绘制预览
                
                # 检查是否点击在现有文本框上（使用widget坐标）
                clicked_on_textbox = False
                for text_box in self.text_boxes:
                    local_pos = text_box.mapFromParent(widget_pos)
                    if text_box.rect().contains(local_pos):
                        clicked_on_textbox = True
                        self._activate_text_box(text_box)
                        break
                
                if not clicked_on_textbox:
                    # 检查是否点击在已渲染的文字上
                    clicked_rendered_text = self._get_rendered_text_at(image_pos)
                    if clicked_rendered_text:
                        # 点击了已渲染的文字，撤销并重新编辑
                        self._edit_rendered_text(clicked_rendered_text)
                        return  # 直接返回，不触发创建新文本框
                    else:
                        # 点击空白区域，开始拖拽创建文本框
                        self.creating_text_box = True
                        self.text_box_start_pos = image_pos  # 使用图像坐标
                        self.text_box_preview_rect = QRect(image_pos, QSize(1, 1))
                        self.temp_pixmap = self.current_pixmap.copy()
            else:
                self.drawing = True
                pos = self._get_image_pos(event.pos())
                self.last_point = pos
                self.shape_start = pos
                self.temp_pixmap = self.current_pixmap.copy()
                
                # 开始记录新笔触
                if self.current_tool in ['pen', 'highlighter', 'blur_brush', 'pixelate_brush']:
                    self.current_stroke = {
                        'type': self.current_tool,
                        'points': [pos],
                        'color': QColor(self.pen_color) if self.current_tool in ['pen', 'highlighter'] else None,
                        'width': self.pen_width,
                        'sub_annotations': []  # 用于存储模糊/像素化的子块
                    }
                    # 支持点按绘制（单点）
                    if self.current_tool == 'pen':
                        self._draw_line(pos, pos)
                    elif self.current_tool == 'highlighter':
                        self._draw_highlighter(pos, pos)
                    elif self.current_tool == 'blur_brush':
                        self._apply_local_blur(pos, pos)
                    elif self.current_tool == 'pixelate_brush':
                        self._apply_local_pixelate(pos, pos)

    def mouseMoveEvent(self, event):
        # 记录鼠标位置用于绘制橡皮擦预览
        self.mouse_pos = event.pos()
        if self.current_tool == 'eraser':
            self.update()

        # OCR 模式
        if self.ocr_mode:
            if event.buttons() & Qt.MouseButton.LeftButton:
                pos = self._get_image_pos(event.pos())
                self.ocr_rect = QRect(self.ocr_start_pos, pos).normalized()
                # 限制在图像范围内
                img_rect = QRect(0, 0, self.current_pixmap.width(), self.current_pixmap.height())
                self.ocr_rect = self.ocr_rect.intersected(img_rect)
                self._update_ocr_display()
            return

        # 裁剪模式
        if self.crop_mode:
            pos = self._get_crop_pos(event.pos())
            if event.buttons() & Qt.MouseButton.LeftButton:
                if self.resizing_crop and self.crop_rect:
                    self._resize_crop_rect(pos)
                    self._update_crop_display()
                elif self.dragging_crop and self.crop_rect:
                    delta = pos - self.crop_start_pos
                    self.crop_rect.translate(delta.x(), delta.y())
                    # 限制在图像范围内
                    self._constrain_crop_rect()
                    self.crop_start_pos = pos
                    self._update_crop_display()
                elif self.creating_crop:
                    # 绘制新的裁剪区域
                    self.crop_rect = QRect(self.crop_start_pos, pos).normalized()
                    # 确保最小尺寸
                    if self.crop_rect.width() < 5:
                        self.crop_rect.setWidth(5)
                    if self.crop_rect.height() < 5:
                        self.crop_rect.setHeight(5)
                    self._constrain_crop_rect()
                    self._update_crop_display()
            else:
                # 更新鼠标样式
                handle = self._get_crop_handle_at(pos)
                if handle:
                    self._set_resize_cursor(handle)
                elif self.crop_rect and self.crop_rect.contains(pos):
                    self.setCursor(Qt.CursorShape.SizeAllCursor)
                else:
                    self.setCursor(Qt.CursorShape.CrossCursor)
            return
        
        pos = self._get_image_pos(event.pos())
        
        # 更新鼠标样式
        if self.current_tool == 'move' and not self.moving:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        
        if self.moving and event.buttons() & Qt.MouseButton.LeftButton:
            # 移动图像
            delta = event.pos() - self.move_start_pos
            self.image_offset += delta
            self.move_start_pos = event.pos()
            self._update_canvas_with_offset()
        elif self.creating_text_box and event.buttons() & Qt.MouseButton.LeftButton:
            # 拖拽创建文本框预览
            self.text_box_preview_rect = QRect(self.text_box_start_pos, pos).normalized()
            # 确保最小尺寸
            if self.text_box_preview_rect.width() < 20:
                self.text_box_preview_rect.setWidth(20)
            if self.text_box_preview_rect.height() < 20:
                self.text_box_preview_rect.setHeight(20)
            self._draw_text_box_preview()
        elif self.drawing and event.buttons() & Qt.MouseButton.LeftButton:
            if self.current_tool == 'pen':
                self._draw_line(self.last_point, pos)
                if self.current_stroke:
                    self.current_stroke['points'].append(pos)
                self.last_point = pos
            elif self.current_tool == 'highlighter':
                self._draw_highlighter(self.last_point, pos)
                if self.current_stroke:
                    self.current_stroke['points'].append(pos)
                self.last_point = pos
            elif self.current_tool == 'eraser':
                self._erase(pos)
                self.last_point = pos
            elif self.current_tool == 'blur_brush':
                self._apply_local_blur(self.last_point, pos)
                self.last_point = pos
            elif self.current_tool == 'pixelate_brush':
                self._apply_local_pixelate(self.last_point, pos)
                self.last_point = pos
            elif self.current_tool in ['rect', 'ellipse', 'arrow', 'line', 'filled_rect', 'filled_ellipse']:
                self._draw_shape_preview(pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # OCR 模式
            if self.ocr_mode:
                if self.ocr_rect and not self.ocr_rect.isNull() and self.ocr_rect.width() > 5 and self.ocr_rect.height() > 5:
                    # 裁剪选取的图像并发出信号
                    selected_img = self.current_pixmap.copy(self.ocr_rect)
                    self.ocr_selection_done.emit(selected_img)
                    self.exit_ocr_mode()
                return

            # 裁剪模式
            if self.crop_mode:
                self.dragging_crop = False
                self.resizing_crop = False
                self.resize_handle = None
                self.creating_crop = False
                # 通知父窗口更新尺寸显示
                self._notify_crop_changed()
                return
            
            if self.moving:
                self.moving = False
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            elif self.creating_text_box:
                # 完成文本框拖拽创建
                self.creating_text_box = False
                # 先恢复原始图像（清除预览框）
                if self.temp_pixmap:
                    self.current_pixmap = self.temp_pixmap.copy()
                if self.text_box_preview_rect and self.text_box_preview_rect.width() >= 30 and self.text_box_preview_rect.height() >= 30:
                    # 创建指定大小的文本框
                    self._add_text_with_size(self.text_box_preview_rect)
                else:
                    # 拖拽区域太小，创建默认大小的文本框
                    self._add_text(self.text_box_start_pos)
                self.text_box_preview_rect = None
                self.temp_pixmap = None
                # 恢复显示
                self.setPixmap(self.current_pixmap)
                # 发出信号，通知父窗口取消文本工具选中状态
                self.text_box_created.emit()
                # 重置当前工具为移动工具
                self.current_tool = 'move'
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            elif self.drawing:
                self.drawing = False
                pos = self._get_image_pos(event.pos())
                
                # 结束并保存笔触
                if self.current_tool in ['pen', 'highlighter', 'blur_brush', 'pixelate_brush'] and self.current_stroke:
                    # 计算包围盒以便快速擦除
                    if 'points' in self.current_stroke and self.current_stroke['points']:
                        points = self.current_stroke['points']
                        xs = [p.x() for p in points]
                        ys = [p.y() for p in points]
                        self.current_stroke['bbox'] = QRect(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
                    elif 'sub_annotations' in self.current_stroke and self.current_stroke['sub_annotations']:
                        rects = [sub['rect'] for sub in self.current_stroke['sub_annotations']]
                        unified = rects[0]
                        for r in rects[1:]:
                            unified = unified.united(r)
                        self.current_stroke['bbox'] = unified
                    
                    self.annotations.append(self.current_stroke)
                    self.current_stroke = None
                    self._save_to_history()
                elif self.current_tool in ['rect', 'ellipse', 'arrow', 'line', 'filled_rect', 'filled_ellipse']:
                    self._draw_shape_final(pos)
                    # 几何图形使用固定宽度
                    draw_width = self.FIXED_SHAPE_WIDTH
                    # 将形状加入 annotations 以便被删除
                    shape_data = {
                        'type': self.current_tool,
                        'start': self.shape_start,
                        'end': pos,
                        'color': QColor(self.pen_color),
                        'width': draw_width,
                        'bbox': QRect(self.shape_start, pos).normalized()
                    }
                    self.annotations.append(shape_data)
                    self._save_to_history()
                else:
                    self._save_to_history()
    
    # ========== 裁剪功能 ==========
    
    def _get_crop_pos(self, widget_pos: QPoint) -> QPoint:
        """获取裁剪模式下的图像坐标（考虑缩放和偏移）"""
        if self.current_pixmap.isNull():
            return QPoint(0, 0)
        
        # 计算缩放后的图像尺寸
        scaled_width = int(self.current_pixmap.width() * self.zoom_level)
        scaled_height = int(self.current_pixmap.height() * self.zoom_level)
        
        # 计算图像在widget中的位置（居中 + 偏移）
        wr = self.rect()
        img_display_x = (wr.width() - scaled_width) // 2 + self.image_offset.x()
        img_display_y = (wr.height() - scaled_height) // 2 + self.image_offset.y()
        
        # 转换鼠标位置到缩放后图像的坐标
        scaled_img_x = widget_pos.x() - img_display_x
        scaled_img_y = widget_pos.y() - img_display_y
        
        # 转换回原图坐标
        if self.zoom_level != 1.0:
            img_x = int(scaled_img_x / self.zoom_level)
            img_y = int(scaled_img_y / self.zoom_level)
        else:
            img_x = scaled_img_x
            img_y = scaled_img_y
        
        # 限制在图像范围内
        img_x = max(0, min(img_x, self.current_pixmap.width() - 1))
        img_y = max(0, min(img_y, self.current_pixmap.height() - 1))
        
        return QPoint(img_x, img_y)
    
    def _notify_crop_changed(self):
        """通知父窗口裁剪区域已改变"""
        parent = self.parent()
        while parent:
            if hasattr(parent, '_update_crop_size_display'):
                parent._update_crop_size_display()
                break
            parent = parent.parent()
    
    def enter_crop_mode(self):
        """进入裁剪模式"""
        if self.ocr_mode:
            self.exit_ocr_mode()
        self.crop_mode = True
        self.creating_crop = False
        self.dragging_crop = False
        self.resizing_crop = False
        # 默认选中整个图像
        self.crop_rect = QRect(0, 0, self.current_pixmap.width(), self.current_pixmap.height())
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._update_crop_display()
        self._notify_crop_changed()
    
    def exit_crop_mode(self, apply: bool = False):
        """退出裁剪模式"""
        if apply and self.crop_rect and not self.crop_rect.isEmpty():
            # 应用裁剪
            self.crop_to_rect(self.crop_rect)
        
        self.crop_mode = False
        self.crop_rect = None
        self.dragging_crop = False
        self.resizing_crop = False
        self.creating_crop = False
        self.resize_handle = None
        # 恢复正常显示
        self.setPixmap(self.current_pixmap)
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def enter_ocr_mode(self):
        """进入 OCR 选区模式"""
        if self.crop_mode:
            self.exit_crop_mode()
        self.ocr_mode = True
        self.ocr_rect = None
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._update_ocr_display()

    def exit_ocr_mode(self):
        """退出 OCR 选区模式"""
        self.ocr_mode = False
        self.ocr_rect = None
        # 恢复正常显示
        self._update_zoomed_display()
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def _update_ocr_display(self):
        """更新 OCR 选区模式下的显示"""
        if not self.ocr_mode or self.current_pixmap.isNull():
            return
        
        display_size = self.size()
        if display_size.width() <= 0 or display_size.height() <= 0:
            return

        # 创建显示画布
        display = QPixmap(display_size)
        display.fill(self.canvas_bg_color)
        
        painter = QPainter(display)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # 计算图像显示参数
        full_scaled_width = int(self.current_pixmap.width() * self.zoom_level)
        full_scaled_height = int(self.current_pixmap.height() * self.zoom_level)
        base_x = (display_size.width() - full_scaled_width) // 2 + self.image_offset.x()
        base_y = (display_size.height() - full_scaled_height) // 2 + self.image_offset.y()
        
        # 绘制背景图像
        image_pixmap = QPixmap.fromImage(self.current_pixmap)
        painter.drawPixmap(base_x, base_y, full_scaled_width, full_scaled_height, image_pixmap)
        
        # 如果有选区，绘制选区效果
        if self.ocr_rect and not self.ocr_rect.isNull():
            # 计算缩放后的选区
            scaled_ocr_rect = QRect(
                base_x + int(self.ocr_rect.left() * self.zoom_level),
                base_y + int(self.ocr_rect.top() * self.zoom_level),
                int(self.ocr_rect.width() * self.zoom_level),
                int(self.ocr_rect.height() * self.zoom_level)
            )
            
            # 1. 遮罩层 (半透明黑色)
            painter.setBrush(QColor(0, 0, 0, 100))
            painter.setPen(Qt.PenStyle.NoPen)
            
            # 绘制选区外部的四个矩形
            # 上
            painter.drawRect(base_x, base_y, full_scaled_width, scaled_ocr_rect.top() - base_y)
            # 下
            painter.drawRect(base_x, scaled_ocr_rect.bottom() + 1, full_scaled_width, base_y + full_scaled_height - scaled_ocr_rect.bottom() - 1)
            # 左
            painter.drawRect(base_x, scaled_ocr_rect.top(), scaled_ocr_rect.left() - base_x, scaled_ocr_rect.height() + 1)
            # 右
            painter.drawRect(scaled_ocr_rect.right() + 1, scaled_ocr_rect.top(), base_x + full_scaled_width - scaled_ocr_rect.right() - 1, scaled_ocr_rect.height() + 1)
            
            # 2. 选区边框 (蓝色)
            pen = QPen(QColor(59, 130, 246), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(scaled_ocr_rect)
            
            # 3. 选区内部高亮
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        else:
            # 没有选区时，整体变暗一点，提示用户开始选择
            painter.setBrush(QColor(0, 0, 0, 50))
            painter.drawRect(base_x, base_y, full_scaled_width, full_scaled_height)

        painter.end()
        super().setPixmap(display)
    
    def _get_crop_handles(self) -> list:
        """获取裁剪区域的8个手柄位置（原图坐标系）"""
        if not self.crop_rect:
            return []
        
        r = self.crop_rect
        # 根据缩放级别调整手柄检测大小
        handle_size = max(12, int(16 / self.zoom_level))
        hs = handle_size // 2
        
        return [
            ('tl', QRect(r.left() - hs, r.top() - hs, handle_size, handle_size)),
            ('t', QRect(r.center().x() - hs, r.top() - hs, handle_size, handle_size)),
            ('tr', QRect(r.right() - hs, r.top() - hs, handle_size, handle_size)),
            ('l', QRect(r.left() - hs, r.center().y() - hs, handle_size, handle_size)),
            ('r', QRect(r.right() - hs, r.center().y() - hs, handle_size, handle_size)),
            ('bl', QRect(r.left() - hs, r.bottom() - hs, handle_size, handle_size)),
            ('b', QRect(r.center().x() - hs, r.bottom() - hs, handle_size, handle_size)),
            ('br', QRect(r.right() - hs, r.bottom() - hs, handle_size, handle_size)),
        ]
    
    def _get_crop_handle_at(self, pos: QPoint) -> str:
        """获取指定位置的手柄（原图坐标系）"""
        for handle_name, handle_rect in self._get_crop_handles():
            # 扩大检测范围
            expanded_rect = handle_rect.adjusted(-3, -3, 3, 3)
            if expanded_rect.contains(pos):
                return handle_name
        return None
    
    def _set_resize_cursor(self, handle: str):
        """根据手柄设置鼠标样式"""
        cursors = {
            'tl': Qt.CursorShape.SizeFDiagCursor,
            'br': Qt.CursorShape.SizeFDiagCursor,
            'tr': Qt.CursorShape.SizeBDiagCursor,
            'bl': Qt.CursorShape.SizeBDiagCursor,
            't': Qt.CursorShape.SizeVerCursor,
            'b': Qt.CursorShape.SizeVerCursor,
            'l': Qt.CursorShape.SizeHorCursor,
            'r': Qt.CursorShape.SizeHorCursor,
        }
        self.setCursor(cursors.get(handle, Qt.CursorShape.ArrowCursor))
    
    def _resize_crop_rect(self, pos: QPoint):
        """调整裁剪区域大小"""
        if not self.crop_rect or not self.resize_handle:
            return
        
        r = self.crop_rect
        handle = self.resize_handle
        
        if 'l' in handle:
            r.setLeft(min(pos.x(), r.right() - 10))
        if 'r' in handle:
            r.setRight(max(pos.x(), r.left() + 10))
        if 't' in handle:
            r.setTop(min(pos.y(), r.bottom() - 10))
        if 'b' in handle:
            r.setBottom(max(pos.y(), r.top() + 10))
        
        self._constrain_crop_rect()
    
    def _constrain_crop_rect(self):
        """限制裁剪区域在图像范围内"""
        if not self.crop_rect or self.current_pixmap.isNull():
            return
        
        img_width = self.current_pixmap.width()
        img_height = self.current_pixmap.height()
        
        # 限制左边界
        if self.crop_rect.left() < 0:
            self.crop_rect.setLeft(0)
        # 限制上边界
        if self.crop_rect.top() < 0:
            self.crop_rect.setTop(0)
        # 限制右边界
        if self.crop_rect.right() >= img_width:
            self.crop_rect.setRight(img_width - 1)
        # 限制下边界
        if self.crop_rect.bottom() >= img_height:
            self.crop_rect.setBottom(img_height - 1)
        
        # 确保最小尺寸
        if self.crop_rect.width() < 10:
            self.crop_rect.setWidth(10)
        if self.crop_rect.height() < 10:
            self.crop_rect.setHeight(10)
    
    def _update_crop_display(self):
        """更新裁剪模式的显示（考虑缩放和偏移 - 优化版：仅渲染可见区域）"""
        if not self.crop_mode or self.current_pixmap.isNull():
            return
        
        display_size = self.size()
        if display_size.width() <= 0 or display_size.height() <= 0:
            return

        # 创建显示画布
        display = QPixmap(display_size)
        display.fill(self.canvas_bg_color)
        
        painter = QPainter(display)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # 计算全尺寸缩放后的大小
        full_scaled_width = int(self.current_pixmap.width() * self.zoom_level)
        full_scaled_height = int(self.current_pixmap.height() * self.zoom_level)
        
        # 计算图像基准位置
        base_x = (display_size.width() - full_scaled_width) // 2 + self.image_offset.x()
        base_y = (display_size.height() - full_scaled_height) // 2 + self.image_offset.y()
        
        # 1. 渲染图像可见区域 (复用 _update_zoomed_display 的逻辑)
        view_rect = QRect(0, 0, display_size.width(), display_size.height())
        image_rect_scaled = QRect(base_x, base_y, full_scaled_width, full_scaled_height)
        visible_rect_in_widget = view_rect.intersected(image_rect_scaled)
        
        if not visible_rect_in_widget.isEmpty():
            src_x_scaled = visible_rect_in_widget.x() - base_x
            src_y_scaled = visible_rect_in_widget.y() - base_y
            
            src_x = int(src_x_scaled / self.zoom_level)
            src_y = int(src_y_scaled / self.zoom_level)
            src_w = int(visible_rect_in_widget.width() / self.zoom_level) + 1
            src_h = int(visible_rect_in_widget.height() / self.zoom_level) + 1
            
            src_x = max(0, min(src_x, self.current_pixmap.width() - 1))
            src_y = max(0, min(src_y, self.current_pixmap.height() - 1))
            src_w = min(src_w, self.current_pixmap.width() - src_x)
            src_h = min(src_h, self.current_pixmap.height() - src_y)
            
            if src_w > 0 and src_h > 0:
                source_roi = self.current_pixmap.copy(src_x, src_y, src_w, src_h)
                
                target_w = int(src_w * self.zoom_level)
                target_h = int(src_h * self.zoom_level)
                
                if target_w > 0 and target_h > 0:
                    # QImage -> QPixmap (小区域转换)
                    scaled_roi = QPixmap.fromImage(source_roi.scaled(
                        target_w, target_h,
                        Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    ))
                    
                    draw_x = base_x + int(src_x * self.zoom_level)
                    draw_y = base_y + int(src_y * self.zoom_level)
                    painter.drawPixmap(draw_x, draw_y, scaled_roi)

        # 2. 绘制裁剪遮罩和裁剪框
        if self.crop_rect:
            # 将裁剪框坐标转换为显示坐标
            display_crop_rect = QRect(
                int(base_x + self.crop_rect.x() * self.zoom_level),
                int(base_y + self.crop_rect.y() * self.zoom_level),
                int(self.crop_rect.width() * self.zoom_level),
                int(self.crop_rect.height() * self.zoom_level)
            )
            
            # 绘制半透明遮罩（裁剪区域外 - 更深的遮罩）
            mask_color = QColor(0, 0, 0, 150)
            
            # 上方区域
            if display_crop_rect.top() > base_y:
                painter.fillRect(base_x, base_y, full_scaled_width, 
                               display_crop_rect.top() - base_y, mask_color)
            # 下方区域
            if display_crop_rect.bottom() < base_y + full_scaled_height:
                painter.fillRect(base_x, display_crop_rect.bottom(), full_scaled_width,
                               base_y + full_scaled_height - display_crop_rect.bottom(), mask_color)
            # 左侧区域
            if display_crop_rect.left() > base_x:
                painter.fillRect(base_x, display_crop_rect.top(), 
                               display_crop_rect.left() - base_x, display_crop_rect.height(), mask_color)
            # 右侧区域
            if display_crop_rect.right() < base_x + full_scaled_width:
                painter.fillRect(display_crop_rect.right(), display_crop_rect.top(),
                               base_x + full_scaled_width - display_crop_rect.right(),
                               display_crop_rect.height(), mask_color)
            
            # 绘制裁剪边框 (使用主题色)
            pen = QPen(QColor("#3b82f6"), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(display_crop_rect)
            
            # 绘制三分线（九宫格 - 更淡雅的白色）
            pen.setWidth(1)
            pen.setColor(QColor(255, 255, 255, 120))
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            
            w = display_crop_rect.width()
            h = display_crop_rect.height()
            x = display_crop_rect.x()
            y = display_crop_rect.y()
            
            if w > 30 and h > 30:  # 只在足够大时绘制九宫格
                # 垂直线
                painter.drawLine(x + w // 3, y, x + w // 3, y + h)
                painter.drawLine(x + 2 * w // 3, y, x + 2 * w // 3, y + h)
                # 水平线
                painter.drawLine(x, y + h // 3, x + w, y + h // 3)
                painter.drawLine(x, y + 2 * h // 3, x + w, y + 2 * h // 3)
            
            # 绘制手柄（圆形手柄，带阴影效果）
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            pen.setColor(QColor("#3b82f6"))
            pen.setWidth(2)
            pen.setStyle(Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            
            handle_size = 10
            hs = handle_size // 2
            handles = [
                QRect(display_crop_rect.left() - hs, display_crop_rect.top() - hs, handle_size, handle_size),
                QRect(display_crop_rect.center().x() - hs, display_crop_rect.top() - hs, handle_size, handle_size),
                QRect(display_crop_rect.right() - hs, display_crop_rect.top() - hs, handle_size, handle_size),
                QRect(display_crop_rect.left() - hs, display_crop_rect.center().y() - hs, handle_size, handle_size),
                QRect(display_crop_rect.right() - hs, display_crop_rect.center().y() - hs, handle_size, handle_size),
                QRect(display_crop_rect.left() - hs, display_crop_rect.bottom() - hs, handle_size, handle_size),
                QRect(display_crop_rect.center().x() - hs, display_crop_rect.bottom() - hs, handle_size, handle_size),
                QRect(display_crop_rect.right() - hs, display_crop_rect.bottom() - hs, handle_size, handle_size),
            ]
            
            # 开启抗锯齿绘制圆形手柄
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            for handle_rect in handles:
                painter.drawEllipse(handle_rect)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        
        painter.end()
        super().setPixmap(display)
    
    def _update_canvas_with_offset(self):
        """根据偏移量更新画布显示 - 直接调用优化后的更新方法"""
        if self.crop_mode:
            self._update_crop_display()
        else:
            self._update_zoomed_display()
        self._update_text_boxes_transform()
    
    def reset_position(self):
        """重置图像位置到中心"""
        self.image_offset = QPoint(0, 0)
        self.setPixmap(self.current_pixmap)

    def _get_widget_pos(self, image_pos: QPoint) -> QPoint:
        """将图像坐标转换为widget坐标（考虑缩放和偏移）"""
        if self.current_pixmap.isNull():
            return image_pos
        
        # 计算缩放后的图像尺寸
        scaled_width = int(self.current_pixmap.width() * self.zoom_level)
        scaled_height = int(self.current_pixmap.height() * self.zoom_level)
        
        # 计算图像在widget中的位置（居中 + 偏移）
        wr = self.rect()
        img_display_x = (wr.width() - scaled_width) // 2 + self.image_offset.x()
        img_display_y = (wr.height() - scaled_height) // 2 + self.image_offset.y()
        
        # 将图像坐标转换为缩放后的坐标
        scaled_x = int(image_pos.x() * self.zoom_level)
        scaled_y = int(image_pos.y() * self.zoom_level)
        
        # 加上图像显示偏移
        widget_x = scaled_x + img_display_x
        widget_y = scaled_y + img_display_y
        
        return QPoint(widget_x, widget_y)

    def _get_image_pos(self, widget_pos: QPoint) -> QPoint:
        """将widget坐标转换为图像坐标（考虑缩放和偏移）"""
        if self.current_pixmap.isNull():
            return QPoint(0, 0)
        
        # 计算缩放后的图像尺寸
        scaled_width = int(self.current_pixmap.width() * self.zoom_level)
        scaled_height = int(self.current_pixmap.height() * self.zoom_level)
        
        # 计算图像在widget中的位置（居中 + 偏移）
        wr = self.rect()
        img_display_x = (wr.width() - scaled_width) // 2 + self.image_offset.x()
        img_display_y = (wr.height() - scaled_height) // 2 + self.image_offset.y()
        
        # 转换鼠标位置到缩放后图像的坐标
        scaled_img_x = widget_pos.x() - img_display_x
        scaled_img_y = widget_pos.y() - img_display_y
        
        # 转换回原图坐标
        if self.zoom_level != 0:
            img_x = int(scaled_img_x / self.zoom_level)
            img_y = int(scaled_img_y / self.zoom_level)
        else:
            img_x = scaled_img_x
            img_y = scaled_img_y
        
        # 限制在图像范围内
        img_x = max(0, min(img_x, self.current_pixmap.width() - 1))
        img_y = max(0, min(img_y, self.current_pixmap.height() - 1))
        
        return QPoint(img_x, img_y)

    def _draw_line(self, start: QPoint, end: QPoint):
        """画笔效果 - 优化为路径绘制"""
        if not self.current_stroke or not self.temp_pixmap:
            # 回退到简单的增量绘制以防万一
            painter = QPainter(self.current_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(self.pen_color, self.pen_width, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(start, end)
            painter.end()
            self.setPixmap(self.current_pixmap)
            return

        # 恢复到笔触开始前的状态并重绘整个路径
        self.current_pixmap = self.temp_pixmap.copy()
        painter = QPainter(self.current_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self.pen_color, self.pen_width, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        
        path = QPainterPath()
        points = self.current_stroke['points']
        if points:
            path.moveTo(points[0])
            for p in points[1:]:
                path.lineTo(p)
            path.lineTo(end)
        else:
            path.moveTo(start)
            path.lineTo(end)
            
        painter.drawPath(path)
        painter.end()
        self.setPixmap(self.current_pixmap)
    
    def _draw_highlighter(self, start: QPoint, end: QPoint):
        """荧光笔效果 - 优化为路径绘制以避免透明度重叠（小圆球问题）"""
        if not self.current_stroke or not self.temp_pixmap:
            # 回退到简单的增量绘制
            painter = QPainter(self.current_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            color = QColor(self.pen_color)
            color.setAlpha(80)
            pen = QPen(color, self.pen_width * 3, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(start, end)
            painter.end()
            self.setPixmap(self.current_pixmap)
            return

        # 恢复到笔触开始前的状态并重绘整个路径
        self.current_pixmap = self.temp_pixmap.copy()
        painter = QPainter(self.current_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = QColor(self.pen_color)
        color.setAlpha(80)
        pen = QPen(color, self.pen_width * 3, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        
        path = QPainterPath()
        points = self.current_stroke['points']
        if points:
            path.moveTo(points[0])
            for p in points[1:]:
                path.lineTo(p)
            path.lineTo(end)
        else:
            path.moveTo(start)
            path.lineTo(end)
            
        painter.drawPath(path)
        painter.end()
        self.setPixmap(self.current_pixmap)

    def _redraw_from_annotations(self):
        """从标注列表重绘图像 - 性能优化版"""
        # 恢复到基础图像
        if self.history:
            self.current_pixmap = self.history[0]['pixmap'].copy()
        else:
            self.current_pixmap = self.original_pixmap.copy()
            
        painter = QPainter(self.current_pixmap)
        # 仅在非移动/非缩放时开启高质量渲染，提升交互流畅度
        if not getattr(self, 'moving', False):
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 预先创建通用的 Pen 对象，减少循环内对象创建
        pen_cache = {}
        
        for ann in self.annotations:
            ann_type = ann['type']
            if ann_type in ['pen', 'highlighter']:
                color = QColor(ann['color'])
                if ann_type == 'highlighter':
                    color.setAlpha(80)
                width = ann['width']
                if ann_type == 'highlighter':
                    width *= 3
                
                # 使用缓存的 Pen
                cache_key = (color.rgba(), width)
                if cache_key not in pen_cache:
                    pen_cache[cache_key] = QPen(color, width, Qt.PenStyle.SolidLine,
                                               Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen_cache[cache_key])
                
                points = ann['points']
                if len(points) > 1:
                    path = QPainterPath()
                    path.moveTo(points[0])
                    for p in points[1:]:
                        path.lineTo(p)
                    painter.drawPath(path)
                elif len(points) == 1:
                    painter.drawPoint(points[0])
            elif ann_type in ['rect', 'ellipse', 'arrow', 'line', 'filled_rect', 'filled_ellipse']:
                painter.setPen(QPen(ann['color'], ann['width']))
                rect = QRect(ann['start'], ann['end']).normalized()
                
                if ann_type == 'rect':
                    painter.drawRect(rect)
                elif ann_type == 'filled_rect':
                    painter.setBrush(QBrush(ann['color']))
                    painter.drawRect(rect)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                elif ann_type == 'ellipse':
                    painter.drawEllipse(rect)
                elif ann_type == 'filled_ellipse':
                    painter.setBrush(QBrush(ann['color']))
                    painter.drawEllipse(rect)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                elif ann_type == 'arrow':
                    self._draw_arrow(painter, ann['start'], ann['end'])
                elif ann_type == 'line':
                    painter.drawLine(ann['start'], ann['end'])
            elif ann_type in ['blur', 'pixelate']:
                painter.drawPixmap(ann['rect'], ann['pixmap'])
            elif ann_type in ['blur_brush', 'pixelate_brush']:
                for sub in ann.get('sub_annotations', []):
                    painter.drawPixmap(sub['rect'], sub['pixmap'])
        
        painter.end()
        self.setPixmap(self.current_pixmap)

    def paintEvent(self, event):
        """重写绘制事件以显示橡皮擦预览"""
        super().paintEvent(event)
        
        # 仅在橡皮擦工具、区域擦除模式且非裁剪模式下绘制预览
        if self.current_tool == 'eraser' and getattr(self, 'eraser_mode', 'stroke') == 'area' and not self.crop_mode and hasattr(self, 'mouse_pos'):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # 绘制橡皮擦圆形预览
            eraser_size_scaled = self.eraser_size * self.zoom_level
            rect = QRectF(
                self.mouse_pos.x() - eraser_size_scaled / 2,
                self.mouse_pos.y() - eraser_size_scaled / 2,
                eraser_size_scaled,
                eraser_size_scaled
            )
            
            # 绘制外边框（浅色）
            painter.setPen(QPen(QColor(255, 255, 255, 180), 1))
            painter.drawEllipse(rect)
            
            # 绘制内边框（深色，增加对比度）
            painter.setPen(QPen(QColor(0, 0, 0, 100), 1))
            painter.drawEllipse(rect.adjusted(1, 1, -1, -1))
            
            painter.end()

    def _erase(self, pos: QPoint):
        """橡皮擦 - 根据模式擦除 (增加路径插值以提高灵敏度)"""
        if not self.annotations:
            return

        # 计算距离
        dist = math.sqrt((pos.x() - self.last_point.x())**2 + (pos.y() - self.last_point.y())**2)
        
        # 决定插值步长：对象擦除使用较小步长，区域擦除根据橡皮大小调整
        step_size = 5 if self.eraser_mode == 'stroke' else max(2, self.eraser_size / 5)
        
        # 如果移动距离较大，进行插值处理
        if dist > step_size:
            steps = int(dist / step_size) + 1
            for i in range(1, steps + 1):
                interp_pos = QPoint(
                    int(self.last_point.x() + (pos.x() - self.last_point.x()) * i / steps),
                    int(self.last_point.y() + (pos.y() - self.last_point.y()) * i / steps)
                )
                if self.eraser_mode == 'area':
                    self._erase_area(interp_pos)
                else:
                    self._erase_stroke(interp_pos)
        else:
            if self.eraser_mode == 'area':
                self._erase_area(pos)
            else:
                self._erase_stroke(pos)

    def _point_to_segment_dist_sq(self, p, a, b):
        """计算点 p 到线段 ab 的距离平方"""
        dx = b.x() - a.x()
        dy = b.y() - a.y()
        l2 = dx*dx + dy*dy
        if l2 == 0:
            return (p.x() - a.x())**2 + (p.y() - a.y())**2
        t = ((p.x() - a.x()) * dx + (p.y() - a.y()) * dy) / l2
        t = max(0, min(1, t))
        proj_x = a.x() + t * dx
        proj_y = a.y() + t * dy
        return (p.x() - proj_x)**2 + (p.y() - proj_y)**2

    def _erase_stroke(self, pos: QPoint):
        """擦除整条线条模式 - 优化碰撞检测"""
        # 提高感应灵敏度，使其更容易擦除
        sensitivity = max(15, self.pen_width * 2.5)
        sensitivity_sq = sensitivity ** 2
        
        removed_any = False
        new_annotations = []
        
        for ann in self.annotations:
            should_remove = False
            
            bbox = ann.get('bbox')
            if bbox:
                # 预检查包围盒，加快速度
                if not bbox.adjusted(-sensitivity, -sensitivity, sensitivity, sensitivity).contains(pos):
                    new_annotations.append(ann)
                    continue

            if ann['type'] in ['pen', 'highlighter']:
                points = ann['points']
                # 检查所有线段，确保不会遗漏长直线
                for i in range(1, len(points)):
                    if self._point_to_segment_dist_sq(pos, points[i-1], points[i]) < sensitivity_sq:
                        should_remove = True
                        break
                # 检查单点笔触
                if not should_remove and len(points) == 1:
                    if (points[0].x() - pos.x())**2 + (points[0].y() - pos.y())**2 < sensitivity_sq:
                        should_remove = True
            elif ann['type'] in ['rect', 'ellipse', 'arrow', 'line', 'filled_rect', 'filled_ellipse']:
                rect = QRect(ann['start'], ann['end']).normalized()
                if rect.adjusted(-sensitivity, -sensitivity, sensitivity, sensitivity).contains(pos):
                    should_remove = True
            elif ann['type'] in ['blur', 'pixelate']:
                if ann['rect'].contains(pos):
                    should_remove = True
            elif ann['type'] in ['blur_brush', 'pixelate_brush']:
                for sub in ann.get('sub_annotations', []):
                    if sub['rect'].contains(pos):
                        should_remove = True
                        break
            
            if should_remove:
                removed_any = True
            else:
                new_annotations.append(ann)
        
        if removed_any:
            # 清除 Pen/Brush 缓存，因为标注列表发生了变化
            if hasattr(self, '_pen_cache'):
                self._pen_cache.clear()
            
            self.annotations = new_annotations
            self._redraw_from_annotations()

    def _get_line_circle_intersections(self, p1, p2, center, radius):
        """计算线段 p1p2 与圆 (center, radius) 的交点"""
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        a = dx*dx + dy*dy
        if a == 0:
            return []
            
        fx = p1.x() - center.x()
        fy = p1.y() - center.y()
        
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
            intersections.append(QPoint(int(p1.x() + t1 * dx), int(p1.y() + t1 * dy)))
        if 0 <= t2 <= 1:
            intersections.append(QPoint(int(p1.x() + t2 * dx), int(p1.y() + t2 * dy)))
            
        # 按 t 值排序确保顺序
        if len(intersections) == 2 and t1 > t2:
            intersections.reverse()
            
        return intersections

    def _erase_area(self, pos: QPoint):
        """局部擦除模式 - 擦除标注内容 (像素级精确裁剪版)"""
        eraser_size = self.eraser_size
        eraser_radius = eraser_size / 2
        eraser_radius_sq = eraser_radius ** 2
        removed_any = False
        new_annotations = []
        
        # 预先计算擦除区域矩形，用于快速过滤
        erase_rect = QRect(
            int(pos.x() - eraser_radius),
            int(pos.y() - eraser_radius),
            int(eraser_size),
            int(eraser_size)
        )
        
        for ann in self.annotations:
            tool = ann.get('type')
            
            # 使用包围盒进行快速过滤
            ann_bbox = ann.get('bbox')
            if ann_bbox and not ann_bbox.intersects(erase_rect):
                new_annotations.append(ann)
                continue

            if tool in ['pen', 'highlighter']:
                points = ann.get('points', [])
                if not points:
                    continue
                
                segments = []
                current_segment = []
                
                # 检查第一个点
                p_first = points[0]
                if (p_first.x() - pos.x())**2 + (p_first.y() - pos.y())**2 >= eraser_radius_sq:
                    current_segment.append(p_first)
                
                hit_in_this_ann = False
                
                for i in range(1, len(points)):
                    p_prev = points[i-1]
                    p_curr = points[i]
                    
                    dist_prev_sq = (p_prev.x() - pos.x())**2 + (p_prev.y() - pos.y())**2
                    dist_curr_sq = (p_curr.x() - pos.x())**2 + (p_curr.y() - pos.y())**2
                    
                    in_prev = dist_prev_sq < eraser_radius_sq
                    in_curr = dist_curr_sq < eraser_radius_sq
                    
                    if in_prev and in_curr:
                        # 都在圆内，跳过
                        hit_in_this_ann = True
                        continue
                    elif not in_prev and not in_curr:
                        # 都在圆外，但可能穿过圆
                        intersections = self._get_line_circle_intersections(p_prev, p_curr, pos, eraser_radius)
                        if len(intersections) >= 2:
                            hit_in_this_ann = True
                            # 穿过圆，产生两个交点，将线段切成三段，中间段在圆内被删
                            # 第一段：p_prev -> intersection1
                            current_segment.append(intersections[0])
                            segments.append(current_segment)
                            # 第二段：intersection2 -> p_curr (作为新段开始)
                            current_segment = [intersections[1], p_curr]
                        elif len(intersections) == 1:
                            # 切线或数值误差导致只有一个交点
                            hit_in_this_ann = True
                            current_segment.append(intersections[0])
                            segments.append(current_segment)
                            current_segment = [intersections[0], p_curr]
                        else:
                            # 完全在圆外
                            current_segment.append(p_curr)
                    elif not in_prev and in_curr:
                        # 从外进入圆
                        hit_in_this_ann = True
                        intersections = self._get_line_circle_intersections(p_prev, p_curr, pos, eraser_radius)
                        if intersections:
                            current_segment.append(intersections[0])
                        segments.append(current_segment)
                        current_segment = []
                    elif in_prev and not in_curr:
                        # 从圆内出来
                        hit_in_this_ann = True
                        intersections = self._get_line_circle_intersections(p_prev, p_curr, pos, eraser_radius)
                        if intersections:
                            current_segment = [intersections[0], p_curr]
                        else:
                            current_segment = [p_curr]
                
                if current_segment:
                    segments.append(current_segment)
                
                if hit_in_this_ann:
                    removed_any = True
                    for seg in segments:
                        if len(seg) >= 1: # 即使是一个点也保留
                            new_ann = ann.copy()
                            new_ann['points'] = seg
                            # 重新计算 bbox
                            xs = [p.x() for p in seg]
                            ys = [p.y() for p in seg]
                            new_ann['bbox'] = QRect(min(xs), min(ys), max(xs)-min(xs)+1, max(ys)-min(ys)+1).adjusted(-5, -5, 5, 5)
                            new_annotations.append(new_ann)
                else:
                    new_annotations.append(ann)
            elif tool in ['rect', 'ellipse', 'arrow', 'line', 'filled_rect', 'filled_ellipse']:
                should_remove = False
                rect = ann.get('bbox')
                if not rect:
                    rect = QRect(ann['start'], ann['end']).normalized()
                
                erase_rect = QRect(
                    pos.x() - eraser_size // 2,
                    pos.y() - eraser_size // 2,
                    eraser_size,
                    eraser_size
                )
                if rect.intersects(erase_rect):
                    should_remove = True
                
                if should_remove:
                    removed_any = True
                else:
                    new_annotations.append(ann)
            elif tool == 'text':
                should_remove = False
                if (ann['start'] - pos).manhattanLength() < eraser_size:
                    should_remove = True
                
                if should_remove:
                    removed_any = True
                else:
                    new_annotations.append(ann)
            else:
                new_annotations.append(ann)
        
        if removed_any:
            # 清除 Pen/Brush 缓存，因为标注列表发生了变化
            if hasattr(self, '_pen_cache'):
                self._pen_cache.clear()
                
            self.annotations = new_annotations
            self._redraw_from_annotations()

    def _apply_local_blur(self, start: QPoint, end: QPoint):
        """局部模糊 - 带有路径插值以确保连续性"""
        # 计算距离
        dist = math.sqrt((end.x() - start.x())**2 + (end.y() - start.y())**2)
        size = self.pen_width * 4
        
        # 插值步长：画笔大小的一半
        step = max(2, size // 3)
        num_steps = max(1, int(dist / step))
        
        for i in range(num_steps + 1):
            t = i / num_steps if num_steps > 0 else 1.0
            p = QPoint(
                int(start.x() + (end.x() - start.x()) * t),
                int(start.y() + (end.y() - start.y()) * t)
            )
            # 循环中不更新显示，只在最后更新一次
            self._blur_at(p, update_display=False)
        
        # 处理完所有插值点后，统一更新一次显示
        self.setPixmap(self.current_pixmap)

    def _blur_at(self, pos: QPoint, update_display=True):
        """在指定位置执行单次模糊"""
        size = self.pen_width * 4
        x = max(0, pos.x() - size // 2)
        y = max(0, pos.y() - size // 2)
        w = min(size, self.current_pixmap.width() - x)
        h = min(size, self.current_pixmap.height() - y)
        
        if w <= 0 or h <= 0:
            return
            
        region = self.current_pixmap.copy(x, y, w, h)
        blurred = self._blur_pixmap(region, 5)
        
        # 如果正在记录笔触，则加入子块
        if self.current_stroke and self.current_stroke['type'] == 'blur_brush':
            self.current_stroke['sub_annotations'].append({
                'rect': QRect(x, y, w, h),
                'pixmap': blurred.copy()
            })
        
        painter = QPainter(self.current_pixmap)
        painter.drawPixmap(x, y, blurred)
        painter.end()
        
        if update_display:
            self.setPixmap(self.current_pixmap)
    
    def _apply_local_pixelate(self, start: QPoint, end: QPoint):
        """局部像素化 - 带有路径插值以确保连续性"""
        dist = math.sqrt((end.x() - start.x())**2 + (end.y() - start.y())**2)
        size = self.pen_width * 4
        
        step = max(2, size // 3)
        num_steps = max(1, int(dist / step))
        
        for i in range(num_steps + 1):
            t = i / num_steps if num_steps > 0 else 1.0
            p = QPoint(
                int(start.x() + (end.x() - start.x()) * t),
                int(start.y() + (end.y() - start.y()) * t)
            )
            # 循环中不更新显示
            self._pixelate_at(p, update_display=False)
            
        # 统一更新一次显示
        self.setPixmap(self.current_pixmap)

    def _pixelate_at(self, pos: QPoint, update_display=True):
        """在指定位置执行单次像素化 - 优化版：网格对齐 + 圆形笔触"""
        size = self.pen_width * 4
        # 1. 确定原始画笔区域
        raw_x = max(0, pos.x() - size // 2)
        raw_y = max(0, pos.y() - size // 2)
        raw_w = min(size, self.current_pixmap.width() - raw_x)
        raw_h = min(size, self.current_pixmap.height() - raw_y)
        
        if raw_w <= 0 or raw_h <= 0:
            return

        # 2. 计算网格对齐区域
        block_size = 12  # 固定马赛克块大小，避免随画笔大小变化而闪烁
        
        # 向外扩展以对齐网格
        align_x = (raw_x // block_size) * block_size
        align_y = (raw_y // block_size) * block_size
        
        # 计算右下角坐标
        raw_right = raw_x + raw_w
        raw_bottom = raw_y + raw_h
        
        align_right = ((raw_right + block_size - 1) // block_size) * block_size
        align_bottom = ((raw_bottom + block_size - 1) // block_size) * block_size
        
        # 限制在图像范围内
        align_x = max(0, align_x)
        align_y = max(0, align_y)
        align_w = min(align_right - align_x, self.current_pixmap.width() - align_x)
        align_h = min(align_bottom - align_y, self.current_pixmap.height() - align_y)
        
        if align_w <= 0 or align_h <= 0:
            return
            
        # 3. 提取并像素化对齐区域
        region = self.current_pixmap.copy(align_x, align_y, align_w, align_h)
        
        # 使用自定义的像素化逻辑，确保块完整
        pixelated = self._pixelate_pixmap(region, block_size)
        
        # 4. 如果正在记录笔触，则加入子块 (使用对齐后的区域)
        if self.current_stroke and self.current_stroke['type'] == 'pixelate_brush':
            # 检查是否与上一个子块完全重叠，如果是则跳过 (性能优化)
            subs = self.current_stroke.get('sub_annotations', [])
            is_redundant = False
            if subs:
                last_rect = subs[-1]['rect']
                if last_rect == QRect(align_x, align_y, align_w, align_h):
                    is_redundant = True
            
            if not is_redundant:
                self.current_stroke['sub_annotations'].append({
                    'rect': QRect(align_x, align_y, align_w, align_h),
                    'pixmap': pixelated.copy()
                })
        
        # 5. 绘制（不使用圆形蒙版，保持方块马赛克的网格对齐特性，且性能更好）
        painter = QPainter(self.current_pixmap)
        painter.drawPixmap(align_x, align_y, pixelated)
        painter.end()
        
        if update_display:
            self.setPixmap(self.current_pixmap)

    def _draw_shape_preview(self, end: QPoint):
        self.current_pixmap = self.temp_pixmap.copy()
        painter = QPainter(self.current_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 几何图形使用固定宽度，画笔/荧光笔使用动态宽度
        draw_width = self.FIXED_SHAPE_WIDTH if self.current_tool in ['rect', 'ellipse', 'arrow', 'line', 'filled_rect', 'filled_ellipse'] else self.pen_width
        pen = QPen(self.pen_color, draw_width)
        painter.setPen(pen)
        rect = QRect(self.shape_start, end).normalized()
        
        if self.current_tool == 'rect':
            painter.drawRect(rect)
        elif self.current_tool == 'filled_rect':
            painter.setBrush(QBrush(self.pen_color))
            painter.drawRect(rect)
        elif self.current_tool == 'ellipse':
            painter.drawEllipse(rect)
        elif self.current_tool == 'filled_ellipse':
            painter.setBrush(QBrush(self.pen_color))
            painter.drawEllipse(rect)
        elif self.current_tool == 'arrow':
            self._draw_arrow(painter, self.shape_start, end)
        elif self.current_tool == 'line':
            painter.drawLine(self.shape_start, end)
        painter.end()
        self.setPixmap(self.current_pixmap)

    def _draw_shape_final(self, end: QPoint):
        self._draw_shape_preview(end)

    def _draw_arrow(self, painter: QPainter, start: QPoint, end: QPoint):
        # 获取当前画笔宽度（可能是固定宽度 3，也可能是全局 pen_width）
        curr_width = painter.pen().width()
        
        # 1. 首先画主干线
        painter.drawLine(start, end)
        
        # 2. 计算箭头的角度
        angle = math.atan2(end.y() - start.y(), end.x() - start.x())
        
        # 3. 动态计算箭头头部大小
        # 基础大小为 15，随线宽增加，但增加速度放缓 (使用线宽的 2.5 倍左右)
        # 同时设置一个最小值，防止线宽很小时箭头看不见
        head_size = max(15, curr_width * 2.5)
        
        # 4. 计算箭头头部的两个翼点
        # 增加一点点偏移，让箭头尖端稍微超过线段末端，或者刚好覆盖线段末端
        # 这里的 30 度角 (pi/6) 是经典比例
        p1 = QPoint(int(end.x() - head_size * math.cos(angle - math.pi / 6)),
                    int(end.y() - head_size * math.sin(angle - math.pi / 6)))
        p2 = QPoint(int(end.x() - head_size * math.cos(angle + math.pi / 6)),
                    int(end.y() - head_size * math.sin(angle + math.pi / 6)))
        
        # 5. 绘制箭头头部
        # 保存当前画笔，设置一个细画笔来画头部的轮廓，防止粗线宽导致头部变形
        old_pen = painter.pen()
        head_pen = QPen(self.pen_color)
        head_pen.setWidth(1) # 头部轮廓使用细线
        head_pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin) # 使用锐角连接
        painter.setPen(head_pen)
        
        # 设置填充颜色
        painter.setBrush(QBrush(self.pen_color))
        
        # 绘制并填充多边形
        painter.drawPolygon([end, p1, p2])
        
        # 恢复原始画笔
        painter.setPen(old_pen)

    def _add_text(self, image_pos: QPoint):
        """添加可编辑文本框 - 默认大小（image_pos是图像坐标）"""
        # 将图像坐标转换为widget坐标
        widget_pos = self._get_widget_pos(image_pos)
        self._add_text_at(widget_pos, image_pos)
    
    def _add_text_with_size(self, image_rect: QRect):
        """添加指定大小的文本框 - 拖拽创建（image_rect是图像坐标）"""
        # 将图像坐标转换为widget坐标
        top_left = self._get_widget_pos(image_rect.topLeft())
        bottom_right = self._get_widget_pos(image_rect.bottomRight())
        widget_rect = QRect(top_left, bottom_right)
        
        self._add_text_with_rect(widget_rect, image_rect)
    
    def _draw_text_box_preview(self):
        """绘制文本框拖拽预览"""
        if not self.text_box_preview_rect or self.temp_pixmap is None:
            return
        
        self.current_pixmap = self.temp_pixmap.copy()
        painter = QPainter(self.current_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 调用 Mixin 的绘制逻辑
        TextManagerMixin._draw_text_box_preview(self, painter, self.text_box_preview_rect)
        
        painter.end()
        self.setPixmap(self.current_pixmap)

    
    def _update_text_boxes_transform(self):
        """缩放时文本框位置和大小保持不变"""
        # 编辑时文本框的屏幕位置和大小固定不变
        # 渲染时会根据当前缩放级别计算正确的图像坐标
        pass
    
    def _on_text_confirmed(self, text: str, text_box):
        """文本确认后绘制到画布"""
        if text.strip():
            # 根据文本框当前屏幕位置计算图像坐标
            widget_pos = text_box.pos()
            margin = text_box._handle_radius + 2
            top_margin = text_box._rotate_handle_distance + margin
            
            # 内容区域左上角的widget坐标
            content_widget_pos = QPoint(widget_pos.x() + margin, widget_pos.y() + top_margin)
            # 转换为图像坐标
            image_pos = self._get_image_pos(content_widget_pos)
            
            # 根据缩放级别计算渲染到图像的字体大小
            # 编辑时字体大小是固定的，渲染时需要除以缩放级别
            display_font_size = text_box.font_size
            if self.zoom_level > 0:
                render_font_size = int(display_font_size / self.zoom_level)
            else:
                render_font_size = display_font_size
            render_font_size = max(8, render_font_size)
            
            text_color = text_box.text_color
            
            # 绘制文本到画布（使用图像坐标）
            painter = QPainter(self.current_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            font = QFont("Microsoft YaHei", render_font_size)
            painter.setFont(font)
            painter.setPen(text_color)
            
            # 内边距也需要根据缩放级别转换
            if self.zoom_level > 0:
                text_padding_x = int(6 / self.zoom_level)
                text_padding_y = int(4 / self.zoom_level)
            else:
                text_padding_x = 6
                text_padding_y = 4
            
            # 计算文本实际绘制位置
            text_x = image_pos.x() + text_padding_x
            text_y = image_pos.y() + text_padding_y
            
            # 计算文本边界矩形
            from PySide6.QtGui import QFontMetrics
            fm = QFontMetrics(font)
            # 使用 boundingRect 计算文本实际占用的宽高
            text_bounds = fm.boundingRect(QRect(0, 0, 10000, 10000), 
                                          Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, 
                                          text)
            # 创建新的矩形，从文本绘制位置开始，使用计算出的宽高
            # 扩大边界矩形，增加点击容差
            text_bounds = QRect(
                text_x - 5,
                text_y - 5,
                text_bounds.width() + 10,
                text_bounds.height() + 10
            )
            
            # 计算文本绘制区域
            text_rect = QRect(text_x, text_y, 10000, 10000)
            
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, text)
            
            painter.end()
            self.setPixmap(self.current_pixmap)
            self._save_to_history()
            
            # 记录渲染的文字信息（用于点击重新编辑）
            self.rendered_texts.append({
                'text': text,
                'image_pos': QPoint(image_pos),  # 内容区域左上角的图像坐标
                'font_size': render_font_size,  # 渲染到图像的字体大小
                'display_font_size': display_font_size,  # 编辑时显示的字体大小
                'color': QColor(text_color),
                'rect': QRect(text_bounds),  # 文字在图像上的边界矩形
                'history_index': self.history_index  # 记录历史索引，用于撤销
            })
        
        # 移除文本框
        self._remove_text_box(text_box)
    
    def _get_rendered_text_at(self, image_pos: QPoint):
        """检查图像坐标位置是否有已渲染的文字，返回最上层的文字信息"""
        # 从后往前遍历（后渲染的在上层）
        for text_info in reversed(self.rendered_texts):
            rect = text_info['rect']
            # 检查点击位置是否在文字边界矩形内
            if rect.contains(image_pos):
                return text_info
        return None
    
    def get_rendered_texts_count(self) -> int:
        """获取已渲染文字数量（用于调试）"""
        return len(self.rendered_texts)
    
    def _edit_rendered_text(self, text_info: dict):
        """撤销已渲染的文字并重新进入编辑模式"""
        # 撤销到渲染该文字之前的状态
        target_index = text_info['history_index'] - 1
        if target_index >= 0 and target_index < len(self.history):
            self.history_index = target_index
            state = self.history[self.history_index]
            self.current_pixmap = state['pixmap'].copy()
            self.annotations = []
            for ann in state['annotations']:
                ann_copy = ann.copy()
                if 'points' in ann:
                    ann_copy['points'] = list(ann['points'])
                self.annotations.append(ann_copy)
                
            self.setPixmap(self.current_pixmap)
            
            # 删除该历史记录之后的所有记录
            self.history = self.history[:self.history_index + 1]
        
        # 从已渲染文字列表中移除
        if text_info in self.rendered_texts:
            self.rendered_texts.remove(text_info)
        
        # 移除历史索引大于等于当前索引的所有渲染文字记录
        self.rendered_texts = [t for t in self.rendered_texts if t['history_index'] <= self.history_index]
        
        # 创建新的文本框进行编辑
        from ui.text_box import TextBoxWidget
        text_box = TextBoxWidget(self)
        text_box.set_font_size(text_info['display_font_size'])
        text_box.set_color(text_info['color'])
        text_box._text = text_info['text']
        text_box._cursor_pos = len(text_info['text'])
        
        # 将图像坐标转换为widget坐标
        widget_pos = self._get_widget_pos(text_info['image_pos'])
        
        # 计算边距，调整位置使内容区域对齐到原始位置
        margin = text_box._handle_radius + 2
        top_margin = text_box._rotate_handle_distance + margin
        adjusted_x = widget_pos.x() - margin
        adjusted_y = widget_pos.y() - top_margin
        text_box.move(adjusted_x, adjusted_y)
        
        # 初始化图像坐标信息
        text_box.image_pos = QPoint(text_info['image_pos'])
        text_box.base_zoom = self.zoom_level
        text_box.display_scale = self.zoom_level
        
        # 使用 Mixin 的设置逻辑
        self._setup_text_box(text_box)
    
    def wheelEvent(self, event):
        """滚轮缩放"""
        # 获取滚轮增量
        delta = event.angleDelta().y()
        
        # 计算新的缩放级别
        if delta > 0:
            new_zoom = min(self.zoom_level * 1.1, self.max_zoom)
        else:
            new_zoom = max(self.zoom_level / 1.1, self.min_zoom)
        
        if new_zoom != self.zoom_level:
            self.set_zoom(new_zoom)
        
        event.accept()
    
    def set_zoom(self, zoom: float):
        """设置缩放级别"""
        self.zoom_level = max(self.min_zoom, min(self.max_zoom, zoom))
        
        if self.crop_mode:
            self._update_crop_display()
        else:
            self._update_zoomed_display()
        
        # 更新文本框位置和大小
        self._update_text_boxes_transform()
        
        # 发送缩放变化信号（如果父窗口需要更新状态栏）
        parent = self.parent()
        while parent:
            if hasattr(parent, '_on_zoom_changed'):
                parent._on_zoom_changed(self.zoom_level)
                break
            parent = parent.parent()
    
    def _update_zoomed_display(self):
        """更新缩放后的显示 - 优化版：仅渲染可见区域以支持超大图片"""
        if self.current_pixmap.isNull():
            return
        
        display_size = self.size()
        if display_size.width() <= 0 or display_size.height() <= 0:
            return

        # 创建显示画布
        display_pixmap = QPixmap(display_size)
        display_pixmap.fill(self.canvas_bg_color)
        
        painter = QPainter(display_pixmap)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 计算缩放后的完整尺寸
        full_scaled_width = int(self.current_pixmap.width() * self.zoom_level)
        full_scaled_height = int(self.current_pixmap.height() * self.zoom_level)

        # 计算图像在 widget 中的起始位置（居中 + 偏移）
        base_x = (display_size.width() - full_scaled_width) // 2 + self.image_offset.x()
        base_y = (display_size.height() - full_scaled_height) // 2 + self.image_offset.y()

        # 计算可见区域在缩放后图像中的矩形 (Widget 坐标系)
        view_rect = QRect(0, 0, display_size.width(), display_size.height())
        image_rect_scaled = QRect(base_x, base_y, full_scaled_width, full_scaled_height)
        visible_rect_in_widget = view_rect.intersected(image_rect_scaled)

        if not visible_rect_in_widget.isEmpty():
            # 将可见区域坐标转换回原图坐标 (Source ROI)
            src_x_scaled = visible_rect_in_widget.x() - base_x
            src_y_scaled = visible_rect_in_widget.y() - base_y
            src_w_scaled = visible_rect_in_widget.width()
            src_h_scaled = visible_rect_in_widget.height()

            # 转回原始图像坐标系
            src_x = int(src_x_scaled / self.zoom_level)
            src_y = int(src_y_scaled / self.zoom_level)
            src_w = int(src_w_scaled / self.zoom_level) + 1
            src_h = int(src_h_scaled / self.zoom_level) + 1

            # 限制范围
            src_x = max(0, min(src_x, self.current_pixmap.width() - 1))
            src_y = max(0, min(src_y, self.current_pixmap.height() - 1))
            src_w = min(src_w, self.current_pixmap.width() - src_x)
            src_h = min(src_h, self.current_pixmap.height() - src_y)

            if src_w > 0 and src_h > 0:
                # 从原图中提取可见部分的切片
                source_roi = self.current_pixmap.copy(src_x, src_y, src_w, src_h)
                
                # 缩放这个切片
                target_w = int(src_w * self.zoom_level)
                target_h = int(src_h * self.zoom_level)
                
                if target_w > 0 and target_h > 0:
                    scaled_roi = source_roi.scaled(
                        target_w, target_h,
                        Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    
                    # 绘制到 display_pixmap
                    draw_x = base_x + int(src_x * self.zoom_level)
                    draw_y = base_y + int(src_y * self.zoom_level)
                    painter.drawPixmap(draw_x, draw_y, QPixmap.fromImage(scaled_roi))

        painter.end()
        super().setPixmap(display_pixmap)
    
    def zoom_in(self):
        """放大"""
        self.set_zoom(self.zoom_level * 1.25)
    
    def zoom_out(self):
        """缩小"""
        self.set_zoom(self.zoom_level / 1.25)
    
    def zoom_reset(self):
        """重置缩放"""
        self.set_zoom(1.0)
    
    def zoom_fit(self):
        """适应窗口"""
        if self.current_pixmap.isNull():
            return
        
        canvas_size = self.size()
        img_size = self.current_pixmap.size()
        
        zoom_w = canvas_size.width() / img_size.width()
        zoom_h = canvas_size.height() / img_size.height()
        
        self.set_zoom(min(zoom_w, zoom_h) * 0.95)

    def _save_to_history(self):
        self.history = self.history[:self.history_index + 1]
        # 深度复制 annotations 以免后续修改影响历史
        saved_annotations = []
        for ann in self.annotations:
            ann_copy = ann.copy()
            if 'points' in ann:
                ann_copy['points'] = list(ann['points'])
            if 'pixmap' in ann:
                ann_copy['pixmap'] = ann['pixmap'].copy()
            if 'sub_annotations' in ann:
                ann_copy['sub_annotations'] = []
                for sub in ann['sub_annotations']:
                    sub_copy = sub.copy()
                    if 'pixmap' in sub:
                        sub_copy['pixmap'] = sub['pixmap'].copy()
                    ann_copy['sub_annotations'].append(sub_copy)
            saved_annotations.append(ann_copy)
            
        self.history.append({
            'pixmap': self.current_pixmap.copy(),
            'original_pixmap': self.original_pixmap.copy(),
            'annotations': saved_annotations,
            'rendered_texts': [t.copy() for t in self.rendered_texts],
            'adjustments': self._current_adjustments.copy()
        })
        self.history_index = len(self.history) - 1
        if len(self.history) > self.max_history:
            self.history.pop(0)
            self.history_index -= 1
            
        # 保存后，当前状态不再是预览状态
        self._is_previewing = False

    def undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            self._is_previewing = False
            state = self.history[self.history_index]
            self.current_pixmap = state['pixmap'].copy()
            self.original_pixmap = state.get('original_pixmap', self.current_pixmap).copy()
            self._current_adjustments = state.get('adjustments', {"brightness": 0, "contrast": 0, "saturation": 0}).copy()
            
            self.annotations = []
            for ann in state['annotations']:
                ann_copy = ann.copy()
                if 'points' in ann:
                    ann_copy['points'] = list(ann['points'])
                if 'pixmap' in ann:
                    ann_copy['pixmap'] = ann['pixmap'].copy()
                if 'sub_annotations' in ann:
                    ann_copy['sub_annotations'] = []
                    for sub in ann['sub_annotations']:
                        sub_copy = sub.copy()
                        if 'pixmap' in sub:
                            sub_copy['pixmap'] = sub['pixmap'].copy()
                        ann_copy['sub_annotations'].append(sub_copy)
                self.annotations.append(ann_copy)
            
            # 恢复渲染文字
            if 'rendered_texts' in state:
                self.rendered_texts = [t.copy() for t in state['rendered_texts']]
            else:
                # 兼容旧版本历史记录
                self.rendered_texts = [t for t in self.rendered_texts if t.get('history_index', 0) <= self.history_index]
                
            self.setPixmap(self.current_pixmap)
            return True
        return False

    def rotate(self, angle: int):
        transform = QTransform().rotate(angle)
        self.current_pixmap = self.current_pixmap.transformed(transform)
        self.original_pixmap = self.original_pixmap.transformed(transform)
        self.setPixmap(self.current_pixmap)
        self._save_to_history()

    def flip_horizontal(self):
        transform = QTransform().scale(-1, 1)
        self.current_pixmap = self.current_pixmap.transformed(transform)
        self.setPixmap(self.current_pixmap)
        self._save_to_history()

    def flip_vertical(self):
        transform = QTransform().scale(1, -1)
        self.current_pixmap = self.current_pixmap.transformed(transform)
        self.setPixmap(self.current_pixmap)
        self._save_to_history()
    
    def _get_effective_original(self):
        """获取用于处理的基础图（支持降采样预览）"""
        if not self.original_pixmap or self.original_pixmap.isNull():
            return None
            
        # 如果当前正在预览模式，且原图很大，则返回降采样版本
        if self._is_previewing:
            max_dim = max(self.original_pixmap.width(), self.original_pixmap.height())
            if max_dim > self._max_preview_size:
                if self._downsampled_original is None:
                    scale = self._max_preview_size / max_dim
                    self._preview_scale = scale
                    self._downsampled_original = self.original_pixmap.scaled(
                        int(self.original_pixmap.width() * scale),
                        int(self.original_pixmap.height() * scale),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                return self._downsampled_original
        
        return self.original_pixmap

    # ========== 画质特效 ==========
    
    def _pixmap_to_cv(self, pixmap):
        """将 QPixmap/QImage 转换为 OpenCV 格式 (BGRA)"""
        if isinstance(pixmap, QPixmap):
            image = pixmap.toImage()
        else:
            image = pixmap
        image = image.convertToFormat(QImage.Format.Format_ARGB32)
        width = image.width()
        height = image.height()
        
        ptr = image.bits()
        # ptr 在某些环境下可能返回 sip.voidptr 或类似对象，需要处理
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape((height, width, 4))
        return arr.copy()

    def _cv_to_pixmap(self, cv_img):
        """将 OpenCV 格式 (BGRA) 转换为 QPixmap"""
        height, width, channel = cv_img.shape
        bytesPerLine = 4 * width
        q_img = QImage(cv_img.data, width, height, bytesPerLine, QImage.Format.Format_ARGB32)
        return QPixmap.fromImage(q_img.copy())

    def _blur_pixmap(self, pixmap: QPixmap, radius: int) -> QPixmap:
        """模糊效果 - 使用 OpenCV 优化"""
        if pixmap.isNull():
            return pixmap
        
        radius = max(1, min(20, radius))
        # 转换为 OpenCV 格式
        cv_img = self._pixmap_to_cv(pixmap)
        
        # 使用 OpenCV 的 GaussianBlur，比盒式模糊效果更好且极快
        # kernel size 必须是奇数
        ksize = radius * 2 + 1
        blurred = cv2.GaussianBlur(cv_img, (ksize, ksize), 0)
        
        return self._cv_to_pixmap(blurred)
    
    def _pixelate_pixmap(self, pixmap: QPixmap, block_size: int) -> QPixmap:
        """像素化效果 - 使用 OpenCV 优化"""
        if pixmap.isNull():
            return pixmap
        
        block_size = max(2, min(40, block_size))
        cv_img = self._pixmap_to_cv(pixmap)
        h, w = cv_img.shape[:2]
        
        # 通过缩放实现像素化。使用 INTER_AREA 降采样可以获得更准确的区域平均颜色
        temp = cv2.resize(cv_img, (max(1, w // block_size), max(1, h // block_size)), interpolation=cv2.INTER_AREA)
        pixelated = cv2.resize(temp, (w, h), interpolation=cv2.INTER_NEAREST)
        
        return self._cv_to_pixmap(pixelated)
    
    def apply_blur(self, radius: int = 5):
        """应用全图模糊"""
        if not self.current_pixmap or self.current_pixmap.isNull():
            return
        try:
            # 如果当前正在预览调整，先应用调整到全分辨率
            if self._is_previewing:
                self.apply_adjustments()
                
            self.current_pixmap = self._blur_pixmap(self.current_pixmap, radius)
            self.original_pixmap = self.current_pixmap.copy() # 更新基础图像
            self.setPixmap(self.current_pixmap)
            self._save_to_history()
        except Exception as e:
            print(f"Apply blur error: {e}")
    
    def apply_pixelate(self, block_size: int = 10):
        """应用全图像素化"""
        if not self.current_pixmap or self.current_pixmap.isNull():
            return
        try:
            # 如果当前正在预览调整，先应用调整到全分辨率
            if self._is_previewing:
                self.apply_adjustments()
                
            self.current_pixmap = self._pixelate_pixmap(self.current_pixmap, block_size)
            self.original_pixmap = self.current_pixmap.copy() # 更新基础图像
            self.setPixmap(self.current_pixmap)
            self._save_to_history()
        except Exception as e:
            print(f"Apply pixelate error: {e}")
    
    def apply_sharpen(self):
        """锐化效果 - 使用 OpenCV 优化"""
        if not self.current_pixmap or self.current_pixmap.isNull():
            return
        
        try:
            # 如果当前正在预览调整，先应用调整到全分辨率
            if self._is_previewing:
                self.apply_adjustments()
                
            cv_img = self._pixmap_to_cv(self.current_pixmap)
            # 锐化算子
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
            # 应用卷积
            sharpened = cv2.filter2D(cv_img, -1, kernel)
            
            self.current_pixmap = self._cv_to_pixmap(sharpened)
            self.original_pixmap = self.current_pixmap.copy() # 更新基础图像
            self.setPixmap(self.current_pixmap)
            self._save_to_history()
        except Exception as e:
            print(f"Apply sharpen error: {e}")
    
    def apply_emboss(self):
        """浮雕效果 - 使用 OpenCV 优化"""
        if not self.current_pixmap or self.current_pixmap.isNull():
            return
        
        try:
            # 如果当前正在预览调整，先应用调整到全分辨率
            if self._is_previewing:
                self.apply_adjustments()
                
            cv_img = self._pixmap_to_cv(self.current_pixmap)
            # 浮雕卷积核
            kernel = np.array([[-2, -1, 0], [-1, 1, 1], [0, 1, 2]], dtype=np.float32)
            # 转灰度处理浮雕感更强，但这里保持彩色并加上偏移
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGRA2GRAY)
            embossed = cv2.filter2D(gray, -1, kernel) + 128
            embossed = np.clip(embossed, 0, 255).astype(np.uint8)
            
            # 转回 BGRA
            embossed_bgra = cv2.cvtColor(embossed, cv2.COLOR_GRAY2BGRA)
            # 恢复 alpha 通道
            embossed_bgra[:, :, 3] = cv_img[:, :, 3]
            
            self.current_pixmap = self._cv_to_pixmap(embossed_bgra)
            self.original_pixmap = self.current_pixmap.copy() # 更新基础图像
            self.setPixmap(self.current_pixmap)
            self._save_to_history()
        except Exception as e:
            print(f"Apply emboss error: {e}")
    
    def add_noise(self, intensity: int = 30):
        """添加噪点 - 使用 NumPy 优化"""
        if not self.current_pixmap or self.current_pixmap.isNull():
            return
        
        try:
            # 如果当前正在预览调整，先应用调整到全分辨率
            if self._is_previewing:
                self.apply_adjustments()
                
            cv_img = self._pixmap_to_cv(self.current_pixmap)
            h, w, c = cv_img.shape
            
            # 生成随机噪声
            noise = np.random.randint(-intensity, intensity, (h, w, 3), dtype=np.int16)
            
            # 只对 RGB 通道添加噪声，Alpha 通道保持不变
            img_rgb = cv_img[:, :, :3].astype(np.int16)
            img_rgb = np.clip(img_rgb + noise, 0, 255).astype(np.uint8)
            
            cv_img[:, :, :3] = img_rgb
            
            self.current_pixmap = self._cv_to_pixmap(cv_img)
            self.original_pixmap = self.current_pixmap.copy() # 更新基础图像
            self.setPixmap(self.current_pixmap)
            self._save_to_history()
        except Exception as e:
            print(f"Add noise error: {e}")
    
    # ========== 色彩调整 ==========
    
    def _apply_all_adjustments(self, base_pixmap: QPixmap) -> QPixmap:
        """对给定的 pixmap 应用当前存储的所有色彩调整"""
        if not base_pixmap or base_pixmap.isNull():
            return base_pixmap
            
        try:
            cv_img = self._pixmap_to_cv(base_pixmap)
            
            # 1. 亮度调整
            brightness = self._current_adjustments["brightness"]
            if brightness != 0:
                img_h = cv_img.astype(np.int16)
                img_h[:, :, :3] += brightness
                cv_img = np.clip(img_h, 0, 255).astype(np.uint8)
                
            # 2. 对比度调整
            contrast = self._current_adjustments["contrast"]
            if contrast != 0:
                factor = 1.0 + (contrast / 100.0)
                img_h = cv_img.astype(np.float32)
                img_h[:, :, :3] = (img_h[:, :, :3] - 128) * factor + 128
                cv_img = np.clip(img_h, 0, 255).astype(np.uint8)
                
            # 3. 饱和度调整
            saturation = self._current_adjustments["saturation"]
            if saturation != 0:
                bgr = cv_img[:, :, :3]
                hls = cv2.cvtColor(bgr, cv2.COLOR_BGR2HLS).astype(np.float32)
                factor = 1.0 + (saturation / 100.0)
                hls[:, :, 2] *= factor
                hls[:, :, 2] = np.clip(hls[:, :, 2], 0, 255)
                bgr_new = cv2.cvtColor(hls.astype(np.uint8), cv2.COLOR_HLS2BGR)
                cv_img[:, :, :3] = bgr_new
                
            return self._cv_to_pixmap(cv_img)
        except Exception as e:
            print(f"Apply adjustments error: {e}")
            return base_pixmap

    def adjust_brightness(self, value: int):
        """调整亮度 -100 到 100"""
        self._current_adjustments["brightness"] = value
        self._is_previewing = True
        base = self._get_effective_original()
        self.current_pixmap = self._apply_all_adjustments(base)
        self.setPixmap(self.current_pixmap)
    
    def adjust_contrast(self, value: int):
        """调整对比度 -100 到 100"""
        self._current_adjustments["contrast"] = value
        self._is_previewing = True
        base = self._get_effective_original()
        self.current_pixmap = self._apply_all_adjustments(base)
        self.setPixmap(self.current_pixmap)
    
    def adjust_saturation(self, value: int):
        """调整饱和度 -100 到 100"""
        self._current_adjustments["saturation"] = value
        self._is_previewing = True
        base = self._get_effective_original()
        self.current_pixmap = self._apply_all_adjustments(base)
        self.setPixmap(self.current_pixmap)
    
    def apply_adjustments(self):
        """应用当前调整到历史 - 使用全分辨率"""
        self._is_previewing = False
        # 在全分辨率上应用所有调整
        self.current_pixmap = self._apply_all_adjustments(self.original_pixmap)
        self.setPixmap(self.current_pixmap)
        self.original_pixmap = self.current_pixmap.copy()
        self._save_to_history()
        # 重置当前调整和预览缓存
        self._current_adjustments = {"brightness": 0, "contrast": 0, "saturation": 0}
        self._downsampled_original = None
    
    def reset_adjustments(self):
        """重置调整"""
        self._is_previewing = False
        self._current_adjustments = {"brightness": 0, "contrast": 0, "saturation": 0}
        self._downsampled_original = None
        self.current_pixmap = self.original_pixmap.copy()
        self.setPixmap(self.current_pixmap)
    
    def crop_to_rect(self, rect: QRect):
        """裁剪到指定区域"""
        self.current_pixmap = self.current_pixmap.copy(rect)
        self.original_pixmap = self.current_pixmap.copy()
        self.setPixmap(self.current_pixmap)
        self._save_to_history()
    
    def clear_annotations(self):
        """清除所有标注"""
        self.annotations = []
        self.current_pixmap = self.original_pixmap.copy()
        self.setPixmap(self.current_pixmap)
        self._save_to_history()
    
    def reset_to_original(self):
        """完全重置 - 恢复到最初截图状态，移除所有绘图和特效"""
        if not self.initial_pixmap or self.initial_pixmap.isNull():
            return False
            
        # 恢复到最初原始图像
        self.original_pixmap = self.initial_pixmap.copy()
        self.current_pixmap = self.initial_pixmap.copy()
        self.annotations = []
        self.rendered_texts = []
        
        # 重置所有调整参数
        self._current_adjustments = {"brightness": 0, "contrast": 0, "saturation": 0}
        self._is_previewing = False
        self._downsampled_original = None
        
        # 更新显示
        self.setPixmap(self.current_pixmap)
        
        # 保存到历史，让重置也可以撤销（可选，但这里遵循原逻辑清空历史，
        # 但我们让它变成一个新的起点，且能回退到最初）
        self.history = [{
            'pixmap': self.current_pixmap.copy(),
            'original_pixmap': self.original_pixmap.copy(),
            'annotations': [],
            'rendered_texts': [],
            'adjustments': {"brightness": 0, "contrast": 0, "saturation": 0}
        }]
        self.history_index = 0
        return True

    def get_pixmap(self) -> QPixmap:
        return QPixmap.fromImage(self.current_pixmap)
