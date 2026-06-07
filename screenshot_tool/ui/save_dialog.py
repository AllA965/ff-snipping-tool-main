"""
增强保存对话框 - 支持快速切换文件夹、批量导出
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QFrame,
    QFileDialog, QListWidget, QListWidgetItem,
    QCheckBox, QGroupBox, QGridLayout,
    QProgressBar, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
import os
from pathlib import Path
from ui.modern_dialog import ModernMessageBox


class EnhancedSaveDialog(QDialog):
    """增强保存对话框"""
    
    def __init__(self, pixmap, config, recent_folders_manager, 
                 default_name: str = "", parent=None):
        super().__init__(parent)
        self.pixmap = pixmap
        self.config = config
        self.recent_folders = recent_folders_manager
        self.default_name = default_name
        self.saved_path = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("保存图像")
        self.setMinimumSize(500, 380)
        self.setStyleSheet("""
            QDialog { background: #f5f5f5; }
            QLabel { color: #333; font-size: 12px; }
            QLabel[title="true"] { font-size: 16px; font-weight: bold; color: #2B579A; }
            QLineEdit, QComboBox {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 6px 10px;
                background: white;
                min-height: 26px;
            }
            QLineEdit:focus, QComboBox:focus { border-color: #0078D7; }
            QPushButton {
                background: #0078D7;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover { background: #005A9E; }
            QPushButton[secondary="true"] { background: #e0e0e0; color: #333; }
            QPushButton[secondary="true"]:hover { background: #d0d0d0; }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 10px;
                padding: 10px;
                padding-top: 20px;
                background: white;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title = QLabel("保存图像")
        title.setProperty("title", True)
        layout.addWidget(title)
        
        # 文件名
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("文件名:"))
        self.name_edit = QLineEdit()
        self.name_edit.setText(self.default_name or self.config.generate_filename("screenshot"))
        name_layout.addWidget(self.name_edit, 1)
        layout.addLayout(name_layout)
        
        # 保存位置
        path_group = QGroupBox("保存位置")
        path_layout = QVBoxLayout(path_group)
        
        # 当前路径
        current_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setText(self.config.get("save_path", str(Path.home() / "Pictures")))
        current_layout.addWidget(self.path_edit, 1)
        
        browse_btn = QPushButton("浏览...")
        browse_btn.setProperty("secondary", True)
        browse_btn.clicked.connect(self._browse_folder)
        current_layout.addWidget(browse_btn)
        path_layout.addLayout(current_layout)
        
        # 快速切换 - 最近文件夹
        recent_label = QLabel("快速切换:")
        recent_label.setStyleSheet("color: #666; font-size: 11px; margin-top: 5px;")
        path_layout.addWidget(recent_label)
        
        recent_layout = QHBoxLayout()
        recent_folders = self.recent_folders.get_recent_folders(3)
        
        if recent_folders:
            for folder in recent_folders:
                folder_name = os.path.basename(folder) or folder
                btn = QPushButton(f"📁 {folder_name[:15]}...")
                btn.setProperty("secondary", True)
                btn.setToolTip(folder)
                btn.setFixedHeight(28)
                btn.clicked.connect(lambda _, f=folder: self._set_folder(f))
                recent_layout.addWidget(btn)
        else:
            no_recent = QLabel("暂无最近文件夹")
            no_recent.setStyleSheet("color: #999;")
            recent_layout.addWidget(no_recent)
        
        recent_layout.addStretch()
        path_layout.addLayout(recent_layout)
        
        # 设为默认
        self.set_default_cb = QCheckBox("设为默认保存位置")
        path_layout.addWidget(self.set_default_cb)
        
        layout.addWidget(path_group)
        
        # 格式选择
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("格式:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "JPEG", "BMP", "WebP"])
        current_format = self.config.get("default_format", "png").upper()
        idx = self.format_combo.findText(current_format)
        if idx >= 0:
            self.format_combo.setCurrentIndex(idx)
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        layout.addLayout(format_layout)
        
        layout.addStretch()
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("secondary", True)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._do_save)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "选择保存位置", self.path_edit.text()
        )
        if folder:
            self._set_folder(folder)
    
    def _set_folder(self, folder: str):
        self.path_edit.setText(folder)
    
    def _do_save(self):
        folder = self.path_edit.text()
        filename = self.name_edit.text()
        fmt = self.format_combo.currentText().lower()
        
        # 确保文件名有正确的扩展名
        if not filename.lower().endswith(f".{fmt}"):
            # 移除其他扩展名
            for ext in [".png", ".jpg", ".jpeg", ".bmp", ".webp"]:
                if filename.lower().endswith(ext):
                    filename = filename[:-len(ext)]
                    break
            filename = f"{filename}.{fmt}"
        
        file_path = os.path.join(folder, filename)
        
        # 检查文件是否存在
        if os.path.exists(file_path):
            reply = ModernMessageBox.question(
                self, "文件已存在",
                f"文件 {filename} 已存在，是否覆盖？",
                yes_text="覆盖", no_text="取消"
            )
            if reply != QDialog.DialogCode.Accepted:
                return
        
        # 确保目录存在
        os.makedirs(folder, exist_ok=True)
        
        # 保存文件
        try:
            if self.pixmap.save(file_path):
                self.saved_path = file_path
                
                # 添加到最近文件夹
                self.recent_folders.add_folder(folder)
                
                # 设为默认
                if self.set_default_cb.isChecked():
                    self.config.set("save_path", folder)
                
                self.accept()
            else:
                raise Exception("保存失败")
        except Exception as e:
            ModernMessageBox.error(self, "保存失败", f"无法保存文件: {str(e)}")
    
    def get_saved_path(self) -> str:
        return self.saved_path


class BatchExportDialog(QDialog):
    """批量导出对话框"""
    
    export_completed = Signal(list)  # 导出完成信号，返回成功保存的路径列表
    
    def __init__(self, images: list, config, recent_folders_manager, parent=None):
        """
        images: [(name, pixmap), ...] 图像列表
        """
        super().__init__(parent)
        self.images = images
        self.config = config
        self.recent_folders = recent_folders_manager
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("批量导出")
        self.setMinimumSize(550, 450)
        self.setStyleSheet("""
            QDialog { background: #f5f5f5; }
            QLabel { color: #333; font-size: 12px; }
            QLabel[title="true"] { font-size: 16px; font-weight: bold; color: #2B579A; }
            QLineEdit, QComboBox {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 6px 10px;
                background: white;
                min-height: 26px;
            }
            QPushButton {
                background: #0078D7;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 16px;
            }
            QPushButton:hover { background: #005A9E; }
            QPushButton[secondary="true"] { background: #e0e0e0; color: #333; }
            QPushButton[secondary="true"]:hover { background: #d0d0d0; }
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
            }
            QListWidget::item { padding: 5px; }
            QListWidget::item:selected { background: #e8f4fd; color: #333; }
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk { background: #0078D7; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title = QLabel(f"批量导出 ({len(self.images)} 张图像)")
        title.setProperty("title", True)
        layout.addWidget(title)
        
        # 图像列表
        list_label = QLabel("待导出图像:")
        layout.addWidget(list_label)
        
        self.image_list = QListWidget()
        self.image_list.setMaximumHeight(120)
        for name, _ in self.images:
            item = QListWidgetItem(f"📷 {name}")
            self.image_list.addItem(item)
        layout.addWidget(self.image_list)
        
        # 导出设置
        settings_layout = QGridLayout()
        
        # 保存位置
        settings_layout.addWidget(QLabel("保存位置:"), 0, 0)
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setText(self.config.get("save_path", str(Path.home() / "Pictures")))
        path_layout.addWidget(self.path_edit)
        browse_btn = QPushButton("浏览")
        browse_btn.setProperty("secondary", True)
        browse_btn.clicked.connect(self._browse_folder)
        path_layout.addWidget(browse_btn)
        settings_layout.addLayout(path_layout, 0, 1)
        
        # 格式
        settings_layout.addWidget(QLabel("导出格式:"), 1, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "JPEG", "BMP", "WebP"])
        settings_layout.addWidget(self.format_combo, 1, 1)
        
        # 命名规则
        settings_layout.addWidget(QLabel("命名规则:"), 2, 0)
        self.naming_combo = QComboBox()
        self.naming_combo.addItems([
            "保持原名",
            "添加前缀",
            "添加后缀",
            "序号命名"
        ])
        self.naming_combo.currentIndexChanged.connect(self._on_naming_changed)
        settings_layout.addWidget(self.naming_combo, 2, 1)
        
        # 前缀/后缀输入
        self.prefix_label = QLabel("前缀:")
        self.prefix_label.hide()
        settings_layout.addWidget(self.prefix_label, 3, 0)
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("例如: export_")
        self.prefix_edit.hide()
        settings_layout.addWidget(self.prefix_edit, 3, 1)
        
        layout.addLayout(settings_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("secondary", True)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        self.export_btn = QPushButton("开始导出")
        self.export_btn.clicked.connect(self._do_export)
        btn_layout.addWidget(self.export_btn)
        
        layout.addLayout(btn_layout)
    
    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "选择导出位置", self.path_edit.text()
        )
        if folder:
            self.path_edit.setText(folder)
    
    def _on_naming_changed(self, index):
        if index in [1, 2]:  # 添加前缀或后缀
            self.prefix_label.show()
            self.prefix_edit.show()
            self.prefix_label.setText("前缀:" if index == 1 else "后缀:")
        else:
            self.prefix_label.hide()
            self.prefix_edit.hide()
    
    def _do_export(self):
        folder = self.path_edit.text()
        fmt = self.format_combo.currentText().lower()
        naming_rule = self.naming_combo.currentIndex()
        prefix_suffix = self.prefix_edit.text()
        
        if not os.path.isdir(folder):
            os.makedirs(folder, exist_ok=True)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self.images))
        self.export_btn.setEnabled(False)
        
        saved_paths = []
        
        for i, (name, pixmap) in enumerate(self.images):
            # 生成文件名
            base_name = os.path.splitext(name)[0]
            
            if naming_rule == 0:  # 保持原名
                new_name = base_name
            elif naming_rule == 1:  # 添加前缀
                new_name = f"{prefix_suffix}{base_name}"
            elif naming_rule == 2:  # 添加后缀
                new_name = f"{base_name}{prefix_suffix}"
            else:  # 序号命名
                new_name = f"export_{i+1:03d}"
            
            file_path = os.path.join(folder, f"{new_name}.{fmt}")
            
            # 处理重名
            counter = 1
            while os.path.exists(file_path):
                file_path = os.path.join(folder, f"{new_name}_{counter}.{fmt}")
                counter += 1
            
            try:
                if pixmap.save(file_path):
                    saved_paths.append(file_path)
                    self.status_label.setText(f"已导出: {os.path.basename(file_path)}")
            except Exception as e:
                self.status_label.setText(f"导出失败: {name} - {str(e)}")
            
            self.progress_bar.setValue(i + 1)
        
        # 添加到最近文件夹
        self.recent_folders.add_folder(folder)
        
        self.export_btn.setEnabled(True)
        self.status_label.setText(f"导出完成! 成功 {len(saved_paths)}/{len(self.images)} 张")
        
        if saved_paths:
            self.export_completed.emit(saved_paths)
            ModernMessageBox.success(
                self, "导出完成",
                f"成功导出 {len(saved_paths)} 张图像到:\n{folder}"
            )
            self.accept()
