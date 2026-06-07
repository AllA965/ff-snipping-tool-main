"""
标签页管理器 - PicPick 风格，支持缩略图显示
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QScrollArea, QFrame, QLabel, QMenu, QDialog
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QPixmap, QColor, QPainter, QPen, QAction, QImage
from ui.modern_dialog import ModernMessageBox
from datetime import datetime


class TabButton(QFrame):
    """标签按钮 - PicPick 风格（显示缩略图和关闭按钮）"""
    
    close_requested = Signal(str)  # tab_id
    activated = Signal(str)  # tab_id
    
    def __init__(self, tab_id: str, title: str, pixmap=None, 
                 is_modified: bool = False, parent=None):
        super().__init__(parent)
        self.tab_id = tab_id
        self.title = title
        self.is_modified = is_modified
        self.is_active = False
        self.thumbnail = None
        
        # PicPick 风格标签 - 带缩略图
        self.setFixedHeight(26)
        self.setMinimumWidth(130)
        self.setMaximumWidth(200)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # 布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 2, 2)
        layout.setSpacing(4)
        
        # 缩略图标签
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(18, 18)
        self.thumb_label.setStyleSheet("border: 1px solid #b4b4b4; background: white;")
        layout.addWidget(self.thumb_label)
        
        # 标题标签
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(self.title_label, 1)
        
        # 关闭按钮
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(16, 16)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 3px;
                color: #999;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #e81123;
                color: white;
            }
        """)
        self.close_btn.clicked.connect(lambda: self.close_requested.emit(self.tab_id))
        layout.addWidget(self.close_btn)
        
        # 生成缩略图
        if pixmap and not pixmap.isNull():
            self.set_thumbnail(pixmap)
        
        self._update_style()
    
    def set_thumbnail(self, pixmap):
        """设置缩略图"""
        if pixmap and not pixmap.isNull():
            # 缩略图生成：如果是 QImage，先缩放再转换，避免超大图转换 QPixmap 失败
            if isinstance(pixmap, QImage):
                scaled_img = pixmap.scaled(
                    16, 16, 
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.thumbnail = QPixmap.fromImage(scaled_img)
            else:
                self.thumbnail = pixmap.scaled(
                    16, 16, 
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            self.thumb_label.setPixmap(self.thumbnail)
    
    def _update_style(self):
        """PicPick 风格标签"""
        if self.is_active:
            self.setStyleSheet("""
                QFrame {
                    background: white;
                    border: 1px solid #d0d0d0;
                    border-bottom: 2px solid #0078D7;
                    border-radius: 0px;
                }
                QFrame:hover { background: #f8f8f8; }
                QLabel { color: #333; font-size: 12px; border: none; background: transparent; }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background: #f0f0f0;
                    border: 1px solid #d8d8d8;
                    border-bottom: 1px solid #d0d0d0;
                    border-radius: 0px;
                }
                QFrame:hover { background: #e8e8e8; }
                QLabel { color: #666; font-size: 12px; border: none; background: transparent; }
            """)
    
    def mousePressEvent(self, event):
        """点击标签时激活"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.activated.emit(self.tab_id)
        super().mousePressEvent(event)
    
    def set_active(self, active: bool):
        if self.is_active == active:
            return
        self.is_active = active
        self._update_style()
    
    def set_modified(self, modified: bool):
        self.is_modified = modified
        # 更新标题显示修改标记
        display_title = self.title
        if len(display_title) > 15:
            display_title = display_title[:12] + "..."
        if modified:
            display_title = "● " + display_title
        self.title_label.setText(display_title)
    
    def set_title(self, title: str):
        self.title = title
        display_title = title
        if len(display_title) > 15:
            display_title = display_title[:12] + "..."
        if self.is_modified:
            display_title = "● " + display_title
        self.title_label.setText(display_title)
    
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: white; border: 1px solid #ddd; padding: 5px; }
            QMenu::item { padding: 6px 20px; border-radius: 3px; }
            QMenu::item:selected { background: #e5f3ff; }
        """)
        
        close_action = QAction("关闭", menu)
        close_action.triggered.connect(lambda: self.close_requested.emit(self.tab_id))
        menu.addAction(close_action)
        
        close_others = QAction("关闭其他", menu)
        close_others.triggered.connect(lambda: self._close_others())
        menu.addAction(close_others)
        
        menu.exec(event.globalPos())
    
    def _close_others(self):
        parent = self.parent()
        if hasattr(parent, 'close_other_tabs'):
            parent.close_other_tabs(self.tab_id)


class TabData:
    """标签页数据"""
    
    def __init__(self, tab_id: str, pixmap: QPixmap, file_path: str = None):
        self.tab_id = tab_id
        self.original_pixmap = pixmap.copy()
        self.current_pixmap = pixmap.copy()
        self.file_path = file_path
        self.is_modified = False
        self.created_at = datetime.now()
        
        if file_path:
            import os
            self.title = os.path.basename(file_path)
        else:
            self.title = self.created_at.strftime("%Y-%m-%d %H:%M:%S")


class TabBar(QWidget):
    """标签栏 - PicPick 风格，带缩略图"""
    
    tab_activated = Signal(str)
    tab_close_requested = Signal(str)
    new_tab_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tabs = {}
        self.active_tab_id = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setFixedHeight(32)
        self.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #f8f8f8, stop:1 #e8e8e8);
            border-bottom: 1px solid #d0d0d0;
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 0)
        layout.setSpacing(2)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setFixedHeight(28)
        
        self.tabs_container = QWidget()
        self.tabs_layout = QHBoxLayout(self.tabs_container)
        self.tabs_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs_layout.setSpacing(2)
        
        # 新建按钮 - 现在放在 tabs_layout 中，紧跟标签页
        self.new_btn = QPushButton("+")
        self.new_btn.setFixedSize(24, 24)
        self.new_btn.setToolTip("新建")
        self.new_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #666;
                border: 1px solid transparent; border-radius: 3px;
                font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background: #e5f3ff; border-color: #cce8ff; color: #0078D7; }
        """)
        self.new_btn.clicked.connect(self.new_tab_requested.emit)
        
        # 先添加伸缩空间
        self.tabs_layout.addStretch()
        # 将新建按钮插入到伸缩空间之前
        self.tabs_layout.insertWidget(0, self.new_btn)
        
        scroll.setWidget(self.tabs_container)
        layout.addWidget(scroll, 1)
    
    def add_tab(self, tab_id: str, title: str, pixmap: QPixmap = None, 
                is_modified: bool = False) -> TabButton:
        btn = TabButton(tab_id, title, pixmap, is_modified)
        btn.activated.connect(self._on_tab_activated)
        btn.close_requested.connect(self._on_tab_close)
        
        # 始终在新建按钮 (+) 之前插入新标签页
        new_btn_index = self.tabs_layout.indexOf(self.new_btn)
        self.tabs_layout.insertWidget(new_btn_index, btn)
        self.tabs[tab_id] = btn
        return btn
    
    def remove_tab(self, tab_id: str):
        if tab_id in self.tabs:
            btn = self.tabs.pop(tab_id)
            self.tabs_layout.removeWidget(btn)
            btn.deleteLater()
    
    def set_active_tab(self, tab_id: str):
        self.active_tab_id = tab_id
        for tid, btn in self.tabs.items():
            btn.set_active(tid == tab_id)
    
    def update_tab_thumbnail(self, tab_id: str, pixmap: QPixmap):
        if tab_id in self.tabs:
            self.tabs[tab_id].set_thumbnail(pixmap)
    
    def update_tab_title(self, tab_id: str, title: str):
        if tab_id in self.tabs:
            self.tabs[tab_id].set_title(title)
    
    def update_tab_modified(self, tab_id: str, modified: bool):
        if tab_id in self.tabs:
            self.tabs[tab_id].set_modified(modified)
    
    def get_tab_ids(self) -> list:
        return list(self.tabs.keys())
    
    def _on_tab_activated(self, tab_id: str):
        self.set_active_tab(tab_id)
        self.tab_activated.emit(tab_id)
    
    def _on_tab_close(self, tab_id: str):
        self.tab_close_requested.emit(tab_id)
    
    def close_other_tabs(self, keep_tab_id: str):
        for tab_id in list(self.tabs.keys()):
            if tab_id != keep_tab_id:
                self.tab_close_requested.emit(tab_id)


class TabManager(QWidget):
    """标签页管理器"""
    
    current_tab_changed = Signal(str)
    tab_closed = Signal(str)
    all_tabs_closed = Signal()
    new_tab_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tabs_data = {}
        self.current_tab_id = None
        self._tab_counter = 0
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.tab_bar = TabBar()
        self.tab_bar.tab_activated.connect(self._on_tab_activated)
        self.tab_bar.tab_close_requested.connect(self._on_tab_close)
        self.tab_bar.new_tab_requested.connect(self.new_tab_requested.emit)
        layout.addWidget(self.tab_bar)
    
    def add_tab(self, pixmap: QPixmap, file_path: str = None, title: str = None) -> str:
        self._tab_counter += 1
        tab_id = f"tab_{self._tab_counter}"
        
        tab_data = TabData(tab_id, pixmap, file_path)
        if title:
            tab_data.title = title
        
        self.tabs_data[tab_id] = tab_data
        self.tab_bar.add_tab(tab_id, tab_data.title, pixmap)
        self.set_current_tab(tab_id)
        
        return tab_id
    
    def remove_tab(self, tab_id: str, force: bool = False) -> bool:
        if tab_id not in self.tabs_data:
            return False
        
        tab_data = self.tabs_data[tab_id]
        
        if tab_data.is_modified and not force:
            reply = ModernMessageBox.question(
                self, "未保存的更改",
                f"'{tab_data.title}' 有未保存的更改，确定要关闭吗？",
                yes_text="保存", no_text="不保存", cancel_text="取消"
            )
            if reply == 2:  # Cancel
                return False
        
        del self.tabs_data[tab_id]
        self.tab_bar.remove_tab(tab_id)
        
        if self.current_tab_id == tab_id:
            remaining = self.tab_bar.get_tab_ids()
            if remaining:
                self.set_current_tab(remaining[-1])
            else:
                self.current_tab_id = None
                self.all_tabs_closed.emit()
        
        self.tab_closed.emit(tab_id)
        return True
    
    def set_current_tab(self, tab_id: str):
        if tab_id in self.tabs_data:
            self.current_tab_id = tab_id
            self.tab_bar.set_active_tab(tab_id)
            self.current_tab_changed.emit(tab_id)
    
    def get_current_tab_data(self) -> TabData:
        if self.current_tab_id:
            return self.tabs_data.get(self.current_tab_id)
        return None
    
    def get_tab_data(self, tab_id: str) -> TabData:
        return self.tabs_data.get(tab_id)
    
    def update_tab_pixmap(self, tab_id: str, pixmap: QPixmap):
        if tab_id in self.tabs_data:
            self.tabs_data[tab_id].current_pixmap = pixmap.copy()
            self.tabs_data[tab_id].is_modified = True
            self.tab_bar.update_tab_modified(tab_id, True)
            self.tab_bar.update_tab_thumbnail(tab_id, pixmap)
    
    def mark_tab_saved(self, tab_id: str, file_path: str = None):
        if tab_id in self.tabs_data:
            tab_data = self.tabs_data[tab_id]
            tab_data.is_modified = False
            if file_path:
                tab_data.file_path = file_path
                import os
                tab_data.title = os.path.basename(file_path)
                self.tab_bar.update_tab_title(tab_id, tab_data.title)
            self.tab_bar.update_tab_modified(tab_id, False)
    
    def get_all_tabs_data(self) -> list:
        return list(self.tabs_data.values())
    
    def get_tab_count(self) -> int:
        return len(self.tabs_data)
    
    def has_unsaved_tabs(self) -> bool:
        return any(td.is_modified for td in self.tabs_data.values())
    
    def _on_tab_activated(self, tab_id: str):
        self.set_current_tab(tab_id)
    
    def _on_tab_close(self, tab_id: str):
        self.remove_tab(tab_id)
