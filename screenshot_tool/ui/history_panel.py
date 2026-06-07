"""
截图历史记录面板
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QMenu,
    QApplication, QGridLayout, QDialog
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QAction, QCursor
import os
from datetime import datetime
import subprocess
import sys
from ui.modern_dialog import ModernMessageBox


class HistoryItemWidget(QFrame):
    """历史记录项控件"""
    
    clicked = Signal(dict)
    open_requested = Signal(dict)
    edit_requested = Signal(dict)
    delete_requested = Signal(dict)
    share_requested = Signal(dict)
    
    def __init__(self, record: dict, parent=None):
        super().__init__(parent)
        self.record = record
        self.setup_ui()
    
    def setup_ui(self):
        self.setFixedHeight(90)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
            }
            QFrame:hover {
                border-color: #0078D7;
                background: #f8fbff;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        
        # 缩略图
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(70, 70)
        self.thumbnail_label.setStyleSheet("""
            QLabel {
                background: #f0f0f0;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        thumbnail_path = self.record.get("thumbnail_path", "")
        if thumbnail_path and os.path.exists(thumbnail_path):
            pixmap = QPixmap(thumbnail_path)
            self.thumbnail_label.setPixmap(pixmap.scaled(
                68, 68, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            self.thumbnail_label.setText("📷")
            self.thumbnail_label.setStyleSheet("""
                QLabel {
                    background: #f0f0f0;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    font-size: 24px;
                }
            """)
        
        layout.addWidget(self.thumbnail_label)
        
        # 信息区域
        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)
        
        # 文件名
        file_name = self.record.get("file_name", "未知")
        name_label = QLabel(file_name)
        name_label.setStyleSheet("font-weight: bold; color: #333; font-size: 12px;")
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)
        
        # 创建时间
        created_at = self.record.get("created_at", "")
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at)
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                time_str = created_at
        else:
            time_str = "未知时间"
        
        time_label = QLabel(f"🕐 {time_str}")
        time_label.setStyleSheet("color: #888; font-size: 10px;")
        info_layout.addWidget(time_label)
        
        # 文件大小
        file_size = self.record.get("file_size", 0)
        if file_size > 0:
            if file_size < 1024:
                size_str = f"{file_size} B"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
        else:
            size_str = "未知大小"
        
        size_label = QLabel(f"📦 {size_str}")
        size_label.setStyleSheet("color: #888; font-size: 10px;")
        info_layout.addWidget(size_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout, 1)
        
        # 操作按钮
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(4)
        
        btn_style = """
            QPushButton {
                background: #f0f0f0;
                border: none;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 10px;
                color: #555;
            }
            QPushButton:hover { background: #e0e0e0; }
        """
        
        open_btn = QPushButton("打开")
        open_btn.setStyleSheet(btn_style)
        open_btn.clicked.connect(lambda: self.open_requested.emit(self.record))
        btn_layout.addWidget(open_btn)
        
        edit_btn = QPushButton("编辑")
        edit_btn.setStyleSheet(btn_style)
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.record))
        btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("删除")
        delete_btn.setStyleSheet(btn_style.replace("#f0f0f0", "#ffe0e0").replace("#e0e0e0", "#ffcccc"))
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.record))
        btn_layout.addWidget(delete_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.record)
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPos())
        super().mousePressEvent(event)
    
    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: white;
                border: 1px solid #ddd;
                padding: 5px;
            }
            QMenu::item {
                padding: 6px 20px;
                color: #333;
            }
            QMenu::item:selected { background: #e8f4fd; }
        """)
        
        open_action = QAction("📂 打开文件位置", menu)
        open_action.triggered.connect(lambda: self.open_requested.emit(self.record))
        menu.addAction(open_action)
        
        edit_action = QAction("✏️ 编辑", menu)
        edit_action.triggered.connect(lambda: self.edit_requested.emit(self.record))
        menu.addAction(edit_action)
        
        copy_action = QAction("📋 复制到剪贴板", menu)
        copy_action.triggered.connect(self._copy_to_clipboard)
        menu.addAction(copy_action)
        
        menu.addSeparator()
        
        delete_action = QAction("🗑️ 删除记录", menu)
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self.record))
        menu.addAction(delete_action)
        
        menu.exec(pos)
    
    def _copy_to_clipboard(self):
        file_path = self.record.get("file_path", "")
        if file_path and os.path.exists(file_path):
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                QApplication.clipboard().setPixmap(pixmap)


class HistoryPanel(QWidget):
    """历史记录面板"""
    
    open_file_requested = Signal(str)  # 请求打开文件
    edit_file_requested = Signal(str)  # 请求编辑文件
    
    def __init__(self, history_manager, parent=None):
        super().__init__(parent)
        self.history_manager = history_manager
        self.setup_ui()
        self.refresh()
    
    def setup_ui(self):
        self.setMinimumWidth(260)
        self.setStyleSheet("""
            HistoryPanel { 
                background: #ffffff; 
                border-left: 1px solid #f0f0f0;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标题栏
        header_layout = QHBoxLayout()
        
        title = QLabel("📷 截图历史")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # 刷新按钮
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(28, 28)
        refresh_btn.setToolTip("刷新")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #e0e0e0;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { background: #d0d0d0; }
        """)
        refresh_btn.clicked.connect(self.refresh)
        header_layout.addWidget(refresh_btn)
        
        # 清空按钮
        clear_btn = QPushButton("🗑️")
        clear_btn.setFixedSize(28, 28)
        clear_btn.setToolTip("清空历史")
        clear_btn.setStyleSheet("""
            QPushButton {
                background: #ffe0e0;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { background: #ffcccc; }
        """)
        clear_btn.clicked.connect(self._clear_history)
        header_layout.addWidget(clear_btn)
        
        layout.addLayout(header_layout)
        
        # 统计信息
        self.stats_label = QLabel("共 0 条记录")
        self.stats_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.stats_label)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #ccc;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover { background: #bbb; }
        """)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 5, 0)
        self.content_layout.setSpacing(8)
        self.content_layout.addStretch()
        
        scroll.setWidget(self.content_widget)
        layout.addWidget(scroll, 1)
    
    def refresh(self):
        """刷新历史记录"""
        # 清空现有项
        while self.content_layout.count() > 1:
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 加载历史记录
        records = self.history_manager.get_all_records()
        self.stats_label.setText(f"共 {len(records)} 条记录")
        
        if not records:
            empty_label = QLabel("暂无历史记录")
            empty_label.setStyleSheet("color: #999; font-size: 12px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_layout.insertWidget(0, empty_label)
        else:
            for record in records:
                item = HistoryItemWidget(record)
                item.open_requested.connect(self._on_open_requested)
                item.edit_requested.connect(self._on_edit_requested)
                item.delete_requested.connect(self._on_delete_requested)
                self.content_layout.insertWidget(self.content_layout.count() - 1, item)
    
    def _on_open_requested(self, record: dict):
        """??????"""
        file_path = record.get("file_path", "")
        if not file_path or not os.path.exists(file_path):
            ModernMessageBox.warning(self, "?????", "???????????")
            return

        if sys.platform == "win32":
            subprocess.run(["explorer", "/select,", os.path.normpath(file_path)], check=False)
        elif sys.platform == "darwin":
            subprocess.run(["open", "-R", file_path], check=False)
        else:
            subprocess.run(["xdg-open", os.path.dirname(file_path)], check=False)

    def _on_edit_requested(self, record: dict):
        """????"""
        file_path = record.get("file_path", "")
        if file_path and os.path.exists(file_path):
            self.edit_file_requested.emit(file_path)
        else:
            ModernMessageBox.warning(self, "?????", "???????????")

    def _on_delete_requested(self, record: dict):
        """删除记录"""
        reply = ModernMessageBox.question(
            self, "确认删除",
            "确定要删除这条历史记录吗？\n（不会删除原文件）",
            yes_text="确定", no_text="取消"
        )
        if reply == QDialog.DialogCode.Accepted:
            self.history_manager.delete_record(record["id"])
            self.refresh()
    
    def _clear_history(self):
        """清空历史"""
        reply = ModernMessageBox.question(
            self, "确认清空",
            "确定要清空所有历史记录吗？\n（不会删除原文件）",
            yes_text="确定", no_text="取消"
        )
        if reply == QDialog.DialogCode.Accepted:
            self.history_manager.clear_history()
            self.refresh()
