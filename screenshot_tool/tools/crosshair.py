"""
坐标轴工具 - 增强版
支持：坐标锁定、相对位移显示、多坐标对比模式
"""
from PySide6.QtWidgets import QWidget, QApplication, QLabel, QMenu
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QCursor, QGuiApplication, QAction


class CrosshairWindow(QWidget):
    """坐标轴窗口 - 增强版"""
    
    def __init__(self, config=None):
        super().__init__()
        self.config = config
        
        # 锁定的坐标点
        self.locked_points = []  # [(x, y, color), ...]
        self.max_locked = 5
        self.colors = [
            QColor(255, 0, 0),    # 红
            QColor(0, 255, 0),    # 绿
            QColor(0, 150, 255),  # 蓝
            QColor(255, 200, 0),  # 黄
            QColor(255, 0, 255),  # 紫
        ]
        
        # 当前坐标是否冻结
        self.frozen = False
        self.frozen_pos = QPoint()
        
        self.setup_ui()
        self.setup_timer()
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        
        # 全屏
        screen = QGuiApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        
        # 信息标签
        self.info_label = QLabel(self)
        self.info_label.setStyleSheet("""
            QLabel {
                background: rgba(0, 0, 0, 0.85);
                color: white;
                padding: 10px 15px;
                border-radius: 6px;
                font-size: 12px;
                font-family: Consolas;
            }
        """)
        self.info_label.hide()
        
        self.cursor_pos = QPoint()
    
    def setup_timer(self):
        """设置定时器"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_position)
        self.timer.start(16)  # ~60fps
    
    def update_position(self):
        """更新位置"""
        if not self.frozen:
            self.cursor_pos = QCursor.pos()
        
        self.update()
        self._update_info_label()
    
    def _update_info_label(self):
        """更新信息标签"""
        lines = [f"当前: X={self.cursor_pos.x()}  Y={self.cursor_pos.y()}"]
        
        if self.frozen:
            lines[0] = f"🔒 锁定: X={self.cursor_pos.x()}  Y={self.cursor_pos.y()}"
        
        # 显示与锁定点的相对位移
        for i, (x, y, color) in enumerate(self.locked_points):
            dx = self.cursor_pos.x() - x
            dy = self.cursor_pos.y() - y
            sign_x = "+" if dx >= 0 else ""
            sign_y = "+" if dy >= 0 else ""
            lines.append(f"点{i+1}: ΔX={sign_x}{dx}  ΔY={sign_y}{dy}")
        
        lines.append("")
        lines.append("Space=锁定 | L=添加对比点 | C=清除 | ESC=退出")
        
        self.info_label.setText("\n".join(lines))
        self.info_label.adjustSize()
        
        # 定位标签
        label_x = self.cursor_pos.x() + 25
        label_y = self.cursor_pos.y() + 25
        
        # 确保标签在屏幕内
        if label_x + self.info_label.width() > self.width():
            label_x = self.cursor_pos.x() - self.info_label.width() - 15
        if label_y + self.info_label.height() > self.height():
            label_y = self.cursor_pos.y() - self.info_label.height() - 15
        
        self.info_label.move(label_x, label_y)
        self.info_label.show()
    
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制锁定点的十字线
        for x, y, color in self.locked_points:
            self._draw_crosshair(painter, QPoint(x, y), color, dashed=True)
        
        # 绘制当前十字线
        main_color = QColor(255, 255, 0) if self.frozen else QColor(255, 0, 0)
        self._draw_crosshair(painter, self.cursor_pos, main_color, dashed=False)
        
        # 绘制锁定点标记
        for i, (x, y, color) in enumerate(self.locked_points):
            self._draw_point_marker(painter, QPoint(x, y), color, i + 1)
        
        # 绘制距离线
        if self.locked_points:
            self._draw_distance_lines(painter)
    
    def _draw_crosshair(self, painter, pos: QPoint, color: QColor, dashed: bool):
        """绘制十字线"""
        if dashed:
            pen = QPen(color, 1, Qt.PenStyle.DashLine)
        else:
            pen = QPen(color, 1, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        
        # 水平线
        painter.drawLine(0, pos.y(), self.width(), pos.y())
        # 垂直线
        painter.drawLine(pos.x(), 0, pos.x(), self.height())
        
        # 绘制中心圆
        painter.setPen(QPen(color, 2))
        painter.drawEllipse(pos, 10, 10)
        
        # 绘制刻度
        self._draw_scale(painter, pos, color)
    
    def _draw_scale(self, painter, pos: QPoint, color: QColor):
        """绘制刻度"""
        painter.setPen(QPen(color.darker(120), 1))
        font = QFont("Arial", 8)
        painter.setFont(font)
        
        # 水平刻度
        for i in range(-500, 501, 50):
            x = pos.x() + i
            if 0 <= x <= self.width():
                if i % 100 == 0:
                    painter.drawLine(x, pos.y() - 8, x, pos.y() + 8)
                    if i != 0:
                        painter.drawText(x - 15, pos.y() - 12, str(abs(i)))
                else:
                    painter.drawLine(x, pos.y() - 4, x, pos.y() + 4)
        
        # 垂直刻度
        for i in range(-500, 501, 50):
            y = pos.y() + i
            if 0 <= y <= self.height():
                if i % 100 == 0:
                    painter.drawLine(pos.x() - 8, y, pos.x() + 8, y)
                    if i != 0:
                        painter.drawText(pos.x() + 12, y + 4, str(abs(i)))
                else:
                    painter.drawLine(pos.x() - 4, y, pos.x() + 4, y)
    
    def _draw_point_marker(self, painter, pos: QPoint, color: QColor, number: int):
        """绘制锁定点标记"""
        painter.setBrush(color)
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        painter.drawEllipse(pos, 12, 12)
        
        # 绘制编号
        painter.setPen(Qt.GlobalColor.white)
        font = QFont("Arial", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pos.x() - 4, pos.y() + 4, str(number))
    
    def _draw_distance_lines(self, painter):
        """绘制到锁定点的距离线"""
        for x, y, color in self.locked_points:
            locked_pos = QPoint(x, y)
            
            # 绘制连接线
            painter.setPen(QPen(color, 1, Qt.PenStyle.DotLine))
            painter.drawLine(self.cursor_pos, locked_pos)
            
            # 计算距离
            import math
            dx = self.cursor_pos.x() - x
            dy = self.cursor_pos.y() - y
            distance = math.sqrt(dx*dx + dy*dy)
            
            # 在中点显示距离
            mid_x = (self.cursor_pos.x() + x) // 2
            mid_y = (self.cursor_pos.y() + y) // 2
            
            painter.fillRect(mid_x - 25, mid_y - 10, 50, 20, QColor(0, 0, 0, 180))
            painter.setPen(color)
            font = QFont("Arial", 9)
            painter.setFont(font)
            painter.drawText(mid_x - 20, mid_y + 5, f"{distance:.1f}px")
    
    def keyPressEvent(self, event):
        """键盘事件"""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_Space:
            # 切换冻结状态
            self.frozen = not self.frozen
            if self.frozen:
                self.frozen_pos = QCursor.pos()
                self.cursor_pos = self.frozen_pos
        elif event.key() == Qt.Key.Key_L:
            # 添加锁定点
            self._add_locked_point()
        elif event.key() == Qt.Key.Key_C:
            # 清除所有锁定点
            self.locked_points.clear()
            self.frozen = False
    
    def _add_locked_point(self):
        """添加锁定点"""
        if len(self.locked_points) >= self.max_locked:
            # 移除最早的点
            self.locked_points.pop(0)
        
        color = self.colors[len(self.locked_points) % len(self.colors)]
        self.locked_points.append((self.cursor_pos.x(), self.cursor_pos.y(), color))
    
    def mousePressEvent(self, event):
        """鼠标点击"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 左键添加锁定点
            self._add_locked_point()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.pos())
    
    def _show_context_menu(self, pos):
        """显示右键菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #2d2d2d;
                color: white;
                border: 1px solid #555;
            }
            QMenu::item:selected { background: #0078D7; }
        """)
        
        freeze_action = QAction("解除锁定" if self.frozen else "锁定当前坐标", menu)
        freeze_action.triggered.connect(lambda: setattr(self, 'frozen', not self.frozen))
        menu.addAction(freeze_action)
        
        add_action = QAction("添加对比点", menu)
        add_action.triggered.connect(self._add_locked_point)
        menu.addAction(add_action)
        
        clear_action = QAction("清除所有对比点", menu)
        clear_action.triggered.connect(lambda: self.locked_points.clear())
        menu.addAction(clear_action)
        
        menu.addSeparator()
        
        close_action = QAction("关闭", menu)
        close_action.triggered.connect(self.close)
        menu.addAction(close_action)
        
        menu.exec(self.mapToGlobal(pos))
    
    def closeEvent(self, event):
        """关闭事件"""
        self.timer.stop()
        super().closeEvent(event)
