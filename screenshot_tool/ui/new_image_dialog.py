"""
新建图像对话框 - 带预览的设计
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QPushButton, QFrame, QComboBox, QWidget
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QIcon, QPainter, QPen
from ui.icons import set_window_icon


# 预设尺寸列表
PRESET_SIZES = [
    ("上次使用", None, None),
    ("剪贴板", None, None),
    ("自定义", None, None),
    ("1920 × 1080 (FHD)", 1920, 1080),
    ("1366 × 768 (HD)", 1366, 768),
    ("1280 × 720 (720p)", 1280, 720),
    ("1024 × 768 (XGA)", 1024, 768),
    ("800 × 600 (SVGA)", 800, 600),
    ("2560 × 1440 (QHD)", 2560, 1440),
    ("3840 × 2160 (4K)", 3840, 2160),
]

# 预设背景颜色
PRESET_COLORS = [
    ("白色", "#FFFFFF"),
    ("黑色", "#000000"),
    ("透明", "transparent"),
    ("灰色", "#808080"),
    ("红色", "#FF0000"),
    ("蓝色", "#0000FF"),
]


class CanvasPreviewWidget(QWidget):
    """画布预览控件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.canvas_width = 800
        self.canvas_height = 600
        self.canvas_color = QColor(255, 255, 255)
        self.is_transparent = False
        self.setMinimumSize(180, 160)
    
    def set_canvas_size(self, width: int, height: int):
        """设置画布尺寸"""
        self.canvas_width = width
        self.canvas_height = height
        self.update()
    
    def set_canvas_color(self, color: QColor, is_transparent: bool = False):
        """设置画布颜色"""
        self.canvas_color = color
        self.is_transparent = is_transparent
        self.update()
    
    def paintEvent(self, event):
        """绘制预览"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制背景
        painter.fillRect(self.rect(), QColor("#e8e8e8"))
        
        # 计算预览区域
        margin = 15
        preview_area_w = self.width() - margin * 2
        preview_area_h = self.height() - margin * 2
        
        # 计算画布在预览区域中的缩放比例
        if self.canvas_width > 0 and self.canvas_height > 0:
            scale = min(preview_area_w / self.canvas_width, preview_area_h / self.canvas_height)
            scale = min(scale, 1.0)  # 不放大超过原始尺寸的比例
            
            preview_w = int(self.canvas_width * scale)
            preview_h = int(self.canvas_height * scale)
            
            # 居中显示
            x = (self.width() - preview_w) // 2
            y = (self.height() - preview_h) // 2
            
            # 绘制阴影
            painter.fillRect(x + 3, y + 3, preview_w, preview_h, QColor(180, 180, 180))
            
            # 绘制画布
            if self.is_transparent:
                # 绘制透明棋盘格
                block_size = 8
                for row in range(0, preview_h, block_size):
                    for col in range(0, preview_w, block_size):
                        if (row // block_size + col // block_size) % 2 == 0:
                            painter.fillRect(x + col, y + row, 
                                           min(block_size, preview_w - col), 
                                           min(block_size, preview_h - row), 
                                           QColor(255, 255, 255))
                        else:
                            painter.fillRect(x + col, y + row, 
                                           min(block_size, preview_w - col), 
                                           min(block_size, preview_h - row), 
                                           QColor(204, 204, 204))
            else:
                painter.fillRect(x, y, preview_w, preview_h, self.canvas_color)
            
            # 绘制边框
            painter.setPen(QPen(QColor(150, 150, 150), 1))
            painter.drawRect(x, y, preview_w, preview_h)


class NewImageDialog(QDialog):
    """新建图像对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_color = QColor(255, 255, 255)
        self.is_transparent = False
        self.last_width = 800
        self.last_height = 600
        self._link_ratio = False
        self._aspect_ratio = 800 / 600
        self._updating_size = False
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("新建图像")
        set_window_icon(self)
        self.setFixedSize(520, 340)
        self.setStyleSheet("""
            QDialog { background: #f5f5f5; }
            QLabel { color: #333; font-size: 12px; }
            QLabel[title="true"] { font-size: 18px; font-weight: bold; color: #2B579A; }
            QLabel[info="true"] { color: #666; font-size: 11px; }
            QSpinBox, QComboBox {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 5px 8px;
                background: white;
                color: #333;
                min-height: 24px;
            }
            QSpinBox:focus, QComboBox:focus { border-color: #0078D7; }
            QPushButton {
                background: #0078D7;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 20px;
                font-size: 12px;
            }
            QPushButton:hover { background: #005A9E; }
            QPushButton[secondary="true"] { background: #e0e0e0; color: #333; }
            QPushButton[secondary="true"]:hover { background: #d0d0d0; }
        """)
        
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 左侧：预览区域
        left_layout = QVBoxLayout()
        left_layout.setSpacing(8)
        
        self.preview_widget = CanvasPreviewWidget()
        self.preview_widget.setFixedSize(180, 160)
        left_layout.addWidget(self.preview_widget)
        
        # 尺寸信息标签
        self.size_info_label = QLabel(f"{self.last_width} × {self.last_height} px")
        self.size_info_label.setProperty("info", True)
        self.size_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.size_info_label)
        
        left_layout.addStretch()
        main_layout.addLayout(left_layout)
        
        # 右侧：设置区域
        right_layout = QVBoxLayout()
        right_layout.setSpacing(12)
        
        # 标题
        title = QLabel("新建图像")
        title.setProperty("title", True)
        right_layout.addWidget(title)
        
        # 画布大小信息
        self.canvas_size_label = QLabel(f"画布大小: {self.last_width} × {self.last_height}")
        self.canvas_size_label.setProperty("info", True)
        right_layout.addWidget(self.canvas_size_label)
        
        right_layout.addSpacing(5)
        
        # 预设选择
        preset_layout = QHBoxLayout()
        preset_label = QLabel("预设:")
        preset_label.setFixedWidth(60)
        preset_layout.addWidget(preset_label)
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(180)
        for name, w, h in PRESET_SIZES:
            self.preset_combo.addItem(name)
        self.preset_combo.setCurrentIndex(0)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addStretch()
        right_layout.addLayout(preset_layout)
        
        # 宽度
        width_layout = QHBoxLayout()
        width_label = QLabel("宽度:")
        width_label.setFixedWidth(60)
        width_layout.addWidget(width_label)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 200000)
        self.width_spin.setValue(self.last_width)
        self.width_spin.setSuffix(" px")
        self.width_spin.setMinimumWidth(120)
        self.width_spin.valueChanged.connect(self._on_width_changed)
        width_layout.addWidget(self.width_spin)
        width_layout.addStretch()
        right_layout.addLayout(width_layout)
        
        # 高度
        height_layout = QHBoxLayout()
        height_label = QLabel("高度:")
        height_label.setFixedWidth(60)
        height_layout.addWidget(height_label)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 200000)
        self.height_spin.setValue(self.last_height)
        self.height_spin.setSuffix(" px")
        self.height_spin.setMinimumWidth(120)
        self.height_spin.valueChanged.connect(self._on_height_changed)
        height_layout.addWidget(self.height_spin)
        height_layout.addStretch()
        right_layout.addLayout(height_layout)
        
        # 背景色
        color_layout = QHBoxLayout()
        color_label = QLabel("背景色:")
        color_label.setFixedWidth(60)
        color_layout.addWidget(color_label)
        self.color_combo = QComboBox()
        self.color_combo.setMinimumWidth(100)
        for name, _ in PRESET_COLORS:
            self.color_combo.addItem(name)
        self.color_combo.currentIndexChanged.connect(self._on_color_preset_changed)
        color_layout.addWidget(self.color_combo)
        
        # 颜色预览
        self.color_preview = QFrame()
        self.color_preview.setFixedSize(40, 26)
        self._update_color_preview()
        color_layout.addWidget(self.color_preview)
        
        # 自定义按钮
        custom_btn = QPushButton("...")
        custom_btn.setProperty("secondary", True)
        custom_btn.setFixedWidth(32)
        custom_btn.setToolTip("自定义颜色")
        custom_btn.clicked.connect(self._select_color)
        color_layout.addWidget(custom_btn)
        color_layout.addStretch()
        right_layout.addLayout(color_layout)
        
        right_layout.addStretch()
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("secondary", True)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        
        right_layout.addLayout(btn_layout)
        
        main_layout.addLayout(right_layout, 1)
        
        # 初始化预览
        self._update_preview()
    
    def _update_preview(self):
        """更新预览"""
        width = self.width_spin.value()
        height = self.height_spin.value()
        self.preview_widget.set_canvas_size(width, height)
        self.preview_widget.set_canvas_color(self.selected_color, self.is_transparent)
        self.size_info_label.setText(f"{width} × {height} px")
        self.canvas_size_label.setText(f"画布大小: {width} × {height}")
    
    def _update_color_preview(self):
        """更新颜色预览"""
        if self.is_transparent:
            self.color_preview.setStyleSheet(
                "QFrame { background: qlineargradient(x1:0, y1:0, x2:0.1, y2:0.1, "
                "stop:0 #ccc, stop:0.5 #ccc, stop:0.5 #fff, stop:1 #fff); "
                "border: 1px solid #ccc; border-radius: 3px; }"
            )
        else:
            self.color_preview.setStyleSheet(
                f"QFrame {{ background: {self.selected_color.name()}; "
                "border: 1px solid #ccc; border-radius: 3px; }}"
            )
    
    def _on_width_changed(self, value: int):
        """宽度改变"""
        if self._updating_size:
            return
        if self._link_ratio and self._aspect_ratio > 0:
            self._updating_size = True
            self.height_spin.setValue(max(1, int(value / self._aspect_ratio)))
            self._updating_size = False
        self._update_preview()
    
    def _on_height_changed(self, value: int):
        """高度改变"""
        if self._updating_size:
            return
        if self._link_ratio and self._aspect_ratio > 0:
            self._updating_size = True
            self.width_spin.setValue(max(1, int(value * self._aspect_ratio)))
            self._updating_size = False
        self._update_preview()
    
    def _on_preset_changed(self, index: int):
        """预设选择改变"""
        if index < 0 or index >= len(PRESET_SIZES):
            return
        
        name, w, h = PRESET_SIZES[index]
        
        if name == "剪贴板":
            from PySide6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            image = clipboard.image()
            if not image.isNull():
                self._updating_size = True
                self.width_spin.setValue(image.width())
                self.height_spin.setValue(image.height())
                self._updating_size = False
        elif name == "上次使用":
            self._updating_size = True
            self.width_spin.setValue(self.last_width)
            self.height_spin.setValue(self.last_height)
            self._updating_size = False
        elif w and h:
            self._updating_size = True
            self.width_spin.setValue(w)
            self.height_spin.setValue(h)
            self._updating_size = False
        
        self._update_preview()
    
    def _on_color_preset_changed(self, index: int):
        """颜色预设改变"""
        if index < 0 or index >= len(PRESET_COLORS):
            return
        
        name, color_str = PRESET_COLORS[index]
        
        if color_str == "transparent":
            self.is_transparent = True
            self.selected_color = QColor(255, 255, 255, 0)
        else:
            self.is_transparent = False
            self.selected_color = QColor(color_str)
        
        self._update_color_preview()
        self._update_preview()
    
    def _select_color(self):
        """选择自定义颜色"""
        from tools.palette import PaletteWindow
        
        self.palette_dialog = PaletteWindow()
        self.palette_dialog.set_color(self.selected_color)
        
        original_close = self.palette_dialog.closeEvent
        dialog_ref = self
        
        def on_close(event):
            color = dialog_ref.palette_dialog.get_color()
            dialog_ref.selected_color = color
            dialog_ref.is_transparent = False
            dialog_ref._update_color_preview()
            dialog_ref._update_preview()
            dialog_ref.show()
            dialog_ref.activateWindow()
            original_close(event)
        
        self.palette_dialog.closeEvent = on_close
        self.hide()
        self.palette_dialog.show()
    
    def get_size(self) -> QSize:
        """获取尺寸"""
        return QSize(self.width_spin.value(), self.height_spin.value())
    
    def get_color(self) -> QColor:
        """获取背景颜色"""
        if self.is_transparent:
            return QColor(255, 255, 255, 0)
        return self.selected_color
