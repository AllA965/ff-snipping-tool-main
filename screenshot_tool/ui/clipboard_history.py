"""
剪贴板历史面板
支持粘贴历史记录功能
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap

from core.social_share import get_social_manager
from ui.modern_dialog import ModernMessageBox


class ClipboardHistoryItem(QFrame):
    """剪贴板历史项"""
    
    clicked = Signal(int)  # 索引
    
    def __init__(self, index: int, thumbnail: QPixmap, timestamp, parent=None):
        super().__init__(parent)
        self.index = index
        self.setFixedSize(120, 100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui(thumbnail, timestamp)
    
    def _setup_ui(self, thumbnail: QPixmap, timestamp):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # 缩略图
        thumb_label = QLabel()
        thumb_label.setPixmap(thumbnail.scaled(100, 70, Qt.AspectRatioMode.KeepAspectRatio))
        thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(thumb_label)
        
        # 时间
        time_label = QLabel(timestamp.strftime("%H:%M:%S"))
        time_label.setStyleSheet("color: #666; font-size: 10px;")
        time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(time_label)
        
        self.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QFrame:hover {
                border-color: #0078D7;
                background: #f0f7ff;
            }
        """)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)
        super().mousePressEvent(event)


class ClipboardHistoryPanel(QWidget):
    """剪贴板历史面板"""
    
    paste_requested = Signal(QPixmap)  # 请求粘贴
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.social_manager = get_social_manager()
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 标题栏
        header = QHBoxLayout()
        
        title = QLabel("剪贴板历史")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        header.addWidget(title)
        
        header.addStretch()
        
        clear_btn = QPushButton("清空")
        clear_btn.setStyleSheet("""
            QPushButton {
                background: #e0e0e0;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
                color: #333;
            }
            QPushButton:hover { background: #d0d0d0; }
        """)
        clear_btn.clicked.connect(self._clear_history)
        header.addWidget(clear_btn)
        
        layout.addLayout(header)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.content = QWidget()
        self.grid = QGridLayout(self.content)
        self.grid.setSpacing(8)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        scroll.setWidget(self.content)
        layout.addWidget(scroll)
        
        # 提示
        self.empty_label = QLabel("暂无历史记录\n复制图像后会自动记录")
        self.empty_label.setStyleSheet("color: #999; font-size: 12px;")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty_label)
        
        self.refresh()
    
    def refresh(self):
        """刷新历史列表"""
        # 清空现有项
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        history = self.social_manager.get_clipboard_history()
        
        if not history:
            self.empty_label.show()
            return
        
        self.empty_label.hide()
        
        cols = 3
        for i, item in enumerate(history):
            row = i // cols
            col = i % cols
            
            history_item = ClipboardHistoryItem(
                i, item['thumbnail'], item['timestamp']
            )
            history_item.clicked.connect(self._on_item_clicked)
            self.grid.addWidget(history_item, row, col)
    
    def _on_item_clicked(self, index: int):
        """历史项点击"""
        pixmap = self.social_manager.paste_from_history(index)
        if pixmap:
            self.paste_requested.emit(pixmap)
    
    def _clear_history(self):
        """清空历史记录"""
        reply = ModernMessageBox.question(
            self, "确认清空",
            "确定要清空所有剪贴板历史记录吗？",
            yes_text="确定", no_text="取消"
        )
        
        if reply == QDialog.DialogCode.Accepted:
            self.social_manager.clear_clipboard_history()
            self.refresh()


class ClipboardHistoryDialog(QDialog):
    """剪贴板历史对话框"""
    
    paste_requested = Signal(QPixmap)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("剪贴板历史")
        self.setFixedSize(450, 400)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.panel = ClipboardHistoryPanel()
        self.panel.paste_requested.connect(self._on_paste)
        layout.addWidget(self.panel)
        
        self.setStyleSheet("QDialog { background: #f5f5f5; }")
    
    def _on_paste(self, pixmap: QPixmap):
        """粘贴请求"""
        self.paste_requested.emit(pixmap)
        self.accept()
