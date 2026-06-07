"""
取色器覆盖层
用于在屏幕上取色，被调色板调用
"""
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QTimer, QPoint, Signal, QRect
from PySide6.QtGui import QColor, QPixmap, QPainter, QCursor, QPen, QFont


class ColorPickerOverlay(QWidget):
    """取色器全屏覆盖层"""
    
    color_picked = Signal(QColor)
    cancelled = Signal()
    
    def __init__(self):
        super().__init__()
        self.current_color = QColor(0, 0, 0)
        self.background = None
        self._setup_ui()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_color)
        self.timer.setInterval(30)
    
    def _setup_ui(self):
        screens = QApplication.screens()
        total_rect = QRect()
        for screen in screens:
            total_rect = total_rect.united(screen.geometry())
        
        self.setGeometry(total_rect)
        self.screen_offset = QPoint(total_rect.x(), total_rect.y())
        
        # 使用 Popup 标志确保窗口能接收所有鼠标事件，即使有模态对话框
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Popup
        )
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def showEvent(self, event):
        self.background = self._capture_screen()
        super().showEvent(event)
        # 确保窗口获得焦点
        self.activateWindow()
        self.setFocus()
        self.raise_()
        self.timer.start()
    
    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def _capture_screen(self) -> QPixmap:
        screens = QApplication.screens()
        if not screens:
            return QPixmap()
        
        total_rect = QRect()
        for screen in screens:
            total_rect = total_rect.united(screen.geometry())
        
        result = QPixmap(total_rect.size())
        painter = QPainter(result)
        for screen in screens:
            geom = screen.geometry()
            pixmap = screen.grabWindow(0)
            painter.drawPixmap(geom.x() - total_rect.x(), geom.y() - total_rect.y(), pixmap)
        painter.end()
        return result
    
    def _update_color(self):
        pos = QCursor.pos()
        if self.background and not self.background.isNull():
            local_x = pos.x() - self.screen_offset.x()
            local_y = pos.y() - self.screen_offset.y()
            if 0 <= local_x < self.background.width() and 0 <= local_y < self.background.height():
                image = self.background.toImage()
                self.current_color = QColor(image.pixel(local_x, local_y))
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        
        if self.background and not self.background.isNull():
            painter.drawPixmap(0, 0, self.background)
        
        pos = QCursor.pos()
        local_x = pos.x() - self.screen_offset.x()
        local_y = pos.y() - self.screen_offset.y()
        
        self._draw_magnifier(painter, local_x, local_y)
        self._draw_color_info(painter, local_x, local_y)
    
    def _draw_magnifier(self, painter: QPainter, x: int, y: int):
        mag_size = 120
        scale = 8
        capture_size = mag_size // scale
        half = capture_size // 2
        
        mag_x = x + 30
        mag_y = y + 30
        
        if mag_x + mag_size > self.width():
            mag_x = x - mag_size - 30
        if mag_y + mag_size > self.height():
            mag_y = y - mag_size - 30
        
        painter.fillRect(mag_x - 2, mag_y - 2, mag_size + 4, mag_size + 4, QColor(40, 40, 40))
        
        if self.background and not self.background.isNull():
            image = self.background.toImage()
            for py in range(capture_size):
                for px in range(capture_size):
                    src_x = x - half + px
                    src_y = y - half + py
                    if 0 <= src_x < image.width() and 0 <= src_y < image.height():
                        color = QColor(image.pixel(src_x, src_y))
                        painter.fillRect(mag_x + px * scale, mag_y + py * scale, scale, scale, color)
        
        painter.setPen(QPen(QColor(60, 60, 60), 1))
        for i in range(capture_size + 1):
            painter.drawLine(mag_x + i * scale, mag_y, mag_x + i * scale, mag_y + mag_size)
            painter.drawLine(mag_x, mag_y + i * scale, mag_x + mag_size, mag_y + i * scale)
        
        center_x = mag_x + half * scale
        center_y = mag_y + half * scale
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawRect(center_x, center_y, scale, scale)

    def _draw_color_info(self, painter: QPainter, x: int, y: int):
        info_width = 180
        info_height = 80
        
        info_x = x + 160
        info_y = y + 30
        
        if info_x + info_width > self.width():
            info_x = x - info_width - 30
        if info_y + info_height > self.height():
            info_y = y - info_height - 30
        
        painter.fillRect(info_x, info_y, info_width, info_height, QColor(40, 40, 40, 230))
        
        painter.fillRect(info_x + 10, info_y + 10, 40, 40, self.current_color)
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawRect(info_x + 10, info_y + 10, 40, 40)
        
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Consolas", 11)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(info_x + 60, info_y + 28, self.current_color.name().upper())
        
        font.setBold(False)
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(QColor(180, 180, 180))
        rgb_text = f"RGB: {self.current_color.red()}, {self.current_color.green()}, {self.current_color.blue()}"
        painter.drawText(info_x + 60, info_y + 45, rgb_text)
        
        painter.drawText(info_x + 10, info_y + 70, f"X: {x + self.screen_offset.x()}  Y: {y + self.screen_offset.y()}")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.color_picked.emit(self.current_color)
            self.close()
        elif event.button() == Qt.MouseButton.RightButton:
            self.cancelled.emit()
            self.close()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self.close()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.color_picked.emit(self.current_color)
            self.close()
