from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QSlider
)
from PySide6.QtCore import Qt, Signal

class EffectsPanel(QFrame):
    """特效面板 - PicPick 风格"""
    
    effect_applied = Signal(str, int)
    undo_clicked = Signal()
    reset_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        self.setStyleSheet("""
            QFrame { 
                background: #f8f8f8; 
                border: 1px solid #d0d0d0;
                border-radius: 4px; 
            }
            QLabel { color: #333; font-size: 11px; }
            QPushButton {
                background: white;
                color: #333;
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover { 
                background: #e5f3ff;
                border-color: #0078d7;
            }
            QPushButton:pressed {
                background: #cce8ff;
            }
            QSlider::groove:horizontal { 
                height: 4px; 
                background: #d0d0d0; 
                border-radius: 2px; 
            }
            QSlider::handle:horizontal { 
                width: 14px; 
                margin: -5px 0; 
                background: #0078D7; 
                border-radius: 7px; 
            }
            QSlider::handle:horizontal:hover {
                background: #005a9e;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        title = QLabel("🎨 画质特效")
        title.setStyleSheet("font-weight: bold; color: #2B579A; font-size: 12px;")
        layout.addWidget(title)
        
        # 分隔线
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #d0d0d0;")
        layout.addWidget(sep)
        
        effects = [
            ("🌫 模糊", "blur"),
            ("🔍 锐化", "sharpen"),
            ("▦ 像素化", "pixelate"),
            ("🗻 浮雕", "emboss"),
            ("✨ 噪点", "noise"),
        ]
        
        for name, effect in effects:
            btn = QPushButton(name)
            btn.clicked.connect(lambda _, e=effect: self.effect_applied.emit(e, 5))
            layout.addWidget(btn)
        
        layout.addSpacing(8)
        
        # 强度滑块
        intensity_label = QLabel("特效强度:")
        intensity_label.setStyleSheet("color: #666;")
        layout.addWidget(intensity_label)
        
        self.intensity_slider = QSlider(Qt.Orientation.Horizontal)
        self.intensity_slider.setRange(1, 20)
        self.intensity_slider.setValue(5)
        layout.addWidget(self.intensity_slider)
        
        # 强度值显示
        self.intensity_value = QLabel("5")
        self.intensity_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.intensity_value.setStyleSheet("color: #0078d7; font-weight: bold;")
        self.intensity_slider.valueChanged.connect(lambda v: self.intensity_value.setText(str(v)))
        layout.addWidget(self.intensity_value)
        
        layout.addSpacing(12)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        self.undo_btn = QPushButton("↩ 撤销")
        self.undo_btn.clicked.connect(self.undo_clicked.emit)
        btn_layout.addWidget(self.undo_btn)
        
        self.reset_btn = QPushButton("↺ 重置")
        self.reset_btn.clicked.connect(self.reset_clicked.emit)
        btn_layout.addWidget(self.reset_btn)
        
        layout.addLayout(btn_layout)
        layout.addStretch()

    def reset_ui(self):
        """重置 UI 状态"""
        self.intensity_slider.blockSignals(True)
        self.intensity_slider.setValue(5)
        self.intensity_value.setText("5")
        self.intensity_slider.blockSignals(False)


class AdjustmentsPanel(QFrame):
    """色彩调整面板 - PicPick 风格"""
    
    adjustment_changed = Signal(str, int)
    apply_clicked = Signal()
    reset_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        self.setStyleSheet("""
            QFrame { 
                background: #f8f8f8; 
                border: 1px solid #d0d0d0;
                border-radius: 4px; 
            }
            QLabel { color: #333; font-size: 11px; }
            QPushButton {
                background: white;
                color: #333;
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover { 
                background: #e5f3ff;
                border-color: #0078d7;
            }
            QPushButton[primary="true"] { 
                background: #0078D7;
                color: white;
                border: none;
            }
            QPushButton[primary="true"]:hover { 
                background: #005a9e;
            }
            QSlider::groove:horizontal { 
                height: 4px; 
                background: #d0d0d0; 
                border-radius: 2px; 
            }
            QSlider::handle:horizontal { 
                width: 14px; 
                margin: -5px 0; 
                background: #0078D7; 
                border-radius: 7px; 
            }
            QSlider::handle:horizontal:hover {
                background: #005a9e;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        title = QLabel("🔆 色彩调整")
        title.setStyleSheet("font-weight: bold; color: #2B579A; font-size: 12px;")
        layout.addWidget(title)
        
        # 分隔线
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #d0d0d0;")
        layout.addWidget(sep)
        
        # 亮度
        brightness_row = QHBoxLayout()
        brightness_label = QLabel("☀ 亮度:")
        brightness_label.setFixedWidth(60)
        brightness_row.addWidget(brightness_label)
        self.brightness_value = QLabel("0")
        self.brightness_value.setFixedWidth(30)
        self.brightness_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.brightness_value.setStyleSheet("color: #0078d7; font-weight: bold;")
        brightness_row.addWidget(self.brightness_value)
        layout.addLayout(brightness_row)
        
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(-100, 100)
        self.brightness_slider.setValue(0)
        self.brightness_slider.valueChanged.connect(lambda v: (
            self.adjustment_changed.emit("brightness", v),
            self.brightness_value.setText(str(v))
        ))
        layout.addWidget(self.brightness_slider)
        
        # 对比度
        contrast_row = QHBoxLayout()
        contrast_label = QLabel("◐ 对比度:")
        contrast_label.setFixedWidth(60)
        contrast_row.addWidget(contrast_label)
        self.contrast_value = QLabel("0")
        self.contrast_value.setFixedWidth(30)
        self.contrast_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.contrast_value.setStyleSheet("color: #0078d7; font-weight: bold;")
        contrast_row.addWidget(self.contrast_value)
        layout.addLayout(contrast_row)
        
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setRange(-100, 100)
        self.contrast_slider.setValue(0)
        self.contrast_slider.valueChanged.connect(lambda v: (
            self.adjustment_changed.emit("contrast", v),
            self.contrast_value.setText(str(v))
        ))
        layout.addWidget(self.contrast_slider)
        
        # 饱和度
        saturation_row = QHBoxLayout()
        saturation_label = QLabel("🎨 饱和度:")
        saturation_label.setFixedWidth(60)
        saturation_row.addWidget(saturation_label)
        self.saturation_value = QLabel("0")
        self.saturation_value.setFixedWidth(30)
        self.saturation_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.saturation_value.setStyleSheet("color: #0078d7; font-weight: bold;")
        saturation_row.addWidget(self.saturation_value)
        layout.addLayout(saturation_row)
        
        self.saturation_slider = QSlider(Qt.Orientation.Horizontal)
        self.saturation_slider.setRange(-100, 100)
        self.saturation_slider.setValue(0)
        self.saturation_slider.valueChanged.connect(lambda v: (
            self.adjustment_changed.emit("saturation", v),
            self.saturation_value.setText(str(v))
        ))
        layout.addWidget(self.saturation_slider)
        
        layout.addSpacing(12)
        
        btn_layout = QHBoxLayout()
        reset_btn = QPushButton("↺ 重置")
        reset_btn.clicked.connect(self._reset)
        btn_layout.addWidget(reset_btn)
        
        apply_btn = QPushButton("✓ 应用")
        apply_btn.setProperty("primary", True)
        apply_btn.clicked.connect(self.apply_clicked.emit)
        btn_layout.addWidget(apply_btn)
        layout.addLayout(btn_layout)
        
        layout.addStretch()
    
    def set_adjustments(self, adj: dict):
        """同步外部调整参数到 UI"""
        self.brightness_slider.blockSignals(True)
        self.contrast_slider.blockSignals(True)
        self.saturation_slider.blockSignals(True)
        
        b = adj.get("brightness", 0)
        c = adj.get("contrast", 0)
        s = adj.get("saturation", 0)
        
        self.brightness_slider.setValue(b)
        self.contrast_slider.setValue(c)
        self.saturation_slider.setValue(s)
        self.brightness_value.setText(str(b))
        self.contrast_value.setText(str(c))
        self.saturation_value.setText(str(s))
        
        self.brightness_slider.blockSignals(False)
        self.contrast_slider.blockSignals(False)
        self.saturation_slider.blockSignals(False)

    def reset_ui(self):
        self.brightness_slider.blockSignals(True)
        self.contrast_slider.blockSignals(True)
        self.saturation_slider.blockSignals(True)
        
        self.brightness_slider.setValue(0)
        self.contrast_slider.setValue(0)
        self.saturation_slider.setValue(0)
        self.brightness_value.setText("0")
        self.contrast_value.setText("0")
        self.saturation_value.setText("0")
        
        self.brightness_slider.blockSignals(False)
        self.contrast_slider.blockSignals(False)
        self.saturation_slider.blockSignals(False)
        self.reset_clicked.emit()

    def _reset(self):
        self.reset_ui()
