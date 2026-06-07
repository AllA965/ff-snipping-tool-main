"""
像素尺工具 - 增强版
支持：水平/垂直同时显示、多单位切换、DPI设置、颜色配色、透明度调节
"""
from PySide6.QtWidgets import (
    QWidget, QApplication, QMenu, QWidgetAction,
    QLabel, QSlider, QVBoxLayout, QHBoxLayout, QFrame
)
from PySide6.QtCore import Qt, QPoint, QRect, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QCursor, QAction
from ui.icons import set_window_icon
from core.i18n import tr


class RulerColorScheme:
    """标尺配色方案"""
    
    SCHEMES = {
        'default': {
            'name': '默认（黄色）',
            'bg': QColor(255, 255, 200, 230),
            'border': QColor(200, 180, 100),
            'tick': QColor(100, 80, 50),
            'text': QColor(80, 60, 40),
        },
        'blue': {
            'name': '蓝色',
            'bg': QColor(200, 220, 255, 230),
            'border': QColor(100, 140, 200),
            'tick': QColor(50, 80, 150),
            'text': QColor(30, 60, 120),
        },
        'white': {
            'name': '白色',
            'bg': QColor(255, 255, 255, 240),
            'border': QColor(180, 180, 180),
            'tick': QColor(80, 80, 80),
            'text': QColor(60, 60, 60),
        },
        'black': {
            'name': '黑色',
            'bg': QColor(40, 40, 40, 240),
            'border': QColor(80, 80, 80),
            'tick': QColor(200, 200, 200),
            'text': QColor(220, 220, 220),
        },
    }
    
    @classmethod
    def get_scheme(cls, name: str) -> dict:
        return cls.SCHEMES.get(name, cls.SCHEMES['default'])
    
    @classmethod
    def get_all_schemes(cls) -> dict:
        return cls.SCHEMES


class RulerUnit:
    """标尺单位"""
    
    PIXEL = 'pixel'
    INCH = 'inch'
    CM = 'cm'
    
    UNITS = {
        PIXEL: {'name': '像素 (px)', 'suffix': 'px'},
        INCH: {'name': '英寸 (in)', 'suffix': 'in'},
        CM: {'name': '厘米 (cm)', 'suffix': 'cm'},
    }
    
    # DPI 选项
    DPI_OPTIONS = [72, 96, 120, 144, 192, 300]
    
    @classmethod
    def convert(cls, pixels: float, unit: str, dpi: int) -> float:
        """将像素转换为指定单位"""
        if unit == cls.PIXEL:
            return pixels
        elif unit == cls.INCH:
            return pixels / dpi
        elif unit == cls.CM:
            return pixels / dpi * 2.54
        return pixels
    
    @classmethod
    def get_tick_interval(cls, unit: str, dpi: int) -> tuple:
        """获取刻度间隔 (小刻度, 中刻度, 大刻度) 单位为像素"""
        if unit == cls.PIXEL:
            return (10, 50, 100)
        elif unit == cls.INCH:
            # 1英寸 = dpi像素
            inch_px = dpi
            return (inch_px // 16, inch_px // 4, inch_px)
        elif unit == cls.CM:
            # 1厘米 = dpi/2.54 像素
            cm_px = dpi / 2.54
            return (int(cm_px / 10), int(cm_px / 2), int(cm_px))
        return (10, 50, 100)


class HorizontalRuler(QWidget):
    """水平标尺"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.unit = RulerUnit.PIXEL
        self.dpi = 96
        self.color_scheme = 'default'
        self.setFixedHeight(30)
        self.setMouseTracking(True)
        self.cursor_x = -1
    
    def set_unit(self, unit: str):
        self.unit = unit
        self.update()
    
    def set_dpi(self, dpi: int):
        self.dpi = dpi
        self.update()
    
    def set_color_scheme(self, scheme: str):
        self.color_scheme = scheme
        self.update()
    
    def set_cursor_pos(self, x: int):
        self.cursor_x = x
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        scheme = RulerColorScheme.get_scheme(self.color_scheme)
        
        # 背景
        painter.fillRect(self.rect(), scheme['bg'])
        
        # 边框
        painter.setPen(QPen(scheme['border'], 1))
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)
        
        # 刻度
        painter.setPen(QPen(scheme['tick'], 1))
        font = QFont("Consolas", 8)
        painter.setFont(font)
        
        small, medium, large = RulerUnit.get_tick_interval(self.unit, self.dpi)
        unit_info = RulerUnit.UNITS[self.unit]
        
        # 绘制刻度
        i = 0
        while i < self.width():
            # 计算显示值
            display_val = RulerUnit.convert(i, self.unit, self.dpi)
            
            if large > 0 and i % large == 0:
                painter.drawLine(i, self.height() - 20, i, self.height())
                # 显示数值
                if self.unit == RulerUnit.PIXEL:
                    text = str(i)
                else:
                    text = f"{display_val:.1f}"
                painter.setPen(scheme['text'])
                painter.drawText(i + 2, 12, text)
                painter.setPen(QPen(scheme['tick'], 1))
            elif medium > 0 and i % medium == 0:
                painter.drawLine(i, self.height() - 14, i, self.height())
            elif small > 0 and i % small == 0:
                painter.drawLine(i, self.height() - 8, i, self.height())
            
            i += max(1, small)
        
        # 绘制光标位置指示线
        if 0 <= self.cursor_x < self.width():
            painter.setPen(QPen(QColor(255, 0, 0), 1))
            painter.drawLine(self.cursor_x, 0, self.cursor_x, self.height())


class VerticalRuler(QWidget):
    """垂直标尺"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.unit = RulerUnit.PIXEL
        self.dpi = 96
        self.color_scheme = 'default'
        self.setFixedWidth(30)
        self.setMouseTracking(True)
        self.cursor_y = -1
    
    def set_unit(self, unit: str):
        self.unit = unit
        self.update()
    
    def set_dpi(self, dpi: int):
        self.dpi = dpi
        self.update()
    
    def set_color_scheme(self, scheme: str):
        self.color_scheme = scheme
        self.update()
    
    def set_cursor_pos(self, y: int):
        self.cursor_y = y
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        scheme = RulerColorScheme.get_scheme(self.color_scheme)
        
        # 背景
        painter.fillRect(self.rect(), scheme['bg'])
        
        # 边框
        painter.setPen(QPen(scheme['border'], 1))
        painter.drawLine(self.width() - 1, 0, self.width() - 1, self.height())
        
        # 刻度
        painter.setPen(QPen(scheme['tick'], 1))
        font = QFont("Consolas", 8)
        painter.setFont(font)
        
        small, medium, large = RulerUnit.get_tick_interval(self.unit, self.dpi)
        
        # 绘制刻度
        i = 0
        while i < self.height():
            display_val = RulerUnit.convert(i, self.unit, self.dpi)
            
            if large > 0 and i % large == 0:
                painter.drawLine(self.width() - 20, i, self.width(), i)
                # 显示数值（旋转）
                painter.save()
                painter.translate(10, i + 2)
                painter.rotate(90)
                if self.unit == RulerUnit.PIXEL:
                    text = str(i)
                else:
                    text = f"{display_val:.1f}"
                painter.setPen(scheme['text'])
                painter.drawText(0, 0, text)
                painter.restore()
                painter.setPen(QPen(scheme['tick'], 1))
            elif medium > 0 and i % medium == 0:
                painter.drawLine(self.width() - 14, i, self.width(), i)
            elif small > 0 and i % small == 0:
                painter.drawLine(self.width() - 8, i, self.width(), i)
            
            i += max(1, small)
        
        # 绘制光标位置指示线
        if 0 <= self.cursor_y < self.height():
            painter.setPen(QPen(QColor(255, 0, 0), 1))
            painter.drawLine(0, self.cursor_y, self.width(), self.cursor_y)


class RulerWindow(QWidget):
    """标尺窗口 - 增强版"""
    
    def __init__(self):
        super().__init__()
        
        # 设置
        self.unit = RulerUnit.PIXEL
        self.dpi = 96
        self.color_scheme = 'default'
        self.opacity = 0.9
        
        # 拖拽状态
        self.dragging = False
        self.drag_start = QPoint()
        self.resizing = False
        self.resize_edge = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("像素尺")
        set_window_icon(self)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        
        # 默认大小
        self.resize(500, 400)
        
        # 移动到屏幕中央
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, 
                  (screen.height() - self.height()) // 2)
        
        self.setWindowOpacity(self.opacity)
    
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        scheme = RulerColorScheme.get_scheme(self.color_scheme)
        ruler_size = 30
        
        # 绘制水平标尺（顶部）
        self._draw_horizontal_ruler(painter, QRect(ruler_size, 0, self.width() - ruler_size, ruler_size), scheme)
        
        # 绘制垂直标尺（左侧）
        self._draw_vertical_ruler(painter, QRect(0, ruler_size, ruler_size, self.height() - ruler_size), scheme)
        
        # 绘制左上角方块
        painter.fillRect(QRect(0, 0, ruler_size, ruler_size), scheme['bg'])
        painter.setPen(QPen(scheme['border'], 1))
        painter.drawRect(QRect(0, 0, ruler_size - 1, ruler_size - 1))
        
        # 绘制中央测量区域
        center_rect = QRect(ruler_size, ruler_size, self.width() - ruler_size, self.height() - ruler_size)
        painter.fillRect(center_rect, QColor(255, 255, 255, 30))
        painter.setPen(QPen(scheme['border'], 1, Qt.PenStyle.DashLine))
        painter.drawRect(center_rect.adjusted(0, 0, -1, -1))
        
        # 绘制尺寸信息
        painter.setPen(scheme['text'])
        font = QFont("Consolas", 10)
        painter.setFont(font)
        
        w_px = self.width() - ruler_size
        h_px = self.height() - ruler_size
        
        if self.unit == RulerUnit.PIXEL:
            size_text = f"{w_px} × {h_px} px"
        else:
            w_val = RulerUnit.convert(w_px, self.unit, self.dpi)
            h_val = RulerUnit.convert(h_px, self.unit, self.dpi)
            suffix = RulerUnit.UNITS[self.unit]['suffix']
            size_text = f"{w_val:.2f} × {h_val:.2f} {suffix}"
        
        # 在中央显示尺寸
        text_rect = painter.fontMetrics().boundingRect(size_text)
        text_x = ruler_size + (w_px - text_rect.width()) // 2
        text_y = ruler_size + (h_px + text_rect.height()) // 2
        
        # 文字背景
        bg_rect = QRect(text_x - 5, text_y - text_rect.height(), text_rect.width() + 10, text_rect.height() + 6)
        painter.fillRect(bg_rect, QColor(255, 255, 255, 200))
        painter.drawText(text_x, text_y, size_text)
        
        # 绘制DPI和单位信息
        info_text = f"DPI: {self.dpi} | 单位: {RulerUnit.UNITS[self.unit]['name']} | 透明度: {int(self.opacity * 100)}%"
        painter.setPen(scheme['text'])
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(ruler_size + 5, self.height() - 8, info_text)
        
        # 绘制操作提示
        hint_text = "右键菜单 | 滚轮调透明度 | 双击关闭"
        hint_rect = painter.fontMetrics().boundingRect(hint_text)
        painter.drawText(self.width() - hint_rect.width() - 10, self.height() - 8, hint_text)
    
    def _draw_horizontal_ruler(self, painter, rect: QRect, scheme: dict):
        """绘制水平标尺"""
        painter.save()
        painter.setClipRect(rect)
        
        # 背景
        painter.fillRect(rect, scheme['bg'])
        
        # 边框
        painter.setPen(QPen(scheme['border'], 1))
        painter.drawRect(rect.adjusted(0, 0, -1, -1))
        
        # 刻度
        painter.setPen(QPen(scheme['tick'], 1))
        font = QFont("Consolas", 8)
        painter.setFont(font)
        
        small, medium, large = RulerUnit.get_tick_interval(self.unit, self.dpi)
        
        i = 0
        while i < rect.width():
            x = rect.x() + i
            display_val = RulerUnit.convert(i, self.unit, self.dpi)
            
            if large > 0 and i % large == 0:
                painter.drawLine(x, rect.bottom() - 18, x, rect.bottom())
                if self.unit == RulerUnit.PIXEL:
                    text = str(i)
                else:
                    text = f"{display_val:.1f}"
                painter.setPen(scheme['text'])
                painter.drawText(x + 2, rect.top() + 12, text)
                painter.setPen(QPen(scheme['tick'], 1))
            elif medium > 0 and i % medium == 0:
                painter.drawLine(x, rect.bottom() - 12, x, rect.bottom())
            elif small > 0 and i % small == 0:
                painter.drawLine(x, rect.bottom() - 6, x, rect.bottom())
            
            i += max(1, small)
        
        painter.restore()
    
    def _draw_vertical_ruler(self, painter, rect: QRect, scheme: dict):
        """绘制垂直标尺"""
        painter.save()
        painter.setClipRect(rect)
        
        # 背景
        painter.fillRect(rect, scheme['bg'])
        
        # 边框
        painter.setPen(QPen(scheme['border'], 1))
        painter.drawRect(rect.adjusted(0, 0, -1, -1))
        
        # 刻度
        painter.setPen(QPen(scheme['tick'], 1))
        font = QFont("Consolas", 8)
        painter.setFont(font)
        
        small, medium, large = RulerUnit.get_tick_interval(self.unit, self.dpi)
        
        i = 0
        while i < rect.height():
            y = rect.y() + i
            display_val = RulerUnit.convert(i, self.unit, self.dpi)
            
            if large > 0 and i % large == 0:
                painter.drawLine(rect.right() - 18, y, rect.right(), y)
                # 旋转绘制文字
                painter.save()
                painter.translate(rect.left() + 10, y + 2)
                painter.rotate(90)
                if self.unit == RulerUnit.PIXEL:
                    text = str(i)
                else:
                    text = f"{display_val:.1f}"
                painter.setPen(scheme['text'])
                painter.drawText(0, 0, text)
                painter.restore()
                painter.setPen(QPen(scheme['tick'], 1))
            elif medium > 0 and i % medium == 0:
                painter.drawLine(rect.right() - 12, y, rect.right(), y)
            elif small > 0 and i % small == 0:
                painter.drawLine(rect.right() - 6, y, rect.right(), y)
            
            i += max(1, small)
        
        painter.restore()
    
    def mousePressEvent(self, event):
        """鼠标按下"""
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._get_resize_edge(event.pos())
            if edge:
                self.resizing = True
                self.resize_edge = edge
            else:
                self.dragging = True
                self.drag_start = event.globalPosition().toPoint() - self.pos()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
    
    def mouseMoveEvent(self, event):
        """鼠标移动"""
        if self.dragging:
            self.move(event.globalPosition().toPoint() - self.drag_start)
        elif self.resizing:
            self._do_resize(event.globalPosition().toPoint())
        else:
            # 更新鼠标样式
            edge = self._get_resize_edge(event.pos())
            if edge in ['right', 'left']:
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif edge in ['top', 'bottom']:
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            elif edge in ['top_right', 'bottom_left']:
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif edge in ['top_left', 'bottom_right']:
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放"""
        self.dragging = False
        self.resizing = False
        self.resize_edge = None
    
    def mouseDoubleClickEvent(self, event):
        """双击关闭"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.close()
    
    def wheelEvent(self, event):
        """滚轮调节透明度"""
        delta = event.angleDelta().y()
        if delta > 0:
            self.opacity = min(1.0, self.opacity + 0.05)
        else:
            self.opacity = max(0.1, self.opacity - 0.05)
        
        self.setWindowOpacity(self.opacity)
        self.update()
    
    def _get_resize_edge(self, pos) -> str:
        """获取调整边缘"""
        margin = 10
        
        at_left = pos.x() < margin
        at_right = pos.x() > self.width() - margin
        at_top = pos.y() < margin
        at_bottom = pos.y() > self.height() - margin
        
        if at_top and at_left:
            return 'top_left'
        elif at_top and at_right:
            return 'top_right'
        elif at_bottom and at_left:
            return 'bottom_left'
        elif at_bottom and at_right:
            return 'bottom_right'
        elif at_left:
            return 'left'
        elif at_right:
            return 'right'
        elif at_top:
            return 'top'
        elif at_bottom:
            return 'bottom'
        
        return None
    
    def _do_resize(self, global_pos):
        """执行调整大小"""
        min_size = 100
        
        if 'right' in self.resize_edge:
            new_width = global_pos.x() - self.x()
            if new_width >= min_size:
                self.resize(new_width, self.height())
        
        if 'left' in self.resize_edge:
            new_width = self.x() + self.width() - global_pos.x()
            if new_width >= min_size:
                self.setGeometry(global_pos.x(), self.y(), new_width, self.height())
        
        if 'bottom' in self.resize_edge:
            new_height = global_pos.y() - self.y()
            if new_height >= min_size:
                self.resize(self.width(), new_height)
        
        if 'top' in self.resize_edge:
            new_height = self.y() + self.height() - global_pos.y()
            if new_height >= min_size:
                self.setGeometry(self.x(), global_pos.y(), self.width(), new_height)
        
        self.update()
    
    def _show_context_menu(self, pos):
        """显示右键菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: white;
                border: 1px solid #ccc;
                padding: 5px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background: #e5f3ff;
            }
            QMenu::separator {
                height: 1px;
                background: #ddd;
                margin: 5px 10px;
            }
        """)
        
        # 单位子菜单
        unit_menu = menu.addMenu("📏 单位")
        unit_group = []
        for unit_key, unit_info in RulerUnit.UNITS.items():
            action = QAction(unit_info['name'], self)
            action.setCheckable(True)
            action.setChecked(self.unit == unit_key)
            action.triggered.connect(lambda checked, u=unit_key: self._set_unit(u))
            unit_menu.addAction(action)
            unit_group.append(action)
        
        # DPI子菜单
        dpi_menu = menu.addMenu("🖥 DPI")
        for dpi_val in RulerUnit.DPI_OPTIONS:
            action = QAction(f"{dpi_val} DPI", self)
            action.setCheckable(True)
            action.setChecked(self.dpi == dpi_val)
            action.triggered.connect(lambda checked, d=dpi_val: self._set_dpi(d))
            dpi_menu.addAction(action)
        
        # 配色子菜单
        color_menu = menu.addMenu("🎨 配色")
        for scheme_key, scheme_info in RulerColorScheme.get_all_schemes().items():
            action = QAction(scheme_info['name'], self)
            action.setCheckable(True)
            action.setChecked(self.color_scheme == scheme_key)
            action.triggered.connect(lambda checked, s=scheme_key: self._set_color_scheme(s))
            color_menu.addAction(action)
        
        menu.addSeparator()
        
        # 透明度滑块
        opacity_action = QWidgetAction(self)
        opacity_widget = QWidget()
        opacity_layout = QHBoxLayout(opacity_widget)
        opacity_layout.setContentsMargins(10, 5, 10, 5)
        
        opacity_label = QLabel(tr("透明度:"))
        opacity_layout.addWidget(opacity_label)
        
        opacity_slider = QSlider(Qt.Orientation.Horizontal)
        opacity_slider.setRange(10, 100)
        opacity_slider.setValue(int(self.opacity * 100))
        opacity_slider.setFixedWidth(100)
        opacity_slider.valueChanged.connect(lambda v: self._set_opacity(v / 100))
        opacity_layout.addWidget(opacity_slider)
        
        opacity_value = QLabel(f"{int(self.opacity * 100)}%")
        opacity_slider.valueChanged.connect(lambda v: opacity_value.setText(f"{v}%"))
        opacity_layout.addWidget(opacity_value)
        
        opacity_action.setDefaultWidget(opacity_widget)
        menu.addAction(opacity_action)
        
        menu.addSeparator()
        
        # 重置大小
        reset_action = QAction("↺ 重置大小", self)
        reset_action.triggered.connect(self._reset_size)
        menu.addAction(reset_action)
        
        # 关闭
        close_action = QAction(tr("✕ 关闭"), self)
        close_action.triggered.connect(self.close)
        menu.addAction(close_action)
        
        menu.exec(pos)
    
    def _set_unit(self, unit: str):
        """设置单位"""
        self.unit = unit
        self.update()
    
    def _set_dpi(self, dpi: int):
        """设置DPI"""
        self.dpi = dpi
        self.update()
    
    def _set_color_scheme(self, scheme: str):
        """设置配色"""
        self.color_scheme = scheme
        self.update()
    
    def _set_opacity(self, opacity: float):
        """设置透明度"""
        self.opacity = opacity
        self.setWindowOpacity(opacity)
        self.update()
    
    def _reset_size(self):
        """重置大小"""
        self.resize(500, 400)
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2,
                  (screen.height() - self.height()) // 2)
    
    def keyPressEvent(self, event):
        """键盘事件"""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_1:
            self._set_unit(RulerUnit.PIXEL)
        elif event.key() == Qt.Key.Key_2:
            self._set_unit(RulerUnit.INCH)
        elif event.key() == Qt.Key.Key_3:
            self._set_unit(RulerUnit.CM)
        elif event.key() == Qt.Key.Key_Plus or event.key() == Qt.Key.Key_Equal:
            self._set_opacity(min(1.0, self.opacity + 0.1))
        elif event.key() == Qt.Key.Key_Minus:
            self._set_opacity(max(0.1, self.opacity - 0.1))
