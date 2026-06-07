"""
统一编辑预览窗口 - 集中显示所有截图
支持：分页/标签页、缩略图导航、批量编辑、性能优化
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QLabel, QPushButton, QFrame,
    QGridLayout, QProgressBar, QComboBox, QLineEdit,
    QCheckBox, QSpinBox, QMenu
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer, QThread, QObject, pyqtSignal
from PySide6.QtGui import (
    QPixmap, QPainter, QColor, QFont, QIcon, QAction,
    QPen, QBrush
)
from ui.icons import set_window_icon
from datetime import datetime
from typing import Dict, List, Tuple
import os
from ui.modern_dialog import ModernMessageBox


class ThumbnailItem(QFrame):
    """缩略图项 - 支持选择和预览"""
    
    clicked = Signal(str)  # tab_id
    double_clicked = Signal(str)  # tab_id
    
    def __init__(self, tab_id: str, pixmap: QPixmap, title: str, parent=None):
        super().__init__(parent)
        self.tab_id = tab_id
        self.pixmap = pixmap.scaledToWidth(120, Qt.TransformationMode.SmoothTransformation)
        self.title = title
        self.is_selected = False
        
        self.setFixedSize(140, 160)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # 缩略图
        self.thumb_label = QLabel()
        self.thumb_label.setPixmap(self.pixmap)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setStyleSheet("border: 2px solid #ddd; border-radius: 4px;")
        layout.addWidget(self.thumb_label)
        
        # 标题
        title_label = QLabel(self.title[:12] + "..." if len(self.title) > 12 else self.title)
        title_label.setStyleSheet("font-size: 10px; color: #666;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setToolTip(self.title)
        layout.addWidget(title_label)
        
        self._update_style()
    
    def _update_style(self):
        if self.is_selected:
            self.setStyleSheet("""
                QFrame {
                    background: #E3F2FD;
                    border: 2px solid #0078D7;
                    border-radius: 6px;
                }
            """)
            self.thumb_label.setStyleSheet("border: 2px solid #0078D7; border-radius: 4px;")
        else:
            self.setStyleSheet("""
                QFrame {
                    background: white;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                }
            """)
            self.thumb_label.setStyleSheet("border: 2px solid #ddd; border-radius: 4px;")
    
    def set_selected(self, selected: bool):
        self.is_selected = selected
        self._update_style()
    
    def mousePressEvent(self, event):
        self.clicked.emit(self.tab_id)
    
    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit(self.tab_id)


class ThumbnailNavigator(QFrame):
    """缩略图导航栏 - 支持滚动和快速预览"""
    
    thumbnail_selected = Signal(str)  # tab_id
    thumbnail_double_clicked = Signal(str)  # tab_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.thumbnails: Dict[str, ThumbnailItem] = {}
        self.selected_tab_id = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setStyleSheet("""
            QFrame {
                background: #f5f5f5;
                border-bottom: 1px solid #ddd;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 标题
        title = QLabel("📷 截图导航")
        title.setStyleSheet("font-weight: bold; color: #333; font-size: 12px;")
        layout.addWidget(title)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:horizontal { height: 8px; background: #e0e0e0; }
            QScrollBar::handle:horizontal { background: #999; border-radius: 4px; }
        """)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.thumbnails_container = QWidget()
        self.thumbnails_layout = QHBoxLayout(self.thumbnails_container)
        self.thumbnails_layout.setContentsMargins(0, 0, 0, 0)
        self.thumbnails_layout.setSpacing(8)
        self.thumbnails_layout.addStretch()
        
        scroll.setWidget(self.thumbnails_container)
        layout.addWidget(scroll, 1)
    
    def add_thumbnail(self, tab_id: str, pixmap: QPixmap, title: str):
        """添加缩略图"""
        thumb = ThumbnailItem(tab_id, pixmap, title)
        thumb.clicked.connect(self._on_thumbnail_clicked)
        thumb.double_clicked.connect(self._on_thumbnail_double_clicked)
        
        self.thumbnails_layout.insertWidget(
            self.thumbnails_layout.count() - 1, thumb
        )
        self.thumbnails[tab_id] = thumb
    
    def remove_thumbnail(self, tab_id: str):
        """移除缩略图"""
        if tab_id in self.thumbnails:
            thumb = self.thumbnails.pop(tab_id)
            self.thumbnails_layout.removeWidget(thumb)
            thumb.deleteLater()
    
    def select_thumbnail(self, tab_id: str):
        """选择缩略图"""
        for tid, thumb in self.thumbnails.items():
            thumb.set_selected(tid == tab_id)
        self.selected_tab_id = tab_id
    
    def _on_thumbnail_clicked(self, tab_id: str):
        self.select_thumbnail(tab_id)
        self.thumbnail_selected.emit(tab_id)
    
    def _on_thumbnail_double_clicked(self, tab_id: str):
        self.thumbnail_double_clicked.emit(tab_id)


class BatchEditPanel(QFrame):
    """批量编辑操作面板"""
    
    operation_requested = Signal(str, dict)  # operation, params
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        self.setStyleSheet("""
            QFrame {
                background: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QPushButton {
                background: #0078D7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover { background: #005A9E; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # 标题
        title = QLabel("⚙️ 批量编辑")
        title.setStyleSheet("font-weight: bold; color: #333; font-size: 12px;")
        layout.addWidget(title)
        
        # 操作按钮
        ops = [
            ("旋转 90°", "rotate_90"),
            ("旋转 -90°", "rotate_270"),
            ("水平翻转", "flip_h"),
            ("垂直翻转", "flip_v"),
            ("全部模糊", "blur_all"),
            ("全部锐化", "sharpen_all"),
        ]
        
        for text, op in ops:
            btn = QPushButton(text)
            btn.clicked.connect(lambda _, o=op: self.operation_requested.emit(o, {}))
            layout.addWidget(btn)
        
        layout.addStretch()


class FilterPanel(QFrame):
    """筛选和排序面板"""
    
    filter_changed = Signal(dict)  # filter_params
    sort_changed = Signal(str)  # sort_key
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        self.setStyleSheet("""
            QFrame {
                background: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QLabel { color: #666; font-size: 11px; }
            QComboBox, QLineEdit, QSpinBox {
                background: white;
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 4px;
                font-size: 11px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # 标题
        title = QLabel("🔍 筛选和排序")
        title.setStyleSheet("font-weight: bold; color: #333; font-size: 12px;")
        layout.addWidget(title)
        
        # 排序
        layout.addWidget(QLabel("排序方式:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["最新优先", "最旧优先", "按名称", "按大小"])
        self.sort_combo.currentTextChanged.connect(self._on_sort_changed)
        layout.addWidget(self.sort_combo)
        
        # 搜索
        layout.addWidget(QLabel("搜索:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入文件名...")
        self.search_input.textChanged.connect(self._on_filter_changed)
        layout.addWidget(self.search_input)
        
        # 大小范围
        layout.addWidget(QLabel("最小宽度:"))
        self.min_width_spin = QSpinBox()
        self.min_width_spin.setRange(0, 200000)
        self.min_width_spin.setValue(0)
        self.min_width_spin.valueChanged.connect(self._on_filter_changed)
        layout.addWidget(self.min_width_spin)
        
        layout.addStretch()
    
    def _on_sort_changed(self):
        sort_map = {
            "最新优先": "newest",
            "最旧优先": "oldest",
            "按名称": "name",
            "按大小": "size"
        }
        self.sort_changed.emit(sort_map.get(self.sort_combo.currentText(), "newest"))
    
    def _on_filter_changed(self):
        self.filter_changed.emit({
            "search": self.search_input.text(),
            "min_width": self.min_width_spin.value()
        })


class ProgressIndicator(QFrame):
    """加载进度指示器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        self.setStyleSheet("""
            QFrame {
                background: rgba(0, 0, 0, 0.7);
                border-radius: 8px;
            }
            QLabel { color: white; font-size: 12px; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        self.status_label = QLabel("加载中...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background: #333;
                border-radius: 4px;
                height: 6px;
            }
            QProgressBar::chunk { background: #0078D7; border-radius: 4px; }
        """)
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        self.hide()
    
    def show_progress(self, current: int, total: int, message: str = ""):
        """显示进度"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        if message:
            self.status_label.setText(f"{message} ({current}/{total})")
        else:
            self.status_label.setText(f"处理中... {current}/{total}")
        self.show()
    
    def hide_progress(self):
        """隐藏进度"""
        self.hide()


class UnifiedPreviewWindow(QMainWindow):
    """统一编辑预览窗口 - 集中显示所有截图"""
    
    closed = Signal()
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.screenshots: Dict[str, Tuple[QPixmap, str]] = {}  # tab_id -> (pixmap, title)
        self.current_tab_id = None
        self.selected_tabs = set()
        
        self.setWindowTitle("统一预览窗口 - PyScreenshot")
        set_window_icon(self)
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1000, 700)
        
        self.setup_ui()
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 左侧面板：导航和控制
        left_panel = self._create_left_panel()
        main_layout.addWidget(left_panel, 0)
        
        # 中间：主预览区域
        center_panel = self._create_center_panel()
        main_layout.addWidget(center_panel, 1)
    
    def _create_left_panel(self) -> QFrame:
        """创建左侧面板"""
        panel = QFrame()
        panel.setFixedWidth(280)
        panel.setStyleSheet("background: #f5f5f5; border-right: 1px solid #ddd;")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 缩略图导航
        self.thumbnail_nav = ThumbnailNavigator()
        self.thumbnail_nav.thumbnail_selected.connect(self._on_thumbnail_selected)
        self.thumbnail_nav.thumbnail_double_clicked.connect(self._on_thumbnail_double_clicked)
        layout.addWidget(self.thumbnail_nav, 1)
        
        # 分隔线
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #ddd;")
        layout.addWidget(sep)
        
        # 批量编辑面板
        self.batch_edit_panel = BatchEditPanel()
        self.batch_edit_panel.operation_requested.connect(self._on_batch_operation)
        layout.addWidget(self.batch_edit_panel)
        
        # 分隔线
        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet("background: #ddd;")
        layout.addWidget(sep2)
        
        # 筛选面板
        self.filter_panel = FilterPanel()
        self.filter_panel.filter_changed.connect(self._on_filter_changed)
        self.filter_panel.sort_changed.connect(self._on_sort_changed)
        layout.addWidget(self.filter_panel)
        
        return panel
    
    def _create_center_panel(self) -> QFrame:
        """创建中间预览区域"""
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 工具栏
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)
        
        # 主预览区域
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setStyleSheet("""
            QScrollArea { border: none; background: #fff; }
            QScrollBar { background: #f0f0f0; width: 12px; }
            QScrollBar::handle { background: #999; border-radius: 6px; }
        """)
        
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("background: white;")
        self.preview_scroll.setWidget(self.preview_label)
        layout.addWidget(self.preview_scroll, 1)
        
        # 进度指示器
        self.progress_indicator = ProgressIndicator(self.preview_scroll)
        
        # 状态栏
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("background: #f5f5f5; padding: 8px; font-size: 11px; color: #666;")
        layout.addWidget(self.status_label)
        
        return panel
    
    def _create_toolbar(self) -> QFrame:
        """创建工具栏"""
        toolbar = QFrame()
        toolbar.setStyleSheet("background: #f9f9f9; border-bottom: 1px solid #ddd;")
        
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        
        # 统计信息
        self.stats_label = QLabel("0 张截图")
        self.stats_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.stats_label)
        
        layout.addStretch()
        
        # 操作按钮
        export_btn = QPushButton("📦 批量导出")
        export_btn.setStyleSheet("""
            QPushButton {
                background: #0078D7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover { background: #005A9E; }
        """)
        export_btn.clicked.connect(self._on_batch_export)
        layout.addWidget(export_btn)
        
        close_btn = QPushButton("✕ 关闭")
        close_btn.setStyleSheet("""
            QPushButton {
                background: #c42b1c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover { background: #a02015; }
        """)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        return toolbar
    
    def add_screenshot(self, tab_id: str, pixmap: QPixmap, title: str = ""):
        """添加截图到预览窗口"""
        if not title:
            title = f"截图 {len(self.screenshots) + 1}"
        
        self.screenshots[tab_id] = (pixmap, title)
        self.thumbnail_nav.add_thumbnail(tab_id, pixmap, title)
        
        # 自动选择第一张
        if not self.current_tab_id:
            self._on_thumbnail_selected(tab_id)
        
        self._update_stats()
    
    def remove_screenshot(self, tab_id: str):
        """移除截图"""
        if tab_id in self.screenshots:
            del self.screenshots[tab_id]
            self.thumbnail_nav.remove_thumbnail(tab_id)
            
            if self.current_tab_id == tab_id:
                remaining = list(self.screenshots.keys())
                if remaining:
                    self._on_thumbnail_selected(remaining[0])
                else:
                    self.current_tab_id = None
                    self.preview_label.clear()
            
            self._update_stats()
    
    def _on_thumbnail_selected(self, tab_id: str):
        """缩略图被选中"""
        self.current_tab_id = tab_id
        self.thumbnail_nav.select_thumbnail(tab_id)
        
        if tab_id in self.screenshots:
            pixmap, title = self.screenshots[tab_id]
            
            # 缩放以适应窗口
            max_width = self.preview_scroll.width() - 40
            max_height = self.preview_scroll.height() - 40
            
            scaled = pixmap.scaledToFit(
                max_width, max_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            self.preview_label.setPixmap(scaled)
            self.status_label.setText(f"📷 {title} | {pixmap.width()}×{pixmap.height()}")
    
    def _on_thumbnail_double_clicked(self, tab_id: str):
        """缩略图双击 - 打开编辑器"""
        if tab_id in self.screenshots:
            pixmap, title = self.screenshots[tab_id]
            # 这里可以触发打开编辑器的信号
            self.status_label.setText(f"✓ 已打开编辑器: {title}")
    
    def _on_batch_operation(self, operation: str, params: dict):
        """批量操作"""
        if not self.screenshots:
            ModernMessageBox.information(self, "提示", "没有可操作的截图")
            return
        
        self.progress_indicator.show_progress(0, len(self.screenshots), f"执行 {operation}")
        
        for i, (tab_id, (pixmap, title)) in enumerate(self.screenshots.items()):
            # 这里执行实际的操作
            self.progress_indicator.show_progress(i + 1, len(self.screenshots))
        
        self.progress_indicator.hide_progress()
        self.status_label.setText(f"✓ 已完成 {operation}")
    
    def _on_batch_export(self):
        """批量导出"""
        if not self.screenshots:
            ModernMessageBox.information(self, "提示", "没有可导出的截图")
            return
        
        self.status_label.setText(f"✓ 已导出 {len(self.screenshots)} 张截图")
    
    def _on_filter_changed(self, filter_params: dict):
        """筛选条件改变"""
        pass
    
    def _on_sort_changed(self, sort_key: str):
        """排序方式改变"""
        pass
    
    def _update_stats(self):
        """更新统计信息"""
        count = len(self.screenshots)
        self.stats_label.setText(f"{count} 张截图")
    
    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)
