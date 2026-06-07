"""
放大镜工具
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSlider, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QCursor, QGuiApplication, QPixmap, QPainter, QColor, QPen, QIcon
from ui.icons import set_window_icon


class MagnifierWindow(QWidget):
    """放大镜窗口 - 现代白色风格"""
    
    def __init__(self):
        super().__init__()
        self.zoom_level = 4
        self.capture_size = 50
        self.drag_pos = None
        
        self.setup_ui()
        self.setup_timer()
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("放大镜")
        set_window_icon(self)
        self.setFixedSize(320, 420)
        # 无边框、置顶、任务栏图标
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setStyleSheet("""
            QWidget#mainContainer {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
            }
            QLabel { 
                color: #333333; 
                font-family: "Microsoft YaHei";
                font-size: 12px;
            }
            QLabel#titleLabel {
                font-weight: bold;
                font-size: 14px;
                color: #1a1a1a;
            }
            QPushButton#closeBtn {
                background-color: transparent;
                border: none;
                color: #999;
                font-size: 18px;
                font-weight: bold;
                border-radius: 15px;
            }
            QPushButton#closeBtn:hover {
                background-color: #ff4d4f;
                color: white;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #f0f0f0;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 14px;
                height: 14px;
                margin: -5px 0;
                background: #0078D7;
                border: 2px solid white;
                border-radius: 7px;
            }
        """)
        
        # 主容器
        self.container = QWidget(self)
        self.container.setObjectName("mainContainer")
        self.container.setFixedSize(self.size())
        
        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(15, 10, 15, 15)
        main_layout.setSpacing(12)
        
        # 标题栏区域
        header_layout = QHBoxLayout()
        title_label = QLabel("放大镜")
        title_label.setObjectName("titleLabel")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self.close_btn = QPushButton("×")
        self.close_btn.setObjectName("closeBtn")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.close)
        header_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(header_layout)
        
        # 放大显示区域
        self.display = QLabel()
        self.display.setFixedSize(280, 240)
        self.display.setStyleSheet("""
            background: #000; 
            border: 1px solid #eeeeee; 
            border-radius: 4px;
        """)
        self.display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.display, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # 底部信息区
        info_container = QWidget()
        info_container.setStyleSheet("background: #f9f9f9; border-radius: 8px;")
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(10, 8, 10, 8)
        info_layout.setSpacing(8)
        
        # 缩放控制
        zoom_layout = QHBoxLayout()
        zoom_icon = QLabel("🔍")
        zoom_layout.addWidget(zoom_icon)
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(2, 12)
        self.zoom_slider.setValue(self.zoom_level)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        zoom_layout.addWidget(self.zoom_slider)
        
        self.zoom_label = QLabel(f"{self.zoom_level}x")
        self.zoom_label.setFixedWidth(30)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        zoom_layout.addWidget(self.zoom_label)
        info_layout.addLayout(zoom_layout)
        
        # 坐标与颜色
        bottom_layout = QHBoxLayout()
        
        # 位置
        self.pos_label = QLabel("📍 (0, 0)")
        bottom_layout.addWidget(self.pos_label)
        
        bottom_layout.addStretch()
        
        # 颜色
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(14, 14)
        self.color_preview.setStyleSheet("background: black; border: 1px solid #ddd; border-radius: 3px;")
        bottom_layout.addWidget(self.color_preview)
        
        self.color_label = QLabel("#000000")
        self.color_label.setStyleSheet("font-family: 'Consolas'; color: #666;")
        bottom_layout.addWidget(self.color_label)
        
        info_layout.addLayout(bottom_layout)
        main_layout.addWidget(info_container)
        
        # 添加底部提示
        hint_label = QLabel("按下 Esc 键退出")
        hint_label.setStyleSheet("color: #bbb; font-size: 10px;")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(hint_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self.drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        super().keyPressEvent(event)
    
    def setup_timer(self):
        """设置定时器"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_magnifier)
        self.timer.start(50)
    
    def _on_zoom_changed(self, value):
        """缩放改变"""
        self.zoom_level = value
        self.zoom_label.setText(f"{value}x")
    
    def update_magnifier(self):
        """更新放大镜 - 采用裁剪拉伸法，更稳定"""
        pos = QCursor.pos()
        screen = QGuiApplication.screenAt(pos)
        
        if screen:
            # 1. 确定显示区域大小 (280x240)
            display_w = self.display.width()
            display_h = self.display.height()
            
            # 2. 计算在当前倍率下，我们需要从屏幕上抓取的实际物理区域大小
            # 例如：倍率为 2x 时，抓取 140x120；倍率为 10x 时，抓取 28x24
            # 这样放大到 280x240 就能实现精确缩放
            cap_w = max(1, display_w // self.zoom_level)
            cap_h = max(1, display_h // self.zoom_level)
            
            # 3. 考虑到 DPI 缩放，增加抓取范围以确保覆盖（后续用 copy 裁剪）
            # 直接抓取目标区域
            x = pos.x() - cap_w // 2
            y = pos.y() - cap_h // 2
            
            # 4. 抓取屏幕
            # 注意：grabWindow 在不同系统上对 x,y 的解释可能略有不同，
            # 我们直接使用 screen.grabWindow(0, x, y, cap_w, cap_h)
            pixmap = screen.grabWindow(0, x, y, cap_w, cap_h)
            
            if not pixmap.isNull():
                # 5. 放大到显示区域
                # 使用 SmoothTransformation 虽然消耗略高，但画质更好
                # 如果觉得卡顿，可以改回 FastTransformation
                scaled = pixmap.scaled(
                    display_w, display_h,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.FastTransformation
                )
                
                # 6. 绘制中心十字线
                painter = QPainter(scaled)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
                # 使用对比色（红色+白色边框）确保在任何背景下可见
                painter.setPen(QPen(QColor(255, 255, 255, 180), 3))
                cx, cy = scaled.width() // 2, scaled.height() // 2
                painter.drawLine(cx, 0, cx, scaled.height())
                painter.drawLine(0, cy, scaled.width(), cy)
                
                painter.setPen(QPen(QColor(255, 0, 0, 200), 1))
                painter.drawLine(cx, 0, cx, scaled.height())
                painter.drawLine(0, cy, scaled.width(), cy)
                painter.end()
                
                self.display.setPixmap(scaled)
                
                # 7. 获取中心颜色
                # 采样 pixmap 中心点的颜色
                img = pixmap.toImage()
                if not img.isNull():
                    color = QColor(img.pixel(pixmap.width() // 2, pixmap.height() // 2))
                    self.color_preview.setStyleSheet(
                        f"background: {color.name()}; border: 1px solid #ddd; border-radius: 3px;"
                    )
                    self.color_label.setText(color.name().upper())
        
        # 8. 更新位置显示
        self.pos_label.setText(f"📍 ({pos.x()}, {pos.y()})")
    
    def closeEvent(self, event):
        """关闭事件"""
        self.timer.stop()
        super().closeEvent(event)
