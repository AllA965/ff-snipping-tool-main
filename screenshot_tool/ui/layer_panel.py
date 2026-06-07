"""
图层面板UI - 完整实现
支持：图层列表、拖拽排序、透明度控制、对齐工具
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSlider, QSpinBox, QLineEdit,
    QMenu, QToolButton, QListWidget, QListWidgetItem,
    QAbstractItemView, QSizePolicy, QToolTip, QFileDialog
)
import os
from PySide6.QtCore import Qt, Signal, QSize, QMimeData, QPoint, QTimer
from PySide6.QtGui import QPixmap, QPainter, QColor, QDrag, QCursor, QIcon
from ui.layer_manager import LayerManager, Layer
from ui.modern_dialog import ModernMessageBox
from typing import Optional


class LayerItemWidget(QFrame):
    """单个图层项的Widget"""
    
    visibility_changed = Signal(int, bool)
    lock_changed = Signal(int, bool)
    selected = Signal(int)
    double_clicked = Signal(int)
    
    def __init__(self, layer: Layer, index: int, is_active: bool = False, parent=None):
        super().__init__(parent)
        self.layer = layer
        self.index = index
        self.is_active = is_active
        self._editing_name = False
        self.setup_ui()
        self.update_style()
    
    def setup_ui(self):
        self.setFixedHeight(64)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)
        
        # 可见性按钮
        self.visibility_btn = QToolButton()
        self.visibility_btn.setFixedSize(30, 30)
        self.visibility_btn.setCheckable(True)
        self.visibility_btn.setChecked(self.layer.visible)
        self.visibility_btn.setText("👁" if self.layer.visible else "○")
        self.visibility_btn.setToolTip("显示/隐藏图层")
        self.visibility_btn.clicked.connect(self._on_visibility_clicked)
        self.visibility_btn.setStyleSheet("""
            QToolButton { 
                border: 1px solid #d1d5db; 
                background: #f9fafb; 
                border-radius: 6px;
                font-family: "Segoe UI Emoji", "Microsoft YaHei UI", "Segoe UI", "Arial";
                font-size: 16px;
                color: #4b5563;
                padding: 0px;
            }
            QToolButton:checked { 
                color: #2563eb; 
                background: #dbeafe;
                border-color: #3b82f6;
            }
            QToolButton:hover { 
                background: #f3f4f6; 
                border-color: #9ca3af;
            }
        """)
        layout.addWidget(self.visibility_btn)
        
        # 缩略图预览容器
        thumb_container = QFrame()
        thumb_container.setFixedSize(44, 44)
        thumb_container.setStyleSheet("""
            QFrame {
                border: 1px solid #ddd;
                background: #fff;
                border-radius: 4px;
            }
        """)
        thumb_layout = QHBoxLayout(thumb_container)
        thumb_layout.setContentsMargins(1, 1, 1, 1)
        
        self.thumbnail = QLabel()
        self.thumbnail.setFixedSize(40, 40)
        self.thumbnail.setScaledContents(True)
        self.update_thumbnail()
        thumb_layout.addWidget(self.thumbnail)
        layout.addWidget(thumb_container)
        
        # 名称和信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setContentsMargins(0, 4, 0, 4)
        
        # 名称（可编辑）
        self.name_edit = QLineEdit(self.layer.name)
        self.name_edit.setReadOnly(True)
        self.name_edit.setStyleSheet("""
            QLineEdit { 
                border: none; 
                background: transparent; 
                font-size: 12px;
                font-weight: 600;
                color: #2c3e50;
            }
            QLineEdit:focus { 
                background: white; 
                border: 1px solid #0078d7;
                border-radius: 4px;
                padding: 0 4px;
            }
        """)
        self.name_edit.editingFinished.connect(self._on_name_edited)
        info_layout.addWidget(self.name_edit)
        
        # 透明度显示
        self.opacity_label = QLabel(f"透明度: {self.layer.opacity}%")
        self.opacity_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        info_layout.addWidget(self.opacity_label)
        
        layout.addLayout(info_layout, 1)
        
        # 锁定按钮
        self.lock_btn = QToolButton()
        self.lock_btn.setFixedSize(30, 30)
        self.lock_btn.setCheckable(True)
        self.lock_btn.setChecked(self.layer.locked)
        self.lock_btn.setText("🔒" if self.layer.locked else "🔓")
        self.lock_btn.setToolTip("锁定/解锁图层")
        self.lock_btn.clicked.connect(self._on_lock_clicked)
        self.lock_btn.setStyleSheet("""
            QToolButton { 
                border: 1px solid #d1d5db; 
                background: #f9fafb; 
                border-radius: 6px;
                font-family: "Segoe UI Emoji", "Microsoft YaHei UI", "Segoe UI", "Arial";
                font-size: 15px;
                color: #4b5563;
                padding: 0px;
            }
            QToolButton:checked { 
                color: #ef4444; 
                background: #fef2f2;
                border-color: #fecaca;
            }
            QToolButton:hover { 
                background: #f3f4f6; 
                border-color: #9ca3af;
            }
        """)
        layout.addWidget(self.lock_btn)
    
    def update_style(self):
        # 设置 ObjectName 以使用精准的选择器，避免样式污染子控件
        self.setObjectName("LayerItemWidget")
        if self.is_active:
            self.setStyleSheet("""
                QFrame#LayerItemWidget {
                    background: #eff6ff;
                    border: 1px solid #3b82f6;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#LayerItemWidget {
                    background: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                }
                QFrame#LayerItemWidget:hover {
                    background: #f8fafc;
                    border-color: #cbd5e1;
                }
            """)
    
    def update_thumbnail(self):
        thumb = self.layer.get_thumbnail(38)
        self.thumbnail.setPixmap(thumb)
    
    def set_active(self, active: bool):
        self.is_active = active
        self.update_style()
    
    def _on_visibility_clicked(self):
        self.layer.visible = self.visibility_btn.isChecked()
        self.visibility_btn.setText("👁" if self.layer.visible else "○")
        self.visibility_changed.emit(self.index, self.layer.visible)
    
    def _on_lock_clicked(self):
        self.layer.locked = self.lock_btn.isChecked()
        self.lock_btn.setText("🔒" if self.layer.locked else "🔓")
        self.lock_changed.emit(self.index, self.layer.locked)
    
    def _on_name_edited(self):
        new_name = self.name_edit.text().strip()
        if new_name and new_name != self.layer.name:
            self.layer.name = new_name
        self.name_edit.setReadOnly(True)
        self._editing_name = False
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.index)
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 双击编辑名称
            self.name_edit.setReadOnly(False)
            self.name_edit.setFocus()
            self.name_edit.selectAll()
            self._editing_name = True
        super().mouseDoubleClickEvent(event)


class LayerListWidget(QScrollArea):
    """图层列表Widget - 支持拖拽排序"""
    
    layer_selected = Signal(int)
    layer_moved = Signal(int, int)
    visibility_changed = Signal(int, bool)
    lock_changed = Signal(int, bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layer_items: list[LayerItemWidget] = []
        self.drag_start_index = -1
        self.setup_ui()
    
    def setup_ui(self):
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QScrollArea { 
                border: none; 
                background: #f8f9fa; 
            }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: #cfd8dc;
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #b0bec5;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(6, 6, 6, 6)
        self.container_layout.setSpacing(6)
        self.container_layout.addStretch()
        
        self.setWidget(self.container)
    
    def update_layers(self, layers: list[Layer], active_index: int):
        """更新图层列表"""
        # 清除现有项
        for item in self.layer_items:
            item.deleteLater()
        self.layer_items.clear()
        
        # 从上到下显示（最上层的图层在列表顶部）
        for i in range(len(layers) - 1, -1, -1):
            layer = layers[i]
            is_active = (i == active_index)
            
            item = LayerItemWidget(layer, i, is_active)
            item.selected.connect(self._on_item_selected)
            item.visibility_changed.connect(self.visibility_changed.emit)
            item.lock_changed.connect(self.lock_changed.emit)
            
            # 插入到stretch之前
            self.container_layout.insertWidget(
                self.container_layout.count() - 1, item
            )
            self.layer_items.append(item)
    
    def _on_item_selected(self, index: int):
        # 更新选中状态
        for item in self.layer_items:
            item.set_active(item.index == index)
        self.layer_selected.emit(index)
    
    def refresh_thumbnails(self):
        """刷新所有缩略图"""
        for item in self.layer_items:
            item.update_thumbnail()


class AlignmentToolbar(QFrame):
    """对齐工具栏"""
    
    align_requested = Signal(str)
    distribute_requested = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        self.setStyleSheet("""
            QFrame { 
                background: #f5f5f5; 
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)
        
        btn_style = """
            QToolButton {
                border: none;
                background: transparent;
                padding: 4px;
                border-radius: 3px;
                font-size: 12px;
            }
            QToolButton:hover { background: #e0e0e0; }
            QToolButton:pressed { background: #d0d0d0; }
        """
        
        # 水平对齐
        align_btns = [
            ("⫷", "left", "左对齐"),
            ("⫿", "center_h", "水平居中"),
            ("⫸", "right", "右对齐"),
        ]
        
        for icon, align, tip in align_btns:
            btn = QToolButton()
            btn.setText(icon)
            btn.setToolTip(tip)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(lambda _, a=align: self.align_requested.emit(a))
            layout.addWidget(btn)
        
        # 分隔线
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setStyleSheet("background: #ccc;")
        layout.addWidget(sep)
        
        # 垂直对齐
        valign_btns = [
            ("⊤", "top", "顶部对齐"),
            ("⊖", "center_v", "垂直居中"),
            ("⊥", "bottom", "底部对齐"),
        ]
        
        for icon, align, tip in valign_btns:
            btn = QToolButton()
            btn.setText(icon)
            btn.setToolTip(tip)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(lambda _, a=align: self.align_requested.emit(a))
            layout.addWidget(btn)
        
        # 分隔线
        sep2 = QFrame()
        sep2.setFixedWidth(1)
        sep2.setStyleSheet("background: #ccc;")
        layout.addWidget(sep2)
        
        # 分布
        dist_btns = [
            ("⋯", "horizontal", "水平等距分布"),
            ("⋮", "vertical", "垂直等距分布"),
        ]
        
        for icon, direction, tip in dist_btns:
            btn = QToolButton()
            btn.setText(icon)
            btn.setToolTip(tip)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(
                lambda _, d=direction: self.distribute_requested.emit(d)
            )
            layout.addWidget(btn)
        
        layout.addStretch()


class LayerPanel(QWidget):
    """完整的图层面板"""
    
    layers_changed = Signal()
    active_layer_changed = Signal(int)
    undo_clicked = Signal()
    reset_clicked = Signal()
    
    def __init__(self, layer_manager: LayerManager = None, parent=None):
        super().__init__(parent)
        self.layer_manager = layer_manager or LayerManager()
        self.setup_ui()
        self.refresh()
    
    def setup_ui(self):
        self.setMinimumWidth(260)
        self.setStyleSheet("""
            QWidget#LayerPanel { background: #ffffff; }
            QLabel { color: #2c3e50; }
        """)
        self.setObjectName("LayerPanel")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        
        # 标题栏
        header_layout = QHBoxLayout()
        title = QLabel("图层管理")
        title.setStyleSheet("font-weight: 700; font-size: 14px; color: #1a202c;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # 快速操作按钮
        add_btn = QToolButton()
        add_btn.setText("+")
        add_btn.setToolTip("添加图层")
        add_btn.setFixedSize(24, 24)
        add_btn.clicked.connect(self._add_layer)
        add_btn.setStyleSheet("""
            QToolButton {
                background: #3b82f6;
                color: white;
                border-radius: 12px;
                font-weight: bold;
                font-size: 16px;
            }
            QToolButton:hover { background: #2563eb; }
        """)
        header_layout.addWidget(add_btn)
        layout.addLayout(header_layout)
        
        # 操作工具栏
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)
        
        # 图层列表
        self.layer_list = LayerListWidget()
        self.layer_list.layer_selected.connect(self._on_layer_selected)
        self.layer_list.visibility_changed.connect(self._on_visibility_changed)
        self.layer_list.lock_changed.connect(self._on_lock_changed)
        layout.addWidget(self.layer_list, 1)
        
        # 透明度控制
        opacity_frame = self._create_opacity_control()
        layout.addWidget(opacity_frame)
        
        # 对齐工具
        align_label = QLabel("对齐与分布")
        align_label.setStyleSheet("font-size: 11px; color: #718096; margin-top: 4px;")
        layout.addWidget(align_label)
        
        self.align_toolbar = AlignmentToolbar()
        self.align_toolbar.align_requested.connect(self._on_align_requested)
        self.align_toolbar.distribute_requested.connect(self._on_distribute_requested)
        layout.addWidget(self.align_toolbar)
    
    def _create_toolbar(self) -> QFrame:
        """创建图层操作工具栏"""
        toolbar = QFrame()
        toolbar.setStyleSheet("""
            QFrame { 
                background: #f8fafc; 
                border: 1px solid #e2e8f0;
                border-radius: 6px;
            }
        """)
        
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)
        
        btn_style = """
            QPushButton {
                border: none;
                background: transparent;
                padding: 4px;
                border-radius: 4px;
                font-size: 14px;
                color: #475569;
            }
            QPushButton:hover { background: #e2e8f0; color: #1e293b; }
            QPushButton:pressed { background: #cbd5e1; }
            QPushButton:disabled { color: #cbd5e1; }
        """
        
        buttons = [
            ("➕", "添加图层", self._add_layer),
            ("➖", "删除图层", self._remove_layer),
            ("📋", "复制图层", self._duplicate_layer),
            ("⬆", "上移", self._move_up),
            ("⬇", "下移", self._move_down),
            ("⤒", "置顶", self._move_to_top),
            ("⤓", "置底", self._move_to_bottom),
            ("⊕", "合并", self._merge_down),
        ]
        
        for icon, tip, callback in buttons:
            btn = QPushButton(icon)
            btn.setToolTip(tip)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(callback)
            layout.addWidget(btn)

        # 分隔线
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setStyleSheet("background: #ddd;")
        layout.addWidget(sep)

        # 撤销和重置
        undo_btn = QPushButton("↩")
        undo_btn.setToolTip("撤销 (Undo)")
        undo_btn.setStyleSheet(btn_style)
        undo_btn.clicked.connect(self.undo_clicked.emit)
        layout.addWidget(undo_btn)

        reset_btn = QPushButton("↺")
        reset_btn.setToolTip("重置图层 (Reset)")
        reset_btn.setStyleSheet(btn_style)
        reset_btn.clicked.connect(self.reset_clicked.emit)
        layout.addWidget(reset_btn)
        
        layout.addStretch()
        return toolbar
    
    def _create_opacity_control(self) -> QFrame:
        """创建透明度控制"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame { 
                background: #f8fafc; 
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
        """)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)
        
        label = QLabel("不透明度")
        label.setStyleSheet("font-size: 12px; font-weight: 600; color: #475569;")
        layout.addWidget(label)
        
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #e2e8f0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 16px;
                height: 16px;
                margin: -5px 0;
                background: #3b82f6;
                border: 2px solid white;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #2563eb;
            }
            QSlider::sub-page:horizontal {
                background: #3b82f6;
                border-radius: 3px;
            }
        """)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        layout.addWidget(self.opacity_slider, 1)
        
        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(0, 100)
        self.opacity_spin.setValue(100)
        self.opacity_spin.setSuffix("%")
        self.opacity_spin.setFixedWidth(55)
        self.opacity_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.opacity_spin.setStyleSheet("""
            QSpinBox {
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 2px;
                font-size: 11px;
                background: white;
                color: #1e293b;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 0px;
            }
        """)
        self.opacity_spin.valueChanged.connect(self._on_opacity_spin_changed)
        layout.addWidget(self.opacity_spin)
        
        return frame
    
    def refresh(self):
        """刷新图层列表"""
        self.layer_list.update_layers(
            self.layer_manager.layers,
            self.layer_manager.active_layer_index
        )
        self._update_opacity_control()
    
    def _update_opacity_control(self):
        """更新透明度控制"""
        layer = self.layer_manager.get_active_layer()
        if layer:
            self.opacity_slider.blockSignals(True)
            self.opacity_spin.blockSignals(True)
            self.opacity_slider.setValue(layer.opacity)
            self.opacity_spin.setValue(layer.opacity)
            self.opacity_slider.blockSignals(False)
            self.opacity_spin.blockSignals(False)
    
    def _on_layer_selected(self, index: int):
        self.layer_manager.set_active_layer(index)
        self._update_opacity_control()
        self.active_layer_changed.emit(index)
    
    def _on_visibility_changed(self, index: int, visible: bool):
        self.layer_manager.set_layer_visibility(index, visible)
        self.layers_changed.emit()
    
    def _on_lock_changed(self, index: int, locked: bool):
        self.layer_manager.set_layer_locked(index, locked)
    
    def _on_opacity_changed(self, value: int):
        self.opacity_spin.blockSignals(True)
        self.opacity_spin.setValue(value)
        self.opacity_spin.blockSignals(False)
        
        index = self.layer_manager.active_layer_index
        self.layer_manager.set_layer_opacity(index, value)
        self.layers_changed.emit()
    
    def _on_opacity_spin_changed(self, value: int):
        self.opacity_slider.blockSignals(True)
        self.opacity_slider.setValue(value)
        self.opacity_slider.blockSignals(False)
        
        index = self.layer_manager.active_layer_index
        self.layer_manager.set_layer_opacity(index, value)
        self.layers_changed.emit()
    
    def _add_layer(self):
        """添加新图层 - 选择图片进行叠加"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片添加为新图层", "",
            "图像文件 (*.png *.jpg *.jpeg *.bmp *.gif);;所有文件 (*.*)"
        )
        if path:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                layer_name = os.path.basename(path)
                self.layer_manager.add_layer(pixmap, layer_name)
                self.refresh()
                self.layers_changed.emit()
            else:
                ModernMessageBox.warning(self, "错误", "无法打开该图像文件")
    
    def _remove_layer(self):
        index = self.layer_manager.active_layer_index
        if self.layer_manager.remove_layer(index):
            self.refresh()
            self.layers_changed.emit()
    
    def _duplicate_layer(self):
        index = self.layer_manager.active_layer_index
        if self.layer_manager.duplicate_layer(index):
            self.refresh()
            self.layers_changed.emit()
    
    def _move_up(self):
        index = self.layer_manager.active_layer_index
        if self.layer_manager.move_layer_up(index):
            self.refresh()
            self.layers_changed.emit()
    
    def _move_down(self):
        index = self.layer_manager.active_layer_index
        if self.layer_manager.move_layer_down(index):
            self.refresh()
            self.layers_changed.emit()
    
    def _move_to_top(self):
        index = self.layer_manager.active_layer_index
        if self.layer_manager.move_layer_to_top(index):
            self.refresh()
            self.layers_changed.emit()
    
    def _move_to_bottom(self):
        index = self.layer_manager.active_layer_index
        if self.layer_manager.move_layer_to_bottom(index):
            self.refresh()
            self.layers_changed.emit()
    
    def _merge_down(self):
        index = self.layer_manager.active_layer_index
        if self.layer_manager.merge_down(index):
            self.refresh()
            self.layers_changed.emit()
    
    def _on_align_requested(self, alignment: str):
        indices = [self.layer_manager.active_layer_index]
        # TODO: 支持多选
        if len(indices) >= 2:
            self.layer_manager.align_layers(indices, alignment)
            self.layers_changed.emit()
    
    def _on_distribute_requested(self, direction: str):
        indices = [self.layer_manager.active_layer_index]
        # TODO: 支持多选
        if len(indices) >= 3:
            self.layer_manager.distribute_layers(indices, direction)
            self.layers_changed.emit()
    
    def set_layer_manager(self, manager: LayerManager):
        """设置图层管理器"""
        self.layer_manager = manager
        self.refresh()
