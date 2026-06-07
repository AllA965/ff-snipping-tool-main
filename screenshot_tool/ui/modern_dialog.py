from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSpacerItem, QSizePolicy, QWidget, QTextEdit, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon

class ModernMessageBox(QDialog):
    """现代风格的对话框，提供比标准 QMessageBox 更美观的 UI"""
    
    def __init__(self, title, message, icon_type="info", parent=None, yes_text="确定", no_text="取消", cancel_text=None):
        super().__init__(parent)
        self.yes_text = yes_text
        self.no_text = no_text
        self.cancel_text = cancel_text
        self.setWindowTitle(title)
        self.setMinimumWidth(380)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setup_ui(title, message, icon_type)
        
    def setup_ui(self, title, message, icon_type):
        # 外层圆角边框
        self.main_frame = QFrame(self)
        self.main_frame.setObjectName("mainFrame")
        self.main_frame.setStyleSheet("""
            QFrame#mainFrame {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.main_frame)
        
        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)
        
        # 标题栏
        title_bar = QFrame()
        title_bar.setFixedHeight(45)
        title_bar.setStyleSheet("""
            background-color: #FBFBFB;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
            border-bottom: 1px solid #F0F0F0;
        """)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(18, 0, 12, 0)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; color: #333; font-size: 14px;")
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #AAA;
                font-size: 16px;
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: #FEEBEB;
                color: #F44336;
            }
        """)
        close_btn.clicked.connect(self.reject)
        title_layout.addWidget(close_btn)
        
        frame_layout.addWidget(title_bar)
        
        # 内容区
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(25, 30, 25, 30)
        content_layout.setSpacing(20)
        
        # 图标
        icon_label = QLabel()
        icon_size = 40
        icon_label.setFixedSize(icon_size, icon_size)
        
        import os
        if isinstance(icon_type, str) and (icon_type.endswith('.ico') or icon_type.endswith('.png') or os.path.exists(icon_type)):
            # 加载外部图标文件
            pixmap = QIcon(icon_type).pixmap(icon_size, icon_size)
            icon_label.setPixmap(pixmap)
            icon_label.setScaledContents(True)
            icon_color = "#9C27B0" # 默认问题颜色
        else:
            icon_char = "ℹ️"
            icon_color = "#2196F3"
            if icon_type == "warning":
                icon_char = "⚠️"
                icon_color = "#FF9800"
            elif icon_type == "error":
                icon_char = "❌"
                icon_color = "#F44336"
            elif icon_type == "success":
                icon_char = "✅"
                icon_color = "#4CAF50"
            elif icon_type == "question":
                icon_char = "❓"
                icon_color = "#9C27B0"
                
            icon_label.setText(icon_char)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            font = icon_label.font()
            font.setPointSize(24)
            icon_label.setFont(font)
        
        content_layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)
        
        # 文本内容
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("color: #444; font-size: 13px; line-height: 1.6;")
        content_layout.addWidget(message_label, 1)
        
        frame_layout.addWidget(content_widget)
        
        # 按钮区
        button_bar = QFrame()
        button_bar.setFixedHeight(60)
        button_bar.setStyleSheet("""
            background-color: #FBFBFB; 
            border-bottom-left-radius: 12px; 
            border-bottom-right-radius: 12px;
            border-top: 1px solid #F0F0F0;
        """)
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(20, 0, 20, 0)
        button_layout.setSpacing(12)
        
        button_layout.addStretch()
        
        if icon_type == "question":
            # 如果有第三个按钮（如：保存、丢弃、取消）
            if self.cancel_text:
                self.third_btn = QPushButton(self.cancel_text)
                self.third_btn.setFixedSize(90, 34)
                self.third_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                self.third_btn.setStyleSheet("""
                    QPushButton {
                        background-color: white;
                        color: #666;
                        border: 1px solid #DDD;
                        border-radius: 6px;
                        font-size: 13px;
                    }
                    QPushButton:hover {
                        background-color: #F5F5F5;
                        border-color: #CCC;
                    }
                """)
                self.third_btn.clicked.connect(lambda: self.done(2)) # 2 for Cancel/Third option
                button_layout.addWidget(self.third_btn)

            self.cancel_btn = QPushButton(self.no_text)
            self.cancel_btn.setFixedSize(90, 34)
            self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.cancel_btn.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    color: #666;
                    border: 1px solid #DDD;
                    border-radius: 6px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #F5F5F5;
                    border-color: #CCC;
                }
            """)
            self.cancel_btn.clicked.connect(self.reject)
            button_layout.addWidget(self.cancel_btn)
            
            self.ok_btn = QPushButton(self.yes_text)
            self.ok_btn.setFixedSize(90, 34)
            self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.ok_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {icon_color};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 13px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {QColor(icon_color).darker(110).name()};
                }}
            """)
            self.ok_btn.clicked.connect(self.accept)
            button_layout.addWidget(self.ok_btn)
        else:
            self.ok_btn = QPushButton("知道了")
            self.ok_btn.setFixedSize(100, 34)
            self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.ok_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {icon_color};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background-color: {QColor(icon_color).darker(110).name()};
                }}
            """)
            self.ok_btn.clicked.connect(self.accept)
            button_layout.addWidget(self.ok_btn)
            
        frame_layout.addWidget(button_bar)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    @staticmethod
    def information(parent, title, message, ok_text="确定"):
        dialog = ModernMessageBox(title, message, "info", parent, yes_text=ok_text)
        return dialog.exec()

    @staticmethod
    def warning(parent, title, message, ok_text="确定"):
        dialog = ModernMessageBox(title, message, "warning", parent, yes_text=ok_text)
        return dialog.exec()

    @staticmethod
    def error(parent, title, message, ok_text="确定"):
        dialog = ModernMessageBox(title, message, "error", parent, yes_text=ok_text)
        return dialog.exec()

    @staticmethod
    def success(parent, title, message, ok_text="确定"):
        dialog = ModernMessageBox(title, message, "success", parent, yes_text=ok_text)
        return dialog.exec()

    @staticmethod
    def question(parent, title, message, yes_text="确定", no_text="取消", cancel_text=None, icon_type="question"):
        dialog = ModernMessageBox(title, message, icon_type, parent, yes_text, no_text, cancel_text)
        return dialog.exec()


class OcrTextDialog(QDialog):
    """OCR 结果编辑对话框"""

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("识别文本")
        self.setMinimumSize(480, 360)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._drag_pos = None

        main_frame = QFrame(self)
        main_frame.setObjectName("mainFrame")
        main_frame.setStyleSheet("""
            QFrame#mainFrame {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(main_frame)

        frame_layout = QVBoxLayout(main_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        title_bar = QFrame()
        title_bar.setFixedHeight(45)
        title_bar.setStyleSheet("""
            background-color: #FBFBFB;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
            border-bottom: 1px solid #F0F0F0;
        """)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(18, 0, 12, 0)

        title_label = QLabel("识别文本")
        title_label.setStyleSheet("font-weight: bold; color: #333; font-size: 14px;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #AAA;
                font-size: 16px;
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: #FEEBEB;
                color: #F44336;
            }
        """)
        close_btn.clicked.connect(self.reject)
        title_layout.addWidget(close_btn)

        frame_layout.addWidget(title_bar)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 16, 20, 12)
        content_layout.setSpacing(8)

        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(text or "")
        self.text_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                font-size: 13px;
                padding: 6px;
            }
            QTextEdit:focus {
                border-color: #3B82F6;
            }
        """)
        content_layout.addWidget(self.text_edit)

        frame_layout.addWidget(content_widget)

        button_bar = QFrame()
        button_bar.setFixedHeight(56)
        button_bar.setStyleSheet("""
            background-color: #FBFBFB;
            border-bottom-left-radius: 12px;
            border-bottom-right-radius: 12px;
            border-top: 1px solid #F0F0F0;
        """)
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(16, 8, 16, 8)
        button_layout.setSpacing(12)

        button_layout.addStretch()

        copy_btn = QPushButton("复制")
        copy_btn.setFixedSize(90, 32)
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
        """)
        copy_btn.clicked.connect(self._on_copy_clicked)
        button_layout.addWidget(copy_btn)

        frame_layout.addWidget(button_bar)

    def _on_copy_clicked(self):
        from PySide6.QtWidgets import QApplication
        text = self.text_edit.toPlainText()
        QApplication.clipboard().setText(text)
        self.accept()

    @property
    def result_text(self) -> str:
        return self.text_edit.toPlainText()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()


class ModernProgressDialog(QDialog):
    """现代风格的进度对话框"""
    
    def __init__(self, title, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(380)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._drag_pos = None
        self.setup_ui(title, message)
        
    def setup_ui(self, title, message):
        # 外层圆角边框
        self.main_frame = QFrame(self)
        self.main_frame.setObjectName("mainFrame")
        self.main_frame.setStyleSheet("""
            QFrame#mainFrame {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.main_frame)
        
        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)
        
        # 标题栏
        title_bar = QFrame()
        title_bar.setFixedHeight(45)
        title_bar.setStyleSheet("""
            background-color: #FBFBFB;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
            border-bottom: 1px solid #F0F0F0;
        """)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(18, 0, 12, 0)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; color: #333; font-size: 14px;")
        title_layout.addWidget(title_label)
        
        frame_layout.addWidget(title_bar)
        
        # 内容区
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(25, 30, 25, 30)
        content_layout.setSpacing(15)
        
        self.message_label = QLabel(message)
        self.message_label.setStyleSheet("color: #444; font-size: 13px;")
        content_layout.addWidget(self.message_label)
        
        # 进度条
        from PySide6.QtWidgets import QProgressBar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #F0F0F0;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 4px;
            }
        """)
        content_layout.addWidget(self.progress_bar)
        
        self.percent_label = QLabel("0%")
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.percent_label.setStyleSheet("color: #888; font-size: 12px;")
        content_layout.addWidget(self.percent_label)
        
        frame_layout.addWidget(content_widget)

    def set_value(self, value):
        self.progress_bar.setValue(value)
        self.percent_label.setText(f"{value}%")

    def set_message(self, message):
        self.message_label.setText(message)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
