"""
调色板工具 - 整合取色器功能
参考 PicPick 调色板设计
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QApplication, QGridLayout,
    QSpinBox, QLineEdit, QComboBox, QDialog
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QCursor
from ui.icons import set_window_icon
from core.i18n import tr


# 主题颜色
THEME_COLORS = [
    "#000000", "#FFFFFF", "#800000", "#FF0000", "#FFA500", "#FFFF00", "#008000", "#00FF00",
    "#008080", "#00FFFF", "#000080", "#0000FF", "#800080", "#FF00FF",
]

# 标准颜色 (6行10列)
STANDARD_COLORS = [
    "#FF0000", "#FF4500", "#FFA500", "#FFD700", "#FFFF00", "#9ACD32", "#32CD32", "#00FA9A", "#00CED1", "#1E90FF",
    "#FF6347", "#FF7F50", "#FFA07A", "#FFE4B5", "#FFFACD", "#98FB98", "#90EE90", "#7FFFD4", "#AFEEEE", "#87CEEB",
    "#DC143C", "#FF8C00", "#DAA520", "#F0E68C", "#ADFF2F", "#3CB371", "#2E8B57", "#20B2AA", "#5F9EA0", "#4682B4",
    "#B22222", "#D2691E", "#CD853F", "#BDB76B", "#6B8E23", "#228B22", "#006400", "#008B8B", "#4169E1", "#0000CD",
    "#8B0000", "#A0522D", "#8B4513", "#808000", "#556B2F", "#2F4F4F", "#191970", "#483D8B", "#8B008B", "#4B0082",
    "#C71585", "#DB7093", "#FF69B4", "#FFB6C1", "#DDA0DD", "#EE82EE", "#DA70D6", "#BA55D3", "#9932CC", "#9400D3",
]


class ColorSquare(QWidget):
    """颜色选择方块"""
    color_changed = Signal(QColor)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)
        self.hue = 0
        self.saturation = 255
        self.value = 255

    def paintEvent(self, event):
        painter = QPainter(self)
        for x in range(self.width()):
            for y in range(self.height()):
                s = int(x * 255 / self.width())
                v = int((self.height() - y) * 255 / self.height())
                color = QColor.fromHsv(self.hue, s, v)
                painter.setPen(color)
                painter.drawPoint(x, y)
        
        # 绘制选择标记
        x = int(self.saturation * self.width() / 255)
        y = int((255 - self.value) * self.height() / 255)
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        painter.drawEllipse(x - 6, y - 6, 12, 12)
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawEllipse(x - 5, y - 5, 10, 10)
    
    def mousePressEvent(self, event):
        self._update_from_pos(event.pos())
    
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._update_from_pos(event.pos())
    
    def _update_from_pos(self, pos):
        x = max(0, min(pos.x(), self.width() - 1))
        y = max(0, min(pos.y(), self.height() - 1))
        self.saturation = int(x * 255 / self.width())
        self.value = int((self.height() - y) * 255 / self.height())
        self.update()
        self.color_changed.emit(self.get_color())
    
    def set_hue(self, hue: int):
        self.hue = hue
        self.update()
        self.color_changed.emit(self.get_color())
    
    def get_color(self) -> QColor:
        return QColor.fromHsv(self.hue, self.saturation, self.value)
    
    def set_color(self, color: QColor):
        h, s, v, _ = color.getHsv()
        self.hue = h if h >= 0 else 0
        self.saturation = s
        self.value = v
        self.update()


class HueBar(QWidget):
    """色相条"""
    hue_changed = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 200)
        self.hue = 0

    def paintEvent(self, event):
        painter = QPainter(self)
        for y in range(self.height()):
            hue = int(y * 359 / self.height())
            color = QColor.fromHsv(hue, 255, 255)
            painter.setPen(color)
            painter.drawLine(0, y, self.width(), y)
        
        y = int(self.hue * self.height() / 359)
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawRect(0, y - 2, self.width() - 1, 4)
    
    def mousePressEvent(self, event):
        self._update_from_pos(event.pos())
    
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._update_from_pos(event.pos())
    
    def _update_from_pos(self, pos):
        y = max(0, min(pos.y(), self.height() - 1))
        self.hue = int(y * 359 / self.height())
        self.update()
        self.hue_changed.emit(self.hue)
    
    def set_hue(self, hue: int):
        self.hue = hue
        self.update()


class ToastWidget(QWidget):
    """提示框"""
    def __init__(self, message: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QVBoxLayout(self)
        label = QLabel(message)
        label.setStyleSheet("QLabel { background: rgba(0,120,215,0.9); color: white; padding: 12px 20px; border-radius: 6px; }")
        layout.addWidget(label)
        self.adjustSize()
        QTimer.singleShot(2000, self.close)
    
    def show_at_cursor(self):
        pos = QCursor.pos()
        self.move(pos.x() + 20, pos.y() + 20)
        self.show()


class PaletteWindow(QDialog):
    """调色板窗口 - 现代现代化设计风格"""
    
    color_selected = Signal(QColor)
    
    def __init__(self, config=None, is_dialog=False, parent=None):
        super().__init__(parent)
        self.config = config
        self.is_dialog = is_dialog
        self.current_color = QColor(255, 255, 255)
        self.custom_colors = [QColor(255, 255, 255) for _ in range(10)]
        self.color_history = []
        self.overlay = None
        self._updating = False
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("调色板")
        set_window_icon(self)
        self.setFixedSize(620, 520 if self.is_dialog else 480)
        
        flags = Qt.WindowType.WindowStaysOnTopHint
        if self.is_dialog:
            flags |= Qt.WindowType.Dialog
        self.setWindowFlags(flags)
        self.setStyleSheet("""
            QWidget { 
                background: white; 
                font-family: "Microsoft YaHei", "Segoe UI";
            }
            QLabel { 
                color: #555; 
                font-size: 12px; 
            }
            QLabel[title="true"] { 
                font-weight: bold; 
                font-size: 13px; 
                color: #1a1a1a; 
                margin-bottom: 5px;
            }
            QSpinBox, QLineEdit { 
                background: #f8f9fa; 
                border: 1px solid #e9ecef; 
                border-radius: 6px; 
                padding: 6px 10px; 
                color: #333;
                font-size: 12px;
            }
            QSpinBox:hover, QLineEdit:hover { 
                border-color: #dee2e6; 
            }
            QSpinBox:focus, QLineEdit:focus { 
                border-color: #0078D7; 
                background: white;
            }
            QComboBox { 
                background: #f8f9fa; 
                border: 1px solid #e9ecef; 
                border-radius: 6px; 
                padding: 6px 12px; 
                font-size: 12px;
            }
            QComboBox:hover {
                border-color: #dee2e6;
            }
            QPushButton#mainActionBtn { 
                background: #0078D7; 
                color: white; 
                border: none; 
                border-radius: 8px; 
                padding: 10px 20px; 
                font-size: 13px; 
                font-weight: bold;
            }
            QPushButton#mainActionBtn:hover { 
                background: #005A9E; 
            }
            QPushButton#mainActionBtn:pressed {
                background: #004578;
            }
            QPushButton#secondaryBtn { 
                background: #f1f3f5; 
                color: #495057; 
                border: none; 
                border-radius: 8px; 
                padding: 8px 16px; 
                font-size: 12px; 
            }
            QPushButton#secondaryBtn:hover { 
                background: #e9ecef; 
                color: #212529;
            }
            QFrame#colorCard {
                background: white;
                border: 1px solid #eee;
                border-radius: 10px;
            }
        """)
        
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(25)
        main_layout.setContentsMargins(25, 25, 25, 25)
        
        # 左侧：预设颜色卡片
        left_container = QFrame()
        left_container.setObjectName("colorCard")
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(15, 15, 15, 15)
        left_layout.setSpacing(12)
        
        # 主题颜色
        theme_label = QLabel("主题颜色")
        theme_label.setProperty("title", True)
        left_layout.addWidget(theme_label)
        
        theme_grid = QGridLayout()
        theme_grid.setSpacing(6)
        for i, color in enumerate(THEME_COLORS):
            btn = self._create_color_btn(color, size=28)
            theme_grid.addWidget(btn, i // 7, i % 7)
        left_layout.addLayout(theme_grid)
        
        # 标准颜色
        std_label = QLabel("标准颜色")
        std_label.setProperty("title", True)
        std_label.setStyleSheet("margin-top: 10px;")
        left_layout.addWidget(std_label)
        
        std_grid = QGridLayout()
        std_grid.setSpacing(4)
        for i, color in enumerate(STANDARD_COLORS):
            btn = self._create_color_btn(color, size=22)
            std_grid.addWidget(btn, i // 10, i % 10)
        left_layout.addLayout(std_grid)
        
        # 自定义颜色
        custom_label = QLabel("自定义颜色")
        custom_label.setProperty("title", True)
        custom_label.setStyleSheet("margin-top: 10px;")
        left_layout.addWidget(custom_label)
        
        self.custom_grid = QGridLayout()
        self.custom_grid.setSpacing(6)
        self.custom_btns = []
        for i in range(10):
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: white; 
                    border: 1px solid #eee; 
                    border-radius: 4px;
                }
                QPushButton:hover {
                    border-color: #0078D7;
                }
            """)
            btn.clicked.connect(lambda checked, idx=i: self._on_custom_clicked(idx))
            self.custom_grid.addWidget(btn, 0, i)
            self.custom_btns.append(btn)
        left_layout.addLayout(self.custom_grid)
        
        left_layout.addStretch()
        
        # 取色器大按钮
        picker_btn = QPushButton(tr("🔍 取色器 (P)"))
        picker_btn.setObjectName("mainActionBtn")
        picker_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        picker_btn.clicked.connect(self._start_picking)
        left_layout.addWidget(picker_btn)
        
        main_layout.addWidget(left_container)

        # 右侧：颜色调节区域
        right_layout = QVBoxLayout()
        right_layout.setSpacing(15)
        
        # 预览与大选择器
        top_preview_layout = QHBoxLayout()
        top_preview_layout.setSpacing(15)
        
        # 颜色方块与色相条
        picker_box = QHBoxLayout()
        picker_box.setSpacing(12)
        
        self.color_square = ColorSquare()
        self.color_square.setFixedSize(200, 200)
        self.color_square.color_changed.connect(self._on_color_changed)
        picker_box.addWidget(self.color_square)
        
        self.hue_bar = HueBar()
        self.hue_bar.setFixedSize(22, 200)
        self.hue_bar.hue_changed.connect(self._on_hue_changed)
        picker_box.addWidget(self.hue_bar)
        
        top_preview_layout.addLayout(picker_box)
        
        # 大预览框
        self.color_preview = QFrame()
        self.color_preview.setFixedSize(60, 60)
        self.color_preview.setStyleSheet("""
            background: white; 
            border: 1px solid #eee; 
            border-radius: 12px;
        """)
        # 添加阴影效果
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 4)
        self.color_preview.setGraphicsEffect(shadow)
        
        top_preview_layout.addWidget(self.color_preview, alignment=Qt.AlignmentFlag.AlignTop)
        right_layout.addLayout(top_preview_layout)
        
        # 参数输入卡片
        params_container = QFrame()
        params_container.setStyleSheet("background: #fcfcfc; border-radius: 10px; border: 1px solid #f0f0f0;")
        params_layout = QGridLayout(params_container)
        params_layout.setSpacing(10)
        params_layout.setContentsMargins(12, 12, 12, 12)
        
        # HSL
        params_layout.addWidget(QLabel("H:"), 0, 0)
        self.h_spin = QSpinBox()
        self.h_spin.setRange(0, 359)
        self.h_spin.valueChanged.connect(self._on_hsv_changed)
        params_layout.addWidget(self.h_spin, 0, 1)
        
        params_layout.addWidget(QLabel("S:"), 1, 0)
        self.s_spin = QSpinBox()
        self.s_spin.setRange(0, 255)
        self.s_spin.valueChanged.connect(self._on_hsv_changed)
        params_layout.addWidget(self.s_spin, 1, 1)
        
        params_layout.addWidget(QLabel("L:"), 2, 0)
        self.l_spin = QSpinBox()
        self.l_spin.setRange(0, 255)
        self.l_spin.valueChanged.connect(self._on_hsv_changed)
        params_layout.addWidget(self.l_spin, 2, 1)
        
        # RGB
        params_layout.addWidget(QLabel("R:"), 0, 2)
        self.r_spin = QSpinBox()
        self.r_spin.setRange(0, 255)
        self.r_spin.valueChanged.connect(self._on_rgb_changed)
        params_layout.addWidget(self.r_spin, 0, 3)
        
        params_layout.addWidget(QLabel("G:"), 1, 2)
        self.g_spin = QSpinBox()
        self.g_spin.setRange(0, 255)
        self.g_spin.valueChanged.connect(self._on_rgb_changed)
        params_layout.addWidget(self.g_spin, 1, 3)
        
        params_layout.addWidget(QLabel("B:"), 2, 2)
        self.b_spin = QSpinBox()
        self.b_spin.setRange(0, 255)
        self.b_spin.valueChanged.connect(self._on_rgb_changed)
        params_layout.addWidget(self.b_spin, 2, 3)
        
        right_layout.addWidget(params_container)
        
        # 交互按钮
        btns_layout = QHBoxLayout()
        add_btn = QPushButton("✨ 添加到自定义颜色")
        add_btn.setObjectName("secondaryBtn")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._add_to_custom)
        btns_layout.addWidget(add_btn)
        right_layout.addLayout(btns_layout)
        
        right_layout.addStretch()
        
        # 底部复制区域
        copy_container = QFrame()
        copy_container.setStyleSheet("background: #f8f9fa; border-radius: 8px; border: 1px solid #e9ecef;")
        copy_layout = QHBoxLayout(copy_container)
        copy_layout.setContentsMargins(8, 8, 8, 8)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["HEX", "RGB", "HSL", "HTML", "Delphi", "C++", "Java"])
        self.format_combo.setFixedWidth(80)
        self.format_combo.currentIndexChanged.connect(self._update_format_preview)
        copy_layout.addWidget(self.format_combo)
        
        self.format_edit = QLineEdit()
        self.format_edit.setReadOnly(True)
        self.format_edit.setStyleSheet("background: transparent; border: none; font-family: 'Consolas'; font-weight: bold; color: #1a1a1a;")
        copy_layout.addWidget(self.format_edit)
        
        copy_btn = QPushButton("📋 复制")
        copy_btn.setObjectName("secondaryBtn")
        copy_btn.setFixedWidth(70)
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.clicked.connect(self._copy_color)
        copy_layout.addWidget(copy_btn)
        
        right_layout.addWidget(copy_container)
        
        # 对话框按钮
        if self.is_dialog:
            dialog_btns_layout = QHBoxLayout()
            dialog_btns_layout.setSpacing(10)
            dialog_btns_layout.addStretch()
            
            cancel_btn = QPushButton(tr("取消"))
            cancel_btn.setObjectName("secondaryBtn")
            cancel_btn.setFixedWidth(80)
            cancel_btn.clicked.connect(self.reject)
            dialog_btns_layout.addWidget(cancel_btn)
            
            ok_btn = QPushButton("确定")
            ok_btn.setObjectName("mainActionBtn")
            ok_btn.setFixedWidth(80)
            ok_btn.clicked.connect(self.accept)
            dialog_btns_layout.addWidget(ok_btn)
            
            right_layout.addLayout(dialog_btns_layout)
        
        main_layout.addLayout(right_layout)
        
        self._set_color(self.current_color)

    def _create_color_btn(self, color: str, size: int) -> QPushButton:
        btn = QPushButton()
        btn.setFixedSize(size, size)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {color}; 
                border: 1px solid rgba(0,0,0,0.1); 
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid white;
                margin: -2px;
            }}
        """)
        # 添加简单的悬停放大效果（通过 margin 模拟）
        btn.clicked.connect(lambda: self._set_color(QColor(color)))
        return btn

    def _update_color_preview(self, color: QColor):
        self.color_preview.setStyleSheet(f"""
            background: {color.name()}; 
            border: 1px solid #ddd; 
            border-radius: 12px;
        """)
    
    def _on_color_changed(self, color: QColor):
        if not self._updating:
            self._set_color(color, update_picker=False)
    
    def _on_hue_changed(self, hue: int):
        if not self._updating:
            self.color_square.set_hue(hue)
    
    def _on_hsv_changed(self):
        if not self._updating:
            color = QColor.fromHsv(self.h_spin.value(), self.s_spin.value(), self.l_spin.value())
            self._set_color(color, update_hsv=False)
    
    def _on_rgb_changed(self):
        if not self._updating:
            color = QColor(self.r_spin.value(), self.g_spin.value(), self.b_spin.value())
            self._set_color(color, update_rgb=False)
    
    def _on_custom_clicked(self, index: int):
        self._set_color(self.custom_colors[index])
    
    def _add_to_custom(self):
        # 找到第一个空位或覆盖最后一个
        for i in range(len(self.custom_colors)):
            if self.custom_colors[i] == QColor(255, 255, 255):
                self.custom_colors[i] = QColor(self.current_color)
                self.custom_btns[i].setStyleSheet(f"""
                    QPushButton {{
                        background: {self.current_color.name()}; 
                        border: 1px solid rgba(0,0,0,0.1); 
                        border-radius: 4px;
                    }}
                    QPushButton:hover {{
                        border: 2px solid white;
                        margin: -2px;
                    }}
                """)
                return
        # 全满则覆盖第一个
        self.custom_colors[0] = QColor(self.current_color)
        self.custom_btns[0].setStyleSheet(f"""
            QPushButton {{
                background: {self.current_color.name()}; 
                border: 1px solid rgba(0,0,0,0.1); 
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid white;
                margin: -2px;
            }}
        """)

    def _set_color(self, color: QColor, update_picker=True, update_hsv=True, update_rgb=True):
        self._updating = True
        self.current_color = color
        
        h, s, v, _ = color.getHsv()
        if h < 0:
            h = 0
        
        if update_picker:
            self.color_square.set_color(color)
            self.hue_bar.set_hue(h)
        
        if update_hsv:
            self.h_spin.setValue(h)
            self.s_spin.setValue(s)
            self.l_spin.setValue(v)
        
        if update_rgb:
            self.r_spin.setValue(color.red())
            self.g_spin.setValue(color.green())
            self.b_spin.setValue(color.blue())
        
        self._update_color_preview(color)
        self._update_format_preview()
        self._updating = False
        
        # 发射颜色选择信号
        self.color_selected.emit(color)
    
    def _update_format_preview(self):
        text = self._get_formatted_color()
        self.format_edit.setText(text)
    
    def _get_formatted_color(self) -> str:
        color = self.current_color
        fmt = self.format_combo.currentText()
        
        if fmt == "HEX":
            return color.name().upper()
        elif fmt == "RGB":
            return f"rgb({color.red()}, {color.green()}, {color.blue()})"
        elif fmt == "HSL":
            h, s, l, _ = color.getHsl()
            return f"hsl({h}, {s*100//255}%, {l*100//255}%)"
        elif fmt == "HTML":
            return f'style="color: {color.name()};"'
        elif fmt == "Delphi":
            return f"${0:02X}{color.blue():02X}{color.green():02X}{color.red():02X}"
        elif fmt == "C++":
            return f"0x00{color.red():02X}{color.green():02X}{color.blue():02X}"
        elif fmt == "Java":
            return f"new Color({color.red()}, {color.green()}, {color.blue()})"
        return color.name().upper()

    def _copy_color(self):
        text = self._get_formatted_color()
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        toast = ToastWidget(f"已复制: {text}", self)
        toast.show_at_cursor()
    
    def _start_picking(self):
        """开始取色"""
        # 保存原始模态状态
        self._original_modality = self.windowModality()
        # 临时取消模态，否则取色器无法正常工作
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.hide()
        QTimer.singleShot(200, self._show_overlay)
    
    def _show_overlay(self):
        """显示取色覆盖层"""
        from tools.color_picker import ColorPickerOverlay
        self.overlay = ColorPickerOverlay()
        self.overlay.color_picked.connect(self._on_color_picked)
        self.overlay.cancelled.connect(self._on_picking_cancelled)
        # 使用 show() 而不是 showFullScreen()，因为窗口已经设置了全屏几何
        self.overlay.show()
        self.overlay.activateWindow()
        self.overlay.setFocus()
    
    def _on_color_picked(self, color: QColor):
        """取色完成"""
        self._set_color(color)
        # 添加到自定义颜色
        self._add_to_custom()
        # 恢复模态状态
        if hasattr(self, '_original_modality'):
            self.setWindowModality(self._original_modality)
        self.show()
        self.activateWindow()
        self.raise_()
        # 自动复制
        self._copy_color()
    
    def _on_picking_cancelled(self):
        """取消取色"""
        # 恢复模态状态
        if hasattr(self, '_original_modality'):
            self.setWindowModality(self._original_modality)
        self.show()
        self.activateWindow()
        self.raise_()
    
    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.close()
        elif key == Qt.Key.Key_P:
            self._start_picking()
        elif key == Qt.Key.Key_A:
            self._add_to_custom()
        elif key == Qt.Key.Key_C:
            self._copy_color()
    
    def get_color(self) -> QColor:
        """获取当前颜色"""
        return self.current_color
    
    def set_color(self, color: QColor):
        """设置当前颜色"""
        self._set_color(color)
        
    def get_color(self):
        """获取当前选择的颜色"""
        return self.current_color

    @staticmethod
    def getColor(initial_color=None, parent=None, title=None, config=None):
        """静态方法，弹出对话框选择颜色"""
        dialog = PaletteWindow(config=config, is_dialog=True, parent=parent)
        dialog.setWindowTitle(title)
        if initial_color:
            dialog.set_color(QColor(initial_color))
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_color()
        return QColor()  # 返回无效颜色表示取消


def start_color_picker(callback=None, config=None):
    """直接启动取色器，取色完成后显示调色板"""
    from tools.color_picker import ColorPickerOverlay
    
    overlay = ColorPickerOverlay()
    
    # 保存引用防止被垃圾回收
    overlay._palette_window = None
    
    def on_picked(color):
        # 复制颜色
        clipboard = QApplication.clipboard()
        clipboard.setText(color.name().upper())
        
        # 显示调色板并设置颜色
        palette = PaletteWindow(config)
        palette._set_color(color)
        # 添加到自定义颜色
        palette._add_to_custom()
        palette.show()
        palette.activateWindow()
        
        # 显示提示
        toast = ToastWidget(f"已复制: {color.name().upper()}")
        toast.show_at_cursor()
        
        # 保存引用
        overlay._palette_window = palette
        
        if callback:
            callback(color)
    
    overlay.color_picked.connect(on_picked)
    # 使用 show() 而不是 showFullScreen()
    overlay.show()
    overlay.activateWindow()
    overlay.setFocus()
    return overlay
