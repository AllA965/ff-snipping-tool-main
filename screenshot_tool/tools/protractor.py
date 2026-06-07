"""
量角器工具 - 增强版
支持：三点测量模式、角度锁定、实时角度显示、测量记录导出
"""
import math
import csv
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QApplication, QMenu, QFileDialog,
    QLabel, QVBoxLayout, QHBoxLayout, QPushButton
)
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QCursor, QAction
from ui.icons import set_window_icon
from core.i18n import tr


class ProtractorWindow(QWidget):
    """量角器窗口 - 增强版"""
    
    def __init__(self, config=None):
        super().__init__()
        self.config = config
        
        # 三点测量模式
        self.center = QPoint(300, 300)  # 中心点
        self.point1 = QPoint(450, 300)  # 起始线端点
        self.point2 = QPoint(300, 150)  # 终止线端点
        
        self.radius = 150
        self.angle1 = 0  # 第一条线的角度
        self.angle2 = 90  # 第二条线的角度
        
        self.dragging = False
        self.dragging_point = None  # 'center', 'point1', 'point2'
        self.drag_start = QPoint()
        
        # 角度锁定
        self.angle_lock = 15  # 锁定间隔
        self.lock_enabled = False
        
        # 测量记录
        self.measurements = []
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("量角器")
        set_window_icon(self)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        
        # 全屏大小，允许在任意位置移动
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        
        # 初始位置在屏幕中央
        self.center = QPoint(screen.width() // 2, screen.height() // 2)
        self.point1 = QPoint(self.center.x() + 150, self.center.y())
        self.point2 = QPoint(self.center.x(), self.center.y() - 150)
        
        self._update_angles()
    
    def _update_angles(self):
        """根据点位置更新角度"""
        # 计算angle1 (center到point1的角度)
        dx1 = self.point1.x() - self.center.x()
        dy1 = self.center.y() - self.point1.y()
        self.angle1 = math.degrees(math.atan2(dy1, dx1))
        if self.angle1 < 0:
            self.angle1 += 360
        
        # 计算angle2 (center到point2的角度)
        dx2 = self.point2.x() - self.center.x()
        dy2 = self.center.y() - self.point2.y()
        self.angle2 = math.degrees(math.atan2(dy2, dx2))
        if self.angle2 < 0:
            self.angle2 += 360
    
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制半透明背景
        painter.fillRect(self.rect(), QColor(0, 0, 0, 30))
        
        # 绘制量角器圆弧
        painter.setPen(QPen(QColor(0, 120, 215), 2))
        painter.drawEllipse(self.center, self.radius, self.radius)
        
        # 绘制刻度
        self._draw_scale(painter)
        
        # 绘制两条测量线
        self._draw_lines(painter)
        
        # 绘制角度弧
        self._draw_angle_arc(painter)
        
        # 绘制角度显示
        self._draw_angle_info(painter)
        
        # 绘制控制点
        self._draw_control_points(painter)
        
        # 绘制帮助信息
        self._draw_help(painter)
    
    def _draw_scale(self, painter):
        """绘制刻度"""
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        font = QFont("Arial", 8)
        painter.setFont(font)
        
        for angle in range(0, 360, 5):
            rad = math.radians(angle)
            
            # 刻度线
            if angle % 30 == 0:
                inner_r = self.radius - 20
                # 绘制角度数字
                text_r = self.radius + 18
                text_x = self.center.x() + text_r * math.cos(rad) - 12
                text_y = self.center.y() - text_r * math.sin(rad) + 5
                painter.setPen(QColor(200, 200, 200))
                painter.drawText(int(text_x), int(text_y), f"{angle}°")
                painter.setPen(QPen(QColor(100, 100, 100), 1))
            elif angle % 15 == 0:
                inner_r = self.radius - 12
            else:
                inner_r = self.radius - 6
            
            x1 = self.center.x() + inner_r * math.cos(rad)
            y1 = self.center.y() - inner_r * math.sin(rad)
            x2 = self.center.x() + self.radius * math.cos(rad)
            y2 = self.center.y() - self.radius * math.sin(rad)
            
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
    
    def _draw_lines(self, painter):
        """绘制测量线"""
        # 第一条线（红色）- 起始线
        painter.setPen(QPen(QColor(255, 80, 80), 3))
        painter.drawLine(self.center, self.point1)
        
        # 第二条线（蓝色）- 终止线
        painter.setPen(QPen(QColor(80, 150, 255), 3))
        painter.drawLine(self.center, self.point2)
    
    def _draw_angle_arc(self, painter):
        """绘制角度弧"""
        # 计算角度差
        angle_diff = self.angle2 - self.angle1
        if angle_diff < 0:
            angle_diff += 360
        
        # 选择较小的角度
        if angle_diff > 180:
            start = self.angle2
            span = 360 - angle_diff
        else:
            start = self.angle1
            span = angle_diff
        
        # 绘制弧
        arc_radius = 50
        painter.setPen(QPen(QColor(0, 200, 100), 3))
        painter.drawArc(
            self.center.x() - arc_radius,
            self.center.y() - arc_radius,
            arc_radius * 2, arc_radius * 2,
            int(start * 16), int(span * 16)
        )
        
        # 填充扇形
        painter.setBrush(QColor(0, 200, 100, 50))
        painter.setPen(Qt.PenStyle.NoPen)
        
        path_points = [QPointF(self.center)]
        for a in range(int(start), int(start + span) + 1, 2):
            rad = math.radians(a)
            x = self.center.x() + arc_radius * math.cos(rad)
            y = self.center.y() - arc_radius * math.sin(rad)
            path_points.append(QPointF(x, y))
        path_points.append(QPointF(self.center))
        
        painter.drawPolygon(path_points)
    
    def _draw_angle_info(self, painter):
        """绘制角度信息"""
        angle_diff = abs(self.angle2 - self.angle1)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff
        
        # 背景框
        info_rect = QPoint(self.center.x() - 60, self.center.y() - 25)
        painter.fillRect(info_rect.x(), info_rect.y(), 120, 50, QColor(0, 0, 0, 200))
        
        # 角度文字
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 18, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(info_rect.x() + 10, info_rect.y() + 30, f"{angle_diff:.1f}°")
        
        # 锁定状态
        if self.lock_enabled:
            font.setPointSize(10)
            painter.setFont(font)
            painter.setPen(QColor(0, 200, 100))
            painter.drawText(info_rect.x() + 10, info_rect.y() + 45, f"锁定: {self.angle_lock}°")
    
    def _draw_control_points(self, painter):
        """绘制控制点"""
        # 中心点（绿色）
        painter.setBrush(QColor(0, 200, 100))
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawEllipse(self.center, 8, 8)
        
        # 起始点（红色）
        painter.setBrush(QColor(255, 80, 80))
        painter.drawEllipse(self.point1, 8, 8)
        
        # 终止点（蓝色）
        painter.setBrush(QColor(80, 150, 255))
        painter.drawEllipse(self.point2, 8, 8)
    
    def _draw_help(self, painter):
        """绘制帮助信息"""
        painter.setPen(QColor(200, 200, 200))
        font = QFont("Microsoft YaHei", 10)
        painter.setFont(font)
        
        help_text = [
            "拖动绿点移动中心",
            "拖动红/蓝点调整角度",
            "L键切换角度锁定",
            "S键保存测量",
            "E键导出CSV",
            "右键菜单 | ESC退出"
        ]
        
        y = 20
        for text in help_text:
            painter.drawText(10, y, text)
            y += 18
    
    def mousePressEvent(self, event):
        """鼠标按下"""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            
            # 检查是否点击了控制点
            if self._distance(pos, self.center) < 15:
                self.dragging = True
                self.dragging_point = 'center'
                self.drag_start = pos
            elif self._distance(pos, self.point1) < 15:
                self.dragging = True
                self.dragging_point = 'point1'
            elif self._distance(pos, self.point2) < 15:
                self.dragging = True
                self.dragging_point = 'point2'
        
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.pos())
    
    def mouseMoveEvent(self, event):
        """鼠标移动"""
        if self.dragging:
            pos = event.pos()
            
            if self.dragging_point == 'center':
                delta = pos - self.drag_start
                self.center += delta
                self.point1 += delta
                self.point2 += delta
                self.drag_start = pos
            elif self.dragging_point == 'point1':
                if self.lock_enabled:
                    pos = self._snap_to_angle(pos, self.angle_lock)
                self.point1 = pos
            elif self.dragging_point == 'point2':
                if self.lock_enabled:
                    pos = self._snap_to_angle(pos, self.angle_lock)
                self.point2 = pos
            
            self._update_angles()
            self.update()
    
    def _snap_to_angle(self, pos: QPoint, interval: int) -> QPoint:
        """将点吸附到最近的角度间隔"""
        dx = pos.x() - self.center.x()
        dy = self.center.y() - pos.y()
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360
        
        # 吸附到最近的间隔
        snapped = round(angle / interval) * interval
        rad = math.radians(snapped)
        dist = math.sqrt(dx*dx + dy*dy)
        
        return QPoint(
            int(self.center.x() + dist * math.cos(rad)),
            int(self.center.y() - dist * math.sin(rad))
        )
    
    def mouseReleaseEvent(self, event):
        """鼠标释放"""
        self.dragging = False
        self.dragging_point = None
    
    def _distance(self, p1: QPoint, p2: QPoint) -> float:
        """计算两点距离"""
        return math.sqrt((p1.x() - p2.x())**2 + (p1.y() - p2.y())**2)
    
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
        
        save_action = QAction(tr("保存当前测量"), menu)
        save_action.triggered.connect(self._save_measurement)
        menu.addAction(save_action)
        
        export_action = QAction(tr("导出测量记录 (CSV)"), menu)
        export_action.triggered.connect(self._export_csv)
        menu.addAction(export_action)
        
        menu.addSeparator()
        
        lock_action = QAction(f"{'禁用' if self.lock_enabled else '启用'}角度锁定 ({self.angle_lock}°)", menu)
        lock_action.triggered.connect(self._toggle_lock)
        menu.addAction(lock_action)
        
        menu.addSeparator()
        
        close_action = QAction("关闭", menu)
        close_action.triggered.connect(self.close)
        menu.addAction(close_action)
        
        menu.exec(self.mapToGlobal(pos))
    
    def _toggle_lock(self):
        """切换角度锁定"""
        self.lock_enabled = not self.lock_enabled
        self.update()
    
    def _save_measurement(self):
        """保存当前测量"""
        angle_diff = abs(self.angle2 - self.angle1)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff
        
        self.measurements.append({
            'timestamp': datetime.now().isoformat(),
            'angle': round(angle_diff, 2),
            'angle1': round(self.angle1, 2),
            'angle2': round(self.angle2, 2),
            'center': (self.center.x(), self.center.y()),
        })
        self.update()
    
    def _export_csv(self):
        """导出CSV"""
        if not self.measurements:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出测量记录",
            f"protractor_measurements_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV文件 (*.csv)"
        )
        
        if file_path:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    tr('时间'),
                    tr('测量角度'),
                    tr('起始角度'),
                    tr('终止角度'),
                    tr('中心点X'),
                    tr('中心点Y'),
                ])
                for m in self.measurements:
                    writer.writerow([
                        m['timestamp'],
                        m['angle'],
                        m['angle1'],
                        m['angle2'],
                        m['center'][0],
                        m['center'][1]
                    ])
    
    def keyPressEvent(self, event):
        """键盘事件"""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_L:
            self._toggle_lock()
        elif event.key() == Qt.Key.Key_S:
            self._save_measurement()
        elif event.key() == Qt.Key.Key_E:
            self._export_csv()
    
    def mouseDoubleClickEvent(self, event):
        """双击关闭"""
        self.close()
