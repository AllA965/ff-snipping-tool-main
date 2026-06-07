"""
滚动截图模块 - 类似PixPin的手动长截图功能
功能：
- 用户手动滚动控制
- 实时长图预览（右侧预览窗口）
- 智能拼接算法
- 平滑滚动和缩放
"""
import time
import numpy as np
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QApplication, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QTimer, QRect, QPoint, QPointF, QSize
from PySide6.QtGui import (
    QPixmap, QPainter, QColor, QImage, QPen, QFont,
    QGuiApplication, QWheelEvent
)


class RealtimePreviewPanel(QWidget):
    """实时预览面板 - 现代化设计"""
    
    finish_clicked = Signal()
    cancel_clicked = Signal()
    
    # 颜色主题 - 现代化白色风格
    BG_COLOR = QColor(255, 255, 255, 240)
    BORDER_COLOR = QColor(0, 0, 0, 20)
    TEXT_COLOR = QColor(31, 41, 55)
    TEXT_SECONDARY = QColor(107, 114, 128)
    ACCENT_COLOR = QColor(37, 99, 235)  # 蓝色
    SUCCESS_COLOR = QColor(22, 163, 74)  # 绿色
    PREVIEW_BG = QColor(243, 244, 246)
    SHADOW_COLOR = QColor(0, 0, 0, 30)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.merged_image = None  # 存储原始 QImage
        self.frame_count = 0
        self.scroll_offset = 0
        self.preview_scale = 1.0
        self.dragging = False
        self.last_mouse_y = 0
        self._hover_finish = False
        self._hover_cancel = False
        self._setup_ui()
    
    def _setup_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(260)  # 稍微加宽一点
        self.setMinimumHeight(450)
        self.setMouseTracking(True)
    
    def position_next_to(self, selection: QRect, screen_offset: QPoint):
        """定位到选区右侧"""
        screen = QGuiApplication.primaryScreen().geometry()
        preview_height = min(selection.height() + 120, screen.height() - 100)
        self.setFixedHeight(max(450, preview_height))
        
        x = selection.right() + screen_offset.x() + 25
        y = selection.top() + screen_offset.y()
        
        if x + self.width() > screen.right():
            x = selection.left() + screen_offset.x() - self.width() - 25
        
        if y + self.height() > screen.bottom():
            y = screen.bottom() - self.height() - 20
        if y < screen.top():
            y = screen.top() + 20
        
        self.move(x, y)
    
    def update_preview(self, merged: QImage, frame_count: int):
        """更新预览图像 - 仅存储引用，绘图时按需裁切"""
        if merged.isNull():
            return
            
        self.merged_image = merged
        self.frame_count = frame_count
        
        # 计算宽度缩放比例 (保持宽度填满预览区)
        available_width = self.width() - 40
        self.preview_scale = available_width / merged.width()
        
        # 自动滚动到最新内容
        scaled_height = int(merged.height() * self.preview_scale)
        visible_height = self.height() - 160
        
        if scaled_height > visible_height:
            # 默认显示最新添加的部分 (底部或顶部)
            # 如果是向下滚动，通常看底部；如果是向上滚动，通常看顶部
            # 这里我们简单地让它跟随最新的拼接点
            self.scroll_offset = max(0, scaled_height - visible_height)
        
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # 绘制阴影效果 - 更细腻的投影
        shadow_rect = self.rect().adjusted(2, 2, -2, -2)
        for i in range(5):
            opacity = (5 - i) * 10
            painter.setBrush(QColor(0, 0, 0, opacity))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(shadow_rect.adjusted(i, i, -i, -i), 12, 12)
        
        # 主背景
        main_rect = self.rect().adjusted(4, 4, -8, -8)
        painter.setBrush(self.BG_COLOR)
        painter.setPen(QPen(self.BORDER_COLOR, 1))
        painter.drawRoundedRect(main_rect, 12, 12)
        
        # 顶部标题栏
        self._draw_header(painter, main_rect)
        
        # 预览区域
        preview_rect = QRect(20, 75, main_rect.width() - 40, main_rect.height() - 160)
        self._draw_preview(painter, preview_rect)
        
        # 底部控制区域
        self._draw_footer(painter, main_rect)
    
    def _draw_header(self, painter, main_rect):
        """绘制顶部标题栏"""
        # 标题
        painter.setPen(self.TEXT_COLOR)
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        painter.drawText(20, 32, "长截图预览")
        
        # 状态指示器（录制中的红点）
        if self.frame_count > 0:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(239, 68, 68))  # 红色
            painter.drawEllipse(20, 44, 8, 8)
            
            painter.setPen(self.TEXT_SECONDARY)
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(34, 52, f"已捕获 {self.frame_count} 帧")
        else:
            painter.setPen(self.TEXT_SECONDARY)
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(20, 52, "等待捕获...")
        
        # 分隔线
        painter.setPen(QPen(self.BORDER_COLOR, 1))
        painter.drawLine(16, 62, main_rect.width() - 16, 62)
    
    def _draw_preview(self, painter, rect: QRect):
        """绘制预览图像 - 按需绘制可见区域"""
        # 预览区域背景（带圆角）
        painter.setBrush(self.PREVIEW_BG)
        painter.setPen(QPen(self.BORDER_COLOR, 1))
        painter.drawRoundedRect(rect, 8, 8)
        
        inner_rect = rect.adjusted(1, 1, -1, -1)
        
        if self.merged_image and not self.merged_image.isNull():
            # 计算缩放后的总高度
            scaled_height = int(self.merged_image.height() * self.preview_scale)
            
            # 计算当前可见区域在原始 QImage 中的坐标
            # scroll_offset 是缩放后的偏移量
            source_y = int(self.scroll_offset / self.preview_scale)
            source_h = int(inner_rect.height() / self.preview_scale)
            
            # 确保不越界
            source_y = max(0, min(source_y, self.merged_image.height() - 1))
            source_h = min(source_h, self.merged_image.height() - source_y)
            
            # 目标绘制区域
            # 如果缩放后的高度小于预览区，居中显示
            draw_h = min(inner_rect.height(), scaled_height)
            draw_y = inner_rect.y()
            if scaled_height < inner_rect.height():
                draw_y += (inner_rect.height() - scaled_height) // 2
            
            # 绘制可见部分
            # 使用 drawImage 的源矩形参数实现高效切片绘制
            painter.setClipRect(inner_rect)
            painter.drawImage(
                QRect(inner_rect.x(), draw_y, inner_rect.width(), draw_h),
                self.merged_image,
                QRect(0, source_y, self.merged_image.width(), source_h)
            )
            painter.setClipping(False)
            
            # 绘制滚动条
            if scaled_height > inner_rect.height():
                self._draw_scrollbar(painter, inner_rect, scaled_height)
        else:
            # 空状态
            painter.setPen(self.TEXT_SECONDARY)
            painter.setFont(QFont("Segoe UI", 11))
            
            # 图标
            icon_y = inner_rect.y() + inner_rect.height() // 2 - 30
            painter.setFont(QFont("Segoe UI", 24))
            painter.drawText(inner_rect.x(), icon_y, inner_rect.width(), 40,
                           Qt.AlignmentFlag.AlignCenter, "⬇")
            
            # 提示文字
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(inner_rect.x(), icon_y + 40, inner_rect.width(), 30,
                           Qt.AlignmentFlag.AlignCenter, "滚动页面开始捕获")
    
    def _draw_scrollbar(self, painter, rect: QRect, content_height: int):
        """绘制滚动条"""
        scrollbar_width = 4
        scrollbar_x = rect.right() - scrollbar_width - 4
        scrollbar_height = rect.height() - 8
        scrollbar_y = rect.y() + 4
        
        visible_ratio = rect.height() / content_height
        thumb_height = max(30, int(scrollbar_height * visible_ratio))
        
        scroll_range = content_height - rect.height()
        thumb_pos = int((self.scroll_offset / scroll_range) * (scrollbar_height - thumb_height)) if scroll_range > 0 else 0
        
        # 轨道
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 15))
        painter.drawRoundedRect(scrollbar_x, scrollbar_y, scrollbar_width, scrollbar_height, 2, 2)
        
        # 滑块
        painter.setBrush(QColor(0, 0, 0, 60))
        painter.drawRoundedRect(scrollbar_x, scrollbar_y + thumb_pos, scrollbar_width, thumb_height, 2, 2)
    
    def _draw_footer(self, painter, main_rect):
        """绘制底部控制区域"""
        footer_y = main_rect.height() - 85
        
        # 分隔线
        painter.setPen(QPen(self.BORDER_COLOR, 1))
        painter.drawLine(20, footer_y, main_rect.width() - 20, footer_y)
        
        # 提示文字
        painter.setPen(self.TEXT_SECONDARY)
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(24, footer_y + 25, "手动滚动预览 · ESC 取消")
        
        # 按钮区域
        btn_y = footer_y + 40
        btn_height = 36
        btn_spacing = 10
        
        # 取消按钮
        cancel_width = 80
        self._cancel_btn_rect = QRect(24, btn_y, cancel_width, btn_height)
        
        if self._hover_cancel:
            painter.setBrush(QColor(243, 244, 246))
        else:
            painter.setBrush(QColor(255, 255, 255))
        painter.setPen(QPen(QColor(0, 0, 0, 40), 1))
        painter.drawRoundedRect(self._cancel_btn_rect, 8, 8)
        
        painter.setPen(self.TEXT_COLOR)
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(self._cancel_btn_rect, Qt.AlignmentFlag.AlignCenter, "取消")
        
        # 完成按钮
        finish_width = main_rect.width() - 48 - cancel_width - btn_spacing
        self._finish_btn_rect = QRect(24 + cancel_width + btn_spacing, btn_y, finish_width, btn_height)
        
        if self._hover_finish:
            painter.setBrush(self.SUCCESS_COLOR.lighter(110))
        else:
            painter.setBrush(self.SUCCESS_COLOR)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self._finish_btn_rect, 8, 8)
        
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        painter.drawText(self._finish_btn_rect, Qt.AlignmentFlag.AlignCenter, "完成截图")
    
    def wheelEvent(self, event):
        """鼠标滚轮滚动预览"""
        if self.merged_image and not self.merged_image.isNull():
            delta = event.angleDelta().y()
            self.scroll_offset -= delta
            
            scaled_height = self.merged_image.height() * self.preview_scale
            visible_height = self.height() - 160
            max_scroll = max(0, scaled_height - visible_height)
            self.scroll_offset = max(0, min(max_scroll, self.scroll_offset))
            
            self.update()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查按钮点击
            if hasattr(self, '_finish_btn_rect') and self._finish_btn_rect.contains(event.pos()):
                self.finish_clicked.emit()
                return
            if hasattr(self, '_cancel_btn_rect') and self._cancel_btn_rect.contains(event.pos()):
                self.cancel_clicked.emit()
                return
            
            self.dragging = True
            self.last_mouse_y = event.pos().y()
    
    def mouseMoveEvent(self, event):
        # 更新悬停状态
        old_hover_finish = self._hover_finish
        old_hover_cancel = self._hover_cancel
        
        self._hover_finish = hasattr(self, '_finish_btn_rect') and self._finish_btn_rect.contains(event.pos())
        self._hover_cancel = hasattr(self, '_cancel_btn_rect') and self._cancel_btn_rect.contains(event.pos())
        
        if old_hover_finish != self._hover_finish or old_hover_cancel != self._hover_cancel:
            self.update()
        
        # 更新鼠标样式
        if self._hover_finish or self._hover_cancel:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        
        if self.dragging and self.merged_image:
            delta = self.last_mouse_y - event.pos().y()
            self.scroll_offset += delta
            self.last_mouse_y = event.pos().y()
            
            # 限制滚动范围
            scaled_height = self.merged_image.height() * self.preview_scale
            visible_height = self.height() - 160
            max_scroll = max(0, scaled_height - visible_height)
            self.scroll_offset = max(0, min(max_scroll, self.scroll_offset))
            
            self.update()
    
    def mouseReleaseEvent(self, event):
        self.dragging = False
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_clicked.emit()
        elif event.key() == Qt.Key.Key_Return:
            self.finish_clicked.emit()


class ScrollCaptureWindow(QWidget):
    """滚动截图窗口 - 带实时预览"""
    
    capture_completed = Signal(object)  # 支持 QPixmap 或 QImage (用于超大长图)
    capture_cancelled = Signal()
    
    MAX_SCROLL_HEIGHT = 200000  # 最大截图高度限制 (20万像素)
    
    def __init__(self, screen_capture):
        super().__init__()
        self.screen_capture = screen_capture
        self.captures = []  # 存储原始帧（可选，用于最后精修）
        self.merged_image = None  # 当前合并的长图 (QImage)
        self.last_frame = None  # 上一帧图像 (QImage)
        self.is_capturing = False
        
        # 选区状态
        self.selecting = False
        self.selection = QRect()
        self.start_pos = QPoint()
        self.background = None
        
        # 预览面板
        self.preview_panel = None
        
        self._setup_ui()

    def _setup_ui(self):
        # 全屏覆盖
        screens = QGuiApplication.screens()
        total_rect = QRect()
        for screen in screens:
            total_rect = total_rect.united(screen.geometry())
        
        self.setGeometry(total_rect)
        self.screen_offset = QPoint(total_rect.x(), total_rect.y())
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Popup
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # 工具栏
        self.toolbar = self._create_toolbar()
        self.toolbar.hide()
        
        # 截图定时器
        self.capture_timer = QTimer()
        self.capture_timer.timeout.connect(self._capture_current)
    
    def _create_toolbar(self):
        """创建工具栏 - 现代化白色风格"""
        toolbar = QFrame(self)
        toolbar.setObjectName("scrollToolbar")
        toolbar.setStyleSheet("""
            QFrame#scrollToolbar {
                background: rgba(255, 255, 255, 0.95);
                border-radius: 12px;
                border: 1px solid rgba(0, 0, 0, 0.05);
            }
        """)
        
        # 添加阴影效果
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        toolbar.setGraphicsEffect(shadow)
        
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(15, 8, 15, 8)
        layout.setSpacing(12)
        
        # 尺寸标签
        self.size_label = QLabel("0 × 0")
        self.size_label.setStyleSheet("""
            color: #333; 
            font-size: 13px; 
            font-weight: 600;
            background: rgba(0, 0, 0, 0.05);
            padding: 4px 10px;
            border-radius: 6px;
        """)
        layout.addWidget(self.size_label)
        
        # 分隔线
        sep = QFrame()
        sep.setFixedSize(1, 20)
        sep.setStyleSheet("background: rgba(0, 0, 0, 0.1);")
        layout.addWidget(sep)
        
        # 开始按钮
        self.start_btn = QPushButton("开始捕获")
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setStyleSheet(self._btn_style("#2563EB", "#1D4ED8"))
        self.start_btn.clicked.connect(self._start_capture)
        layout.addWidget(self.start_btn)
        
        # 提示文字
        hint = QLabel("点击开始后滚动页面")
        hint.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(hint)
        
        # 取消按钮 (美化图标)
        cancel_btn = QPushButton("✕")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setFixedSize(30, 30)
        # 使用更精致的关闭按钮样式
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #FEE2E2;
                color: #EF4444;
                border: none;
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
                padding-bottom: 2px;
            }
            QPushButton:hover {
                background: #EF4444;
                color: white;
            }
        """)
        cancel_btn.clicked.connect(self._cancel)
        layout.addWidget(cancel_btn)
        
        toolbar.adjustSize()
        return toolbar
    
    def _btn_style(self, bg="#555", hover="#666"):
        return f"""
            QPushButton {{
                background: {bg};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{ 
                background: {hover}; 
                margin-top: -1px;
            }}
            QPushButton:pressed {{
                margin-top: 1px;
            }}
            QPushButton:disabled {{ 
                background: #E5E7EB; 
                color: #9CA3AF; 
            }}
        """

    def showEvent(self, event):
        self.background = self.screen_capture.capture_all_screens()
        super().showEvent(event)
        self.activateWindow()
        self.setFocus()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 背景
        if self.background:
            painter.drawPixmap(0, 0, self.background)
        
        # 遮罩
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        
        # 选区
        if not self.selection.isNull():
            if self.background:
                painter.drawPixmap(self.selection, self.background, self.selection)
            
            # 边框颜色根据状态变化
            color = QColor(0, 200, 100) if self.is_capturing else QColor(0, 150, 255)
            pen = QPen(color, 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.selection)
            
            # 尺寸标签
            self._draw_size_label(painter)
            
            # 捕获状态指示
            if self.is_capturing:
                self._draw_capture_indicator(painter)
        
        # 提示
        if self.selection.isNull():
            painter.setPen(Qt.GlobalColor.white)
            painter.setFont(QFont("Microsoft YaHei", 12))
            painter.drawText(20, 35, "拖动选择滚动区域 | ESC 取消")
    
    def _draw_size_label(self, painter):
        text = f"{self.selection.width()} × {self.selection.height()}"
        font = QFont("Microsoft YaHei", 10)
        painter.setFont(font)
        
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(text) + 12
        th = fm.height() + 6
        
        x = self.selection.left()
        y = self.selection.top() - th - 4
        if y < 0:
            y = self.selection.bottom() + 4
        
        painter.fillRect(x, y, tw, th, QColor(0, 0, 0, 180))
        painter.setPen(Qt.GlobalColor.white)
        painter.drawText(x + 6, y + th - 5, text)

    def _draw_capture_indicator(self, painter):
        """绘制捕获状态指示器"""
        # 闪烁的录制指示点
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 0, 0))
        x = self.selection.right() - 15
        y = self.selection.top() + 10
        painter.drawEllipse(x, y, 10, 10)
        
        # 显示已捕获数量
        painter.setPen(Qt.GlobalColor.white)
        painter.setFont(QFont("Microsoft YaHei", 9))
        painter.drawText(x - 50, y + 9, f"捕获中: {len(self.captures)}")
    
    def _update_toolbar_pos(self):
        if self.selection.isNull():
            return
        
        self.toolbar.adjustSize()
        tw = self.toolbar.width()
        th = self.toolbar.height()
        
        x = self.selection.right() - tw
        y = self.selection.bottom() + 8
        
        if y + th > self.height():
            y = self.selection.top() - th - 8
        if x < 0:
            x = 0
        
        self.toolbar.move(x, y)
        self.toolbar.show()
        self.size_label.setText(f"{self.selection.width()} × {self.selection.height()}")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_capturing:
                return
            self.selecting = True
            self.start_pos = event.pos()
            self.selection = QRect()
            self.toolbar.hide()
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            if self.selection.isNull():
                self._cancel()
            else:
                self.selection = QRect()
                self.toolbar.hide()
                self.captures.clear()
                self.merged_image = None
                self.update()
    
    def mouseMoveEvent(self, event):
        if self.selecting:
            self.selection = QRect(self.start_pos, event.pos()).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.selecting:
            self.selecting = False
            if self.selection.width() > 50 and self.selection.height() > 50:
                self._update_toolbar_pos()
            else:
                self.selection = QRect()
            self.update()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self.is_capturing:
                self._stop_capture()
            self._cancel()
        elif event.key() == Qt.Key.Key_Return:
            if self.captures:
                self._finish()
            elif not self.selection.isNull() and not self.is_capturing:
                self._start_capture()
        elif event.key() == Qt.Key.Key_Space:
            if not self.selection.isNull() and not self.is_capturing:
                self._start_capture()

    def _start_capture(self):
        """开始捕获"""
        if self.selection.isNull():
            return
        
        self.is_capturing = True
        self.captures.clear()
        self.merged_image = None
        self.last_frame = None
        
        # 创建并显示实时预览面板
        self._show_preview_panel()
        
        # 隐藏主窗口和工具栏
        self.toolbar.hide()
        self.hide()
        QApplication.processEvents()
        time.sleep(0.15)
        
        # 截取第一帧
        self._capture_current()
        
        # 启动定时器，频率更高一些 (100ms)
        self.capture_timer.start(100)
    
    def _stop_capture(self):
        """停止捕获"""
        self.capture_timer.stop()
        self.is_capturing = False
    
    def _show_preview_panel(self):
        """显示实时预览面板"""
        if self.preview_panel is None:
            self.preview_panel = RealtimePreviewPanel()
            self.preview_panel.finish_clicked.connect(self._finish)
            self.preview_panel.cancel_clicked.connect(self._cancel)
        
        self.preview_panel.position_next_to(self.selection, self.screen_offset)
        self.preview_panel.update_preview(QImage(), 0)
        self.preview_panel.show()
        self.preview_panel.activateWindow()
    
    def _hide_preview_panel(self):
        """隐藏预览面板"""
        if self.preview_panel:
            self.preview_panel.hide()
    
    def _capture_current(self):
        """捕获当前区域并进行增量合并"""
        if self.merged_image and self.merged_image.height() >= self.MAX_SCROLL_HEIGHT:
            # 已达到最大高度，停止捕获
            self._stop_capture()
            return
            
        rect = (
            self.selection.x() + self.screen_offset.x(),
            self.selection.y() + self.screen_offset.y(),
            self.selection.width(),
            self.selection.height()
        )
        
        pixmap = self.screen_capture.capture_region(*rect)
        if pixmap.isNull():
            return
        
        curr_image = pixmap.toImage()
        
        # 第一帧处理
        if self.merged_image is None:
            self.merged_image = curr_image
            self.last_frame = curr_image
            self.captures.append(curr_image) # 存储为 QImage 以节省 GPU 内存
            self._update_merged_preview()
            return
            
        # 检查是否与上一帧完全相同（无滚动）
        if self._is_same_image(self.last_frame, curr_image):
            return
            
        # 查找重叠位置
        overlap, direction = self._find_overlap_cv2(self.last_frame, curr_image)
        
        # 如果找到有效的重叠
        if overlap > 0:
            # 计算新增加的部分
            new_height = curr_image.height() - overlap
            if new_height > 0:
                # 增量更新长图
                self._append_to_merged(pixmap, overlap, new_height, direction)
                self.last_frame = curr_image
                self.captures.append(curr_image) # 存储为 QImage 以节省 GPU 内存
                self._update_merged_preview()
        elif overlap == -1:
            # 未找到重叠，尝试普通算法 (仅向下)
            overlap = self._find_overlap(self.last_frame, curr_image)
            if overlap > 0:
                new_height = curr_image.height() - overlap
                if new_height > 0:
                    self._append_to_merged(pixmap, overlap, new_height, 1)
                    self.last_frame = curr_image
                    self.captures.append(curr_image)
                    self._update_merged_preview()

    def _append_to_merged(self, new_pixmap: QPixmap, overlap: int, new_height: int, direction: int = 1):
        """增量拼接新内容到现有长图
        
        Args:
            new_pixmap: 新截图
            overlap: 重叠高度
            new_height: 新增内容的净高度 (curr_h - overlap)
            direction: 1 表示向下滚动 (拼接在底部), -1 表示向上滚动 (拼接在顶部)
        """
        new_img = new_pixmap.toImage()
        
        if self.merged_image is None:
            self.merged_image = new_img
            return
            
        old_width = self.merged_image.width()
        old_height = self.merged_image.height()
        
        # 创建新的大图 (使用 QImage 以支持超大尺寸)
        new_total_height = old_height + new_height
        
        # 限制最大高度
        if new_total_height > self.MAX_SCROLL_HEIGHT:
            new_total_height = self.MAX_SCROLL_HEIGHT
            # 如果超过限制，我们只能截断新增部分
            new_height = new_total_height - old_height
            if new_height <= 0:
                self._stop_capture()
                return

        combined_img = QImage(old_width, new_total_height, QImage.Format.Format_ARGB32)
        combined_img.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(combined_img)
        
        if direction == 1:
            # 向下滚动：旧图在上，新图在下
            painter.drawImage(0, 0, self.merged_image)
            # 只绘制新帧中非重叠的部分 (从 overlap 开始到 height)
            # drawImage(x, y, image, sx, sy, sw, sh)
            painter.drawImage(0, old_height, new_img, 0, overlap, old_width, new_height)
        else:
            # 向上滚动：新图在上，旧图在下
            # 新图绘制在顶部 (0, 0)，绘制高度为 new_height (即新图的顶部部分)
            # 新图底部 overlap 部分与旧图顶部 overlap 部分重叠
            # 我们取新图的 Top (new_height) 部分
            painter.drawImage(0, 0, new_img, 0, 0, old_width, new_height)
            # 旧图绘制在下方
            painter.drawImage(0, new_height, self.merged_image)
            
        painter.end()
        
        self.merged_image = combined_img

    def _qimage_to_cv2(self, qimg: QImage):
        """QImage 转换为 OpenCV 格式 (Gray)，处理字节对齐问题"""
        # 转换为 8 位灰度图
        qimg = qimg.convertToFormat(QImage.Format.Format_Grayscale8)
        width = qimg.width()
        height = qimg.height()
        bytes_per_line = qimg.bytesPerLine()
        
        # 获取内存视图
        ptr = qimg.constBits()
        
        # 关键修复：QImage 的内存布局通常会有字节对齐（padding）
        # 实际每行的字节数是 bytes_per_line，可能大于 width
        arr = np.array(ptr, dtype=np.uint8).reshape((height, bytes_per_line))
        
        # 如果存在 padding，则切片取实际有效的宽度部分
        if bytes_per_line > width:
            arr = arr[:, :width]
            
        return arr

    def _find_overlap_cv2(self, prev_img: QImage, curr_img: QImage) -> tuple[int, int]:
        """使用 OpenCV 模板匹配查找重叠区域
        Returns:
            (overlap_height, direction)
            direction: 1 (down), -1 (up), 0 (none)
        """
        if not HAS_CV2:
            return self._find_overlap(prev_img, curr_img), 1
            
        # 转换为灰度图进行匹配，提高速度
        img1 = self._qimage_to_cv2(prev_img)
        img2 = self._qimage_to_cv2(curr_img)
        
        h, w = img1.shape
        
        # 为了避免侧边滚动条干扰，切除左右各 15% 的区域
        margin = int(w * 0.15)
        if w - 2 * margin > 50:
            img1 = img1[:, margin:-margin]
            img2 = img2[:, margin:-margin]
            w_match = img1.shape[1]
        else:
            w_match = w

        template_h = min(50, h // 4)
        if template_h < 10: return -1, 0
        
        # --- 1. 尝试检测向下滚动 (Last Frame Top vs Curr Frame Bottom) ---
        # 错误修正：向下滚动时，prev_img (上图) 的底部 与 curr_img (下图) 的顶部重叠
        # Template: prev_img 底部
        # Search: curr_img 顶部
        
        template_down = img1[h-template_h:h, :]
        search_down = img2[0:min(h, h//2 + 50), :] # 搜索下半张图的顶部区域? 不，搜索整张图的上半部分
        
        res_down = cv2.matchTemplate(search_down, template_down, cv2.TM_CCOEFF_NORMED)
        min_val_d, max_val_d, min_loc_d, max_loc_d = cv2.minMaxLoc(res_down)
        
        # --- 2. 尝试检测向上滚动 (Last Frame Bottom vs Curr Frame Top) ---
        # 向上滚动时，curr_img (上图) 的底部 与 prev_img (下图) 的顶部重叠
        # 这意味着 curr_img 在 prev_img 之上。
        # 所以 prev_img 的顶部 应该出现在 curr_img 的底部。
        # Template: prev_img 顶部
        # Search: curr_img 底部
        
        template_up = img1[0:template_h, :]
        search_up = img2[max(0, h - (h//2 + 50)):h, :] # 搜索整张图的下半部分
        
        res_up = cv2.matchTemplate(search_up, template_up, cv2.TM_CCOEFF_NORMED)
        min_val_u, max_val_u, min_loc_u, max_loc_u = cv2.minMaxLoc(res_up)
        
        best_overlap = -1
        direction = 0
        
        # 阈值判断
        threshold = 0.8
        
        score_down = max_val_d if max_val_d > threshold else 0
        score_up = max_val_u if max_val_u > threshold else 0
        
        if score_down == 0 and score_up == 0:
            return -1, 0
            
        if score_down >= score_up:
            # 向下滚动匹配成功
            match_y = max_loc_d[1]
            # 重叠高度 = 匹配位置 + 模板高度
            # 匹配位置是相对于 search_down (即 curr_img 顶部) 的 offset
            # 所以 curr_img 顶部 match_y 处开始是重叠
            # 重叠结束于 match_y + template_h
            # 所以重叠高度 = match_y + template_h
            best_overlap = match_y + template_h
            direction = 1
        else:
            # 向上滚动匹配成功
            # match_y 是相对于 search_up 的 offset
            # search_up 也就是 curr_img 的底部区域
            # search_up_start_y = max(0, h - (h//2 + 50))
            search_up_start_y = max(0, h - (h//2 + 50))
            
            # 在 curr_img 中的实际 y = search_up_start_y + match_y
            actual_y_in_curr = search_up_start_y + max_loc_u[1]
            
            # 模板 (prev_img 顶部) 匹配到了 curr_img 的 actual_y_in_curr 位置
            # 这意味着 curr_img 从 actual_y_in_curr 开始与 prev_img 重叠
            # 所以 curr_img 底部 (h) - actual_y_in_curr = 重叠高度
            # 验证：如果匹配在最底部 (h-template_h)，则 overlap = template_h
            best_overlap = h - actual_y_in_curr
            direction = -1
            
        return best_overlap, direction

    def _is_same_image(self, img1: QImage, img2: QImage) -> bool:
        """更快速、准确的相同图片检测"""
        if img1.size() != img2.size():
            return False
            
        # 采样 10 个随机点比较即可，如果这 10 个点都一样，大概率是同一张图（无滚动）
        # 或者直接比较一小块区域
        w, h = img1.width(), img1.height()
        samples = [
            (w // 2, h // 2), (w // 4, h // 4), (3 * w // 4, 3 * w // 4),
            (w // 4, 3 * w // 4), (3 * w // 4, h // 4),
            (w // 2, h // 4), (w // 2, 3 * h // 4),
            (w // 4, h // 2), (3 * w // 4, h // 2)
        ]
        
        for x, y in samples:
            if img1.pixel(x, y) != img2.pixel(x, y):
                return False
        return True
    
    def _update_merged_preview(self):
        """更新预览图"""
        if self.merged_image and not self.merged_image.isNull():
            # 直接调用预览面板的更新方法，它会处理缩放
            if self.preview_panel:
                self.preview_panel.update_preview(self.merged_image, len(self.captures))
    
    def _merge_captures(self) -> QImage:
        """合并所有截图 (优化版：假设 captures 中全是 QImage)"""
        if not self.captures:
            return QImage()
        
        first_frame = self.captures[0]
        if len(self.captures) == 1:
            return first_frame
        
        # 计算所有重叠区域
        overlaps = []
        for i in range(1, len(self.captures)):
            prev_img = self.captures[i-1]
            curr_img = self.captures[i]
            
            overlap = self._find_overlap_cv2(prev_img, curr_img)
            if overlap == -1:
                overlap = self._find_overlap(prev_img, curr_img)
            overlaps.append(max(0, overlap))
        
        # 计算总高度
        width = first_frame.width()
        total_height = first_frame.height()
        for i, overlap in enumerate(overlaps):
            total_height += self.captures[i+1].height() - overlap
        
        # 限制最大高度
        if total_height > self.MAX_SCROLL_HEIGHT:
            total_height = self.MAX_SCROLL_HEIGHT
        
        # 创建结果图像
        result_img = QImage(width, total_height, QImage.Format.Format_ARGB32)
        result_img.fill(Qt.GlobalColor.white)
        
        painter = QPainter(result_img)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # 绘制第一张图
        painter.drawImage(0, 0, first_frame)
            
        current_y = first_frame.height()
        
        # 绘制后续图片
        for i, overlap in enumerate(overlaps):
            curr_frame = self.captures[i+1]
            
            # 计算这一帧要绘制的高度
            frame_h = curr_frame.height()
            draw_h = frame_h - overlap
            
            if current_y + draw_h > total_height:
                draw_h = total_height - current_y
                
            if draw_h > 0:
                painter.drawImage(0, current_y, curr_frame, 0, overlap, width, draw_h)
                current_y += draw_h
            
            if current_y >= total_height:
                break
        
        painter.end()
        return result_img

    def _find_overlap(self, img1: QImage, img2: QImage) -> int:
        """查找两张图片的重叠区域
        
        算法：取img1底部的一个条带，在img2中搜索这个条带的位置
        这样可以直接找到img1底部在img2中对应的位置
        """
        h1, h2 = img1.height(), img2.height()
        w = min(img1.width(), img2.width())
        
        if h1 < 30 or h2 < 30 or w < 30:
            return 0
        
        # 条带高度（用于匹配的参考区域）
        strip_height = min(15, h1 // 10, h2 // 10)
        if strip_height < 5:
            strip_height = 5
        
        # 采样点
        num_samples = min(60, w // 3)
        sample_x = [int(w * i / num_samples) for i in range(num_samples)]
        
        # 提取img1底部条带的特征
        # 条带位置：img1的最底部往上strip_height像素
        strip_start_in_img1 = h1 - strip_height
        
        # 计算条带的像素数据
        def get_strip_data(img, start_y, height):
            data = []
            for dy in range(height):
                y = start_y + dy
                if y >= img.height():
                    break
                row = []
                for x in sample_x:
                    if 0 <= x < img.width():
                        p = img.pixel(x, y)
                        row.append(((p & 0xFF), ((p >> 8) & 0xFF), ((p >> 16) & 0xFF)))
                data.append(row)
            return data
        
        def compare_strips(strip1, strip2):
            """比较两个条带的相似度"""
            if len(strip1) != len(strip2):
                return 99999
            total_diff = 0
            count = 0
            for row1, row2 in zip(strip1, strip2):
                for (r1, g1, b1), (r2, g2, b2) in zip(row1, row2):
                    total_diff += abs(r1 - r2) + abs(g1 - g2) + abs(b1 - b2)
                    count += 1
            return total_diff / count if count > 0 else 99999
        
        # 提取img1底部条带
        ref_strip = get_strip_data(img1, strip_start_in_img1, strip_height)
        
        # 在img2中搜索这个条带
        # 搜索范围：img2的前90%区域
        search_end = int(h2 * 0.9)
        
        best_match_y = -1
        best_diff = 99999
        
        for y2 in range(0, search_end):
            # 提取img2中从y2开始的条带
            test_strip = get_strip_data(img2, y2, strip_height)
            
            if len(test_strip) < strip_height:
                continue
            
            diff = compare_strips(ref_strip, test_strip)
            
            if diff < best_diff:
                best_diff = diff
                best_match_y = y2
        
        # 如果找到了好的匹配
        if best_match_y >= 0 and best_diff < 20:
            # 重叠区域 = img1底部条带在img2中的位置 + 条带高度
            # 也就是说，img2从0到(best_match_y + strip_height)的部分与img1底部重叠
            overlap = best_match_y + strip_height
            
            # 验证：额外检查重叠区域的其他部分
            if overlap > 10:
                verify_ok = True
                # 检查重叠区域的中间部分
                check_y1 = h1 - overlap + overlap // 2
                check_y2 = overlap // 2
                
                if 0 <= check_y1 < h1 and 0 <= check_y2 < h2:
                    mid_diff = 0
                    mid_count = 0
                    for x in sample_x:
                        if 0 <= x < w:
                            p1 = img1.pixel(x, check_y1)
                            p2 = img2.pixel(x, check_y2)
                            mid_diff += abs((p1 & 0xFF) - (p2 & 0xFF))
                            mid_diff += abs(((p1 >> 8) & 0xFF) - ((p2 >> 8) & 0xFF))
                            mid_diff += abs(((p1 >> 16) & 0xFF) - ((p2 >> 16) & 0xFF))
                            mid_count += 1
                    
                    if mid_count > 0 and mid_diff / mid_count > 40:
                        verify_ok = False
                
                if verify_ok:
                    return overlap
        
        return 0
    
    def _finish(self):
        """完成截图"""
        self._stop_capture()
        self._hide_preview_panel()
        
        if not self.captures:
            self._cancel()
            return
        
        # 最终合并
        if self.merged_image is None or self.merged_image.isNull():
            self.merged_image = self._merge_captures()
        
        if not self.merged_image.isNull():
            # 发送合并后的图像 (QImage)
            # EditorWindow.setPixmap 已支持 QImage
            self.capture_completed.emit(self.merged_image)
        
        self.close()
    
    def _cancel(self):
        """取消"""
        self._stop_capture()
        self._hide_preview_panel()
        self.capture_cancelled.emit()
        self.close()
