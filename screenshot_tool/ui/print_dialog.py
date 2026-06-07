"""
打印对话框 - 参考 PicPick 设计
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QComboBox, QSpinBox,
    QGroupBox, QGridLayout, QScrollArea, QWidget
)
from PySide6.QtCore import Qt, QSize, QRect, QMarginsF
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QPageLayout, QPageSize
from PySide6.QtPrintSupport import QPrinter, QPrinterInfo, QPrintDialog


class PrintPreviewWidget(QWidget):
    """打印预览控件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = None
        self.page_size = QSize(210, 297)  # A4 默认 (mm)
        self.margins = [10, 10, 10, 10]  # 左上右下边距 (mm)
        self.scale_mode = "fit"  # fit, 100%, custom
        self.scale_percent = 100
        self.orientation = "portrait"  # portrait, landscape
        self.setMinimumSize(300, 400)
        self.setStyleSheet("background: #e0e0e0;")
    
    def set_image(self, pixmap: QPixmap):
        """设置要打印的图像"""
        self.pixmap = pixmap
        self.update()
    
    def set_margins(self, left, top, right, bottom):
        """设置边距 (mm)"""
        self.margins = [left, top, right, bottom]
        self.update()
    
    def set_orientation(self, orientation: str):
        """设置方向"""
        self.orientation = orientation
        self.update()
    
    def set_scale_mode(self, mode: str, percent: int = 100):
        """设置缩放模式"""
        self.scale_mode = mode
        self.scale_percent = percent
        self.update()
    
    def paintEvent(self, event):
        """绘制预览"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 计算纸张显示区域
        widget_w = self.width()
        widget_h = self.height()
        
        # 纸张尺寸 (根据方向)
        if self.orientation == "portrait":
            paper_w, paper_h = self.page_size.width(), self.page_size.height()
        else:
            paper_w, paper_h = self.page_size.height(), self.page_size.width()
        
        # 计算缩放比例使纸张适应控件
        scale = min((widget_w - 40) / paper_w, (widget_h - 40) / paper_h)
        
        # 纸张显示尺寸
        display_w = int(paper_w * scale)
        display_h = int(paper_h * scale)
        
        # 居中显示
        paper_x = (widget_w - display_w) // 2
        paper_y = (widget_h - display_h) // 2
        
        # 绘制纸张阴影
        painter.fillRect(paper_x + 3, paper_y + 3, display_w, display_h, QColor(180, 180, 180))
        
        # 绘制纸张
        painter.fillRect(paper_x, paper_y, display_w, display_h, QColor(255, 255, 255))
        
        # 绘制边距虚线框
        margin_left = int(self.margins[0] * scale)
        margin_top = int(self.margins[1] * scale)
        margin_right = int(self.margins[2] * scale)
        margin_bottom = int(self.margins[3] * scale)
        
        content_x = paper_x + margin_left
        content_y = paper_y + margin_top
        content_w = display_w - margin_left - margin_right
        content_h = display_h - margin_top - margin_bottom
        
        pen = QPen(QColor(100, 100, 100), 1, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawRect(content_x, content_y, content_w, content_h)
        
        # 绘制图像
        if self.pixmap and not self.pixmap.isNull():
            img_w = self.pixmap.width()
            img_h = self.pixmap.height()
            
            # 计算图像在内容区域的显示尺寸
            if self.scale_mode == "fit":
                img_scale = min(content_w / img_w, content_h / img_h)
            elif self.scale_mode == "100%":
                # 100% 时使用实际像素比例
                img_scale = scale * 0.264583  # mm to pixel (96 dpi)
            else:
                img_scale = (self.scale_percent / 100) * scale * 0.264583
            
            draw_w = int(img_w * img_scale)
            draw_h = int(img_h * img_scale)
            
            # 居中显示图像
            img_x = content_x + (content_w - draw_w) // 2
            img_y = content_y + (content_h - draw_h) // 2
            
            # 裁剪到内容区域
            painter.setClipRect(content_x, content_y, content_w, content_h)
            painter.drawPixmap(img_x, img_y, draw_w, draw_h, self.pixmap)
            painter.setClipping(False)
        
        # 绘制纸张边框
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        painter.drawRect(paper_x, paper_y, display_w, display_h)


class PrintDialog(QDialog):
    """打印对话框"""
    
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.pixmap = pixmap
        self.printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        self.setup_ui()
        self._load_printers()
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("打印")
        self.setMinimumSize(750, 550)
        self.setStyleSheet("""
            QDialog { background: #f5f5f5; }
            QLabel { color: #333; font-size: 12px; }
            QLabel[title="true"] { font-size: 20px; font-weight: bold; color: #333; }
            QLabel[section="true"] { font-size: 13px; font-weight: bold; color: #333; }
            QComboBox, QSpinBox {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 5px 8px;
                background: white;
                min-height: 24px;
            }
            QComboBox:focus, QSpinBox:focus { border-color: #0078D7; }
            QPushButton {
                background: #0078D7;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 20px;
                font-size: 12px;
            }
            QPushButton:hover { background: #005A9E; }
            QPushButton[secondary="true"] {
                background: #e0e0e0;
                color: #333;
            }
            QPushButton[secondary="true"]:hover { background: #d0d0d0; }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 8px;
                padding: 12px;
                padding-top: 20px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 左侧：设置区域
        left_layout = QVBoxLayout()
        left_layout.setSpacing(12)
        
        # 标题
        title = QLabel("打印")
        title.setProperty("title", True)
        left_layout.addWidget(title)
        
        # 打印按钮
        print_btn_layout = QHBoxLayout()
        self.print_btn = QPushButton("🖨️ 打印")
        self.print_btn.setFixedHeight(40)
        self.print_btn.clicked.connect(self._do_print)
        print_btn_layout.addWidget(self.print_btn)
        print_btn_layout.addStretch()
        left_layout.addLayout(print_btn_layout)
        
        # 打印机选择
        printer_label = QLabel("打印机")
        printer_label.setProperty("section", True)
        left_layout.addWidget(printer_label)
        
        self.printer_combo = QComboBox()
        self.printer_combo.currentIndexChanged.connect(self._on_printer_changed)
        left_layout.addWidget(self.printer_combo)
        
        # 打印设置链接
        settings_link = QLabel('<a href="#" style="color: #0078D7;">打印设置</a>')
        settings_link.setOpenExternalLinks(False)
        settings_link.linkActivated.connect(self._open_printer_settings)
        left_layout.addWidget(settings_link)
        
        # 设置组
        settings_label = QLabel("设置")
        settings_label.setProperty("section", True)
        left_layout.addWidget(settings_label)

        # 缩放设置
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("缩放:"))
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["调整到 100%", "适合页面", "自定义"])
        self.scale_combo.setCurrentIndex(1)
        self.scale_combo.currentIndexChanged.connect(self._on_scale_changed)
        scale_layout.addWidget(self.scale_combo)
        left_layout.addLayout(scale_layout)
        
        # 方向设置
        orientation_layout = QHBoxLayout()
        orientation_layout.addWidget(QLabel("方向:"))
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItems(["纵向", "横向"])
        self.orientation_combo.currentIndexChanged.connect(self._on_orientation_changed)
        orientation_layout.addWidget(self.orientation_combo)
        left_layout.addLayout(orientation_layout)
        
        # 纸张尺寸
        paper_layout = QHBoxLayout()
        paper_layout.addWidget(QLabel("纸张尺寸:"))
        self.paper_combo = QComboBox()
        self.paper_combo.addItems([
            "A4 (210 × 297 mm)",
            "A3 (297 × 420 mm)",
            "A5 (148 × 210 mm)",
            "Letter (216 × 279 mm)",
            "Legal (216 × 356 mm)"
        ])
        self.paper_combo.currentIndexChanged.connect(self._on_paper_changed)
        paper_layout.addWidget(self.paper_combo)
        left_layout.addLayout(paper_layout)
        
        # 边距设置
        margin_layout = QHBoxLayout()
        margin_layout.addWidget(QLabel("页边距:"))
        self.margin_combo = QComboBox()
        self.margin_combo.addItems([
            "正常 (左: 10mm, 上: 10mm)",
            "窄 (左: 5mm, 上: 5mm)",
            "宽 (左: 20mm, 上: 20mm)",
            "自定义..."
        ])
        self.margin_combo.currentIndexChanged.connect(self._on_margin_changed)
        margin_layout.addWidget(self.margin_combo)
        left_layout.addLayout(margin_layout)
        
        # 打印颜色
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("打印颜色:"))
        self.color_combo = QComboBox()
        self.color_combo.addItems(["彩色", "灰度", "黑白"])
        color_layout.addWidget(self.color_combo)
        left_layout.addLayout(color_layout)
        
        # 页面设置链接
        page_link = QLabel('<a href="#" style="color: #0078D7;">页面设置</a>')
        page_link.setOpenExternalLinks(False)
        left_layout.addWidget(page_link)
        
        left_layout.addStretch()
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("secondary", True)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        left_layout.addLayout(btn_layout)
        
        main_layout.addLayout(left_layout)
        
        # 右侧：预览区域
        right_layout = QVBoxLayout()
        
        # 边距输入
        margin_input_layout = QHBoxLayout()
        margin_input_layout.addWidget(QLabel("边距"))
        margin_input_layout.addWidget(QLabel("左"))
        self.margin_left = QSpinBox()
        self.margin_left.setRange(0, 50)
        self.margin_left.setValue(10)
        self.margin_left.setSuffix(" mm")
        self.margin_left.valueChanged.connect(self._update_preview)
        margin_input_layout.addWidget(self.margin_left)
        
        margin_input_layout.addWidget(QLabel("上"))
        self.margin_top = QSpinBox()
        self.margin_top.setRange(0, 50)
        self.margin_top.setValue(10)
        self.margin_top.setSuffix(" mm")
        self.margin_top.valueChanged.connect(self._update_preview)
        margin_input_layout.addWidget(self.margin_top)
        
        margin_input_layout.addWidget(QLabel("右"))
        self.margin_right = QSpinBox()
        self.margin_right.setRange(0, 50)
        self.margin_right.setValue(10)
        self.margin_right.setSuffix(" mm")
        self.margin_right.valueChanged.connect(self._update_preview)
        margin_input_layout.addWidget(self.margin_right)
        
        margin_input_layout.addWidget(QLabel("下"))
        self.margin_bottom = QSpinBox()
        self.margin_bottom.setRange(0, 50)
        self.margin_bottom.setValue(10)
        self.margin_bottom.setSuffix(" mm")
        self.margin_bottom.valueChanged.connect(self._update_preview)
        margin_input_layout.addWidget(self.margin_bottom)
        
        margin_input_layout.addStretch()
        right_layout.addLayout(margin_input_layout)
        
        # 预览控件
        self.preview = PrintPreviewWidget()
        self.preview.set_image(self.pixmap)
        right_layout.addWidget(self.preview, 1)
        
        # 页面信息
        info_layout = QHBoxLayout()
        self.page_info = QLabel("页面: 1 - 1")
        info_layout.addWidget(self.page_info)
        info_layout.addStretch()
        self.size_info = QLabel("纸张尺寸: 210 mm × 297 mm")
        info_layout.addWidget(self.size_info)
        right_layout.addLayout(info_layout)
        
        main_layout.addLayout(right_layout, 1)
    
    def _load_printers(self):
        """加载打印机列表"""
        printers = QPrinterInfo.availablePrinters()
        default_printer = QPrinterInfo.defaultPrinter()
        
        for printer in printers:
            self.printer_combo.addItem(printer.printerName())
        
        # 选择默认打印机
        if default_printer.printerName():
            idx = self.printer_combo.findText(default_printer.printerName())
            if idx >= 0:
                self.printer_combo.setCurrentIndex(idx)
    
    def _on_printer_changed(self, index):
        """打印机改变"""
        printer_name = self.printer_combo.currentText()
        self.printer.setPrinterName(printer_name)
    
    def _on_scale_changed(self, index):
        """缩放改变"""
        modes = ["100%", "fit", "custom"]
        if index < len(modes):
            self.preview.set_scale_mode(modes[index])
    
    def _on_orientation_changed(self, index):
        """方向改变"""
        orientation = "portrait" if index == 0 else "landscape"
        self.preview.set_orientation(orientation)
        if index == 0:
            self.printer.setPageOrientation(QPageLayout.Orientation.Portrait)
        else:
            self.printer.setPageOrientation(QPageLayout.Orientation.Landscape)
    
    def _on_paper_changed(self, index):
        """纸张尺寸改变"""
        sizes = [
            (210, 297),  # A4
            (297, 420),  # A3
            (148, 210),  # A5
            (216, 279),  # Letter
            (216, 356),  # Legal
        ]
        if index < len(sizes):
            w, h = sizes[index]
            self.preview.page_size = QSize(w, h)
            self.size_info.setText(f"纸张尺寸: {w} mm × {h} mm")
            self.preview.update()
    
    def _on_margin_changed(self, index):
        """边距预设改变"""
        margins = [
            (10, 10, 10, 10),  # 正常
            (5, 5, 5, 5),      # 窄
            (20, 20, 20, 20),  # 宽
        ]
        if index < len(margins):
            l, t, r, b = margins[index]
            self.margin_left.setValue(l)
            self.margin_top.setValue(t)
            self.margin_right.setValue(r)
            self.margin_bottom.setValue(b)
    
    def _update_preview(self):
        """更新预览"""
        self.preview.set_margins(
            self.margin_left.value(),
            self.margin_top.value(),
            self.margin_right.value(),
            self.margin_bottom.value()
        )
    
    def _open_printer_settings(self):
        """打开打印机设置"""
        dialog = QPrintDialog(self.printer, self)
        dialog.exec()
    
    def _do_print(self):
        """执行打印"""
        if self.pixmap.isNull():
            return
        
        # 设置打印机
        printer_name = self.printer_combo.currentText()
        self.printer.setPrinterName(printer_name)
        
        # 设置边距
        margins = QMarginsF(
            self.margin_left.value(),
            self.margin_top.value(),
            self.margin_right.value(),
            self.margin_bottom.value()
        )
        self.printer.setPageMargins(margins, QPageLayout.Unit.Millimeter)
        
        # 打印
        painter = QPainter()
        if painter.begin(self.printer):
            # 计算打印区域
            page_rect = self.printer.pageRect(QPrinter.Unit.DevicePixel)
            
            # 计算图像缩放
            scale_mode = self.scale_combo.currentIndex()
            if scale_mode == 0:  # 100%
                scale = 1.0
            elif scale_mode == 1:  # 适合页面
                scale = min(
                    page_rect.width() / self.pixmap.width(),
                    page_rect.height() / self.pixmap.height()
                )
            else:
                scale = 1.0
            
            # 计算绘制尺寸
            draw_w = int(self.pixmap.width() * scale)
            draw_h = int(self.pixmap.height() * scale)
            
            # 居中绘制
            x = int((page_rect.width() - draw_w) / 2)
            y = int((page_rect.height() - draw_h) / 2)
            
            painter.drawPixmap(x, y, draw_w, draw_h, self.pixmap)
            painter.end()
            
            self.accept()
