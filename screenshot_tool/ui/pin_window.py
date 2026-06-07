"""
固定截图窗口 - 将截图固定在桌面上
"""
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QMenu
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap, QAction


from ui.icons import set_window_icon


class PinWindow(QWidget):
    """固定截图窗口"""
    
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.pixmap = pixmap
        self.drag_pos = None
        self.setup_ui()
        set_window_icon(self)
    
    def setup_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        
        self.label = QLabel()
        self.label.setPixmap(self.pixmap)
        self.label.setStyleSheet("""
            QLabel {
                border: 2px solid #0078d7;
                border-radius: 4px;
                background: white;
            }
        """)
        layout.addWidget(self.label)
        
        self.adjustSize()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
    
    def mouseMoveEvent(self, event):
        if self.drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
    
    def mouseReleaseEvent(self, event):
        self.drag_pos = None
    
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: white; border: 1px solid #ccc; padding: 4px; }
            QMenu::item { padding: 6px 20px; }
            QMenu::item:selected { background: #e5f3ff; }
        """)
        
        copy_action = QAction("复制", self)
        copy_action.triggered.connect(self._copy)
        menu.addAction(copy_action)
        
        save_action = QAction("保存", self)
        save_action.triggered.connect(self._save)
        menu.addAction(save_action)
        
        menu.addSeparator()
        
        close_action = QAction("关闭", self)
        close_action.triggered.connect(self.close)
        menu.addAction(close_action)
        
        menu.exec(event.globalPos())
    
    def _copy(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setPixmap(self.pixmap)
    
    def _save(self):
        from PySide6.QtWidgets import QFileDialog
        from datetime import datetime
        name = f"pinned_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path, _ = QFileDialog.getSaveFileName(self, "保存", name, "PNG (*.png)")
        if path:
            self.pixmap.save(path)
