"""
设置对话框 - 增强版
支持：快捷键管理、界面个性化、文件命名规则、多语言等
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QGroupBox,
    QFormLayout, QCheckBox, QComboBox, QScrollArea,
    QWidget, QFrame, QTabWidget, QSpinBox, QListWidget,
    QListWidgetItem
)
from PySide6.QtCore import Qt
from ui.modern_dialog import ModernMessageBox
from ui.icons import set_window_icon
from core.i18n import tr, get_supported_languages, apply_language
from PySide6.QtGui import QColor, QFont, QIcon, QKeySequence
from core.i18n import apply_language, get_supported_languages, current_language


class HotkeyEdit(QLineEdit):
    """快捷键输入框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText(tr("点击后按下快捷键..."))
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
    
    def keyPressEvent(self, event):
        key = event.key()
        
        # 允许 Backspace 和 Delete 清除快捷键
        if key == Qt.Key.Key_Backspace or key == Qt.Key.Key_Delete:
            self.clear()
            return
            
        modifiers = event.modifiers()
        modifier_list = []
        
        # 检测修饰键
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            modifier_list.append("Ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            modifier_list.append("Alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            modifier_list.append("Shift")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            modifier_list.append("Win")
            
        # 如果按下的是修饰键本身，只显示修饰键
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            if modifier_list:
                self.setText("+".join(modifier_list))
            else:
                # 某些情况下 modifiers 可能为空，但 key 是修饰键
                key_map = {
                    Qt.Key.Key_Control: "Ctrl",
                    Qt.Key.Key_Shift: "Shift",
                    Qt.Key.Key_Alt: "Alt",
                    Qt.Key.Key_Meta: "Win"
                }
                self.setText(key_map.get(key, ""))
            return
            
        # 使用 QKeySequence 获取标准键名
        # 注意：Qt.Key_A -> "A", Qt.Key_F1 -> "F1"
        key_name = QKeySequence(key).toString()
        
        if key_name:
            if modifier_list:
                # 组合键
                self.setText("+".join(modifier_list) + "+" + key_name)
            else:
                # 单键
                self.setText(key_name)


class SettingsDialog(QDialog):
    """设置对话框 - 增强版"""
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        self.setWindowTitle(tr("程序设置"))
        set_window_icon(self)
        self.setMinimumSize(580, 520)
        self.setStyleSheet("""
            QDialog { background: #f5f5f5; }
            QTabWidget::pane { 
                border: 1px solid #ddd; 
                background: white; 
                border-radius: 4px; 
            }
            QTabBar::tab { 
                background: #e8e8e8; 
                padding: 10px 20px; 
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                color: #555;
            }
            QTabBar::tab:selected { 
                background: white; 
                color: #2B579A;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background: #f0f0f0;
            }
            QGroupBox { 
                font-weight: bold; 
                font-size: 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 12px;
                padding: 15px;
                padding-top: 25px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #2B579A;
            }
            QLineEdit, QComboBox, QSpinBox {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 6px 10px;
                background: white;
                min-height: 18px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border-color: #0078D7;
            }
            QCheckBox { spacing: 8px; color: #333; }
            QCheckBox::indicator { 
                width: 16px; 
                height: 16px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background: white;
            }
            QCheckBox::indicator:checked {
                background: #0078D7;
                border-color: #0078D7;
            }
            QPushButton {
                background: #0078D7;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 20px;
                font-size: 12px;
                outline: none;
            }
            QPushButton:hover { background: #005A9E; }
            QPushButton[secondary="true"] {
                background: #e0e0e0;
                color: #333;
            }
            QPushButton[secondary="true"]:hover { background: #d0d0d0; }
            QLabel { color: #333; }
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标签页
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs, 1)
        
        # 各个标签页
        self.general_tab = self._create_general_tab()
        self.capture_tab = self._create_capture_tab()
        self.hotkey_tab = self._create_hotkey_tab()
        self.naming_tab = self._create_naming_tab()
        self.tabs.addTab(self.general_tab, tr("常规"))
        self.tabs.addTab(self.capture_tab, tr("截图"))
        self.tabs.addTab(self.hotkey_tab, tr("快捷键"))
        self.tabs.addTab(self.naming_tab, tr("命名规则"))
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        # 鲲穹AI品牌标识
        self.brand_label = QLabel(tr("鲲穹AI旗下产品"))
        self.brand_label.setStyleSheet("color: #bbb; font-size: 9px;")
        btn_layout.addWidget(self.brand_label)
        
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton(tr("取消"))
        self.cancel_btn.setProperty("secondary", True)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton(tr("保存设置"))
        self.save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.save_btn)
        
        main_layout.addLayout(btn_layout)
    
    def _create_general_tab(self) -> QWidget:
        """常规设置"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # 保存设置
        self.save_group = QGroupBox(tr("保存设置"))
        save_layout = QVBoxLayout(self.save_group)
        save_layout.setSpacing(12)
        
        self.path_label = QLabel(tr("默认保存路径:"))
        save_layout.addWidget(self.path_label)
        
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText(tr("选择截图保存目录..."))
        path_layout.addWidget(self.path_edit)
        
        self.browse_btn = QPushButton(tr("浏览"))
        self.browse_btn.setProperty("secondary", True)
        self.browse_btn.setFixedWidth(80)
        self.browse_btn.clicked.connect(self._browse_path)
        path_layout.addWidget(self.browse_btn)
        save_layout.addLayout(path_layout)
        
        format_layout = QHBoxLayout()
        self.format_label = QLabel(tr("默认格式:"))
        format_layout.addWidget(self.format_label)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "JPG", "BMP"])
        self.format_combo.setFixedWidth(100)
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        save_layout.addLayout(format_layout)
        
        self.auto_save_check = QCheckBox(tr("截图后自动保存到默认目录"))
        save_layout.addWidget(self.auto_save_check)
        
        self.clipboard_check = QCheckBox(tr("截图后自动复制到剪贴板"))
        save_layout.addWidget(self.clipboard_check)
        
        self.notification_check = QCheckBox(tr("操作完成后显示通知"))
        save_layout.addWidget(self.notification_check)
        
        language_layout = QHBoxLayout()
        self.language_label = QLabel(tr("界面语言:"))
        language_layout.addWidget(self.language_label)
        self.language_combo = QComboBox()
        self.language_combo.setMinimumWidth(220)
        for item in get_supported_languages():
            self.language_combo.addItem(item["name"], item["code"])
        language_layout.addWidget(self.language_combo)
        language_layout.addStretch()
        save_layout.addLayout(language_layout)
        
        layout.addWidget(self.save_group)
        
        # 编辑器设置
        self.editor_group = QGroupBox(tr("编辑器设置"))
        editor_layout = QVBoxLayout(self.editor_group)
        
        self.editor_fullscreen_check = QCheckBox(tr("编辑器默认全屏显示"))
        editor_layout.addWidget(self.editor_fullscreen_check)
        
        self.editor_remember_size_check = QCheckBox(tr("记住编辑器窗口大小"))
        editor_layout.addWidget(self.editor_remember_size_check)
        
        layout.addWidget(self.editor_group)
        
        # 版本与更新
        self.update_group = QGroupBox(tr("版本与更新"))
        update_layout = QVBoxLayout(self.update_group)

        version_layout = QHBoxLayout()
        from PySide6.QtWidgets import QApplication
        current_version = QApplication.applicationVersion()
        self.version_label = QLabel(tr("当前版本: {current_version}").format(current_version=current_version))
        self.version_label.setStyleSheet("color: #666666;")
        version_layout.addWidget(self.version_label)
        
        version_layout.addStretch()
        
        self.check_update_btn = QPushButton(tr("检查更新"))
        self.check_update_btn.setProperty("secondary", True)
        self.check_update_btn.setFixedWidth(100)
        self.check_update_btn.clicked.connect(self._manual_check_update)
        version_layout.addWidget(self.check_update_btn)
        
        self.feedback_btn = QPushButton(tr("反馈问题"))
        self.feedback_btn.setProperty("secondary", True)
        self.feedback_btn.setFixedWidth(100)
        self.feedback_btn.clicked.connect(self._open_feedback)
        version_layout.addWidget(self.feedback_btn)
        
        update_layout.addLayout(version_layout)
        layout.addWidget(self.update_group)
        
        layout.addStretch()
        
        return widget

    def _manual_check_update(self):
        """手动检查更新"""
        from core.update_manager import UpdateManager
        # 获取主窗口作为父窗口（如果有的话）
        parent = self.window()
        update_manager = UpdateManager(parent)
        # 强制检查更新，不静默
        update_manager.check_for_updates(manual=True)
    
    def _open_feedback(self):
        """打开反馈页面"""
        import webbrowser
        parent = self.parent()
        if parent and hasattr(parent, "login_manager"):
            url = parent.login_manager.get_feedback_url()
            if url:
                webbrowser.open(url)
                return
        
        # 回退逻辑
        from core.config import Config
        webbrowser.open(f"https://www.kunqiongai.com/feedback?soft_number={Config.SOFT_NUMBER}")
    
    def _create_capture_tab(self) -> QWidget:
        """截图设置"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # 滚动截图
        self.scroll_group = QGroupBox(tr("滚动截图"))
        scroll_layout = QFormLayout(self.scroll_group)
        
        self.scroll_delay_spin = QSpinBox()
        self.scroll_delay_spin.setRange(1, 20)
        self.scroll_delay_spin.setSuffix(tr(" × 0.1秒"))
        self.scroll_delay_label = QLabel(tr("滚动延迟:"))
        scroll_layout.addRow(self.scroll_delay_label, self.scroll_delay_spin)
        
        self.scroll_speed_combo = QComboBox()
        self.scroll_speed_combo.addItems([tr("慢速"), tr("中速"), tr("快速")])
        self.scroll_speed_label = QLabel(tr("滚动速度:"))
        scroll_layout.addRow(self.scroll_speed_label, self.scroll_speed_combo)
        
        layout.addWidget(self.scroll_group)
        
        # 重复截取
        self.repeat_group = QGroupBox(tr("重复截取"))
        repeat_layout = QVBoxLayout(self.repeat_group)
        
        self.repeat_hint_label = QLabel(tr("按 F8 可重复上次截图操作"))
        repeat_layout.addWidget(self.repeat_hint_label)
        
        layout.addWidget(self.repeat_group)
        layout.addStretch()
        
        return widget
    
    def _create_hotkey_tab(self) -> QWidget:
        """快捷键设置"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        self.hotkey_group = QGroupBox(tr("快捷键设置"))
        hotkey_layout = QFormLayout(self.hotkey_group)
        hotkey_layout.setSpacing(12)
        
        # 快捷键输入框和状态标签
        self.hotkey_inputs = {}
        self.hotkey_status = {}
        
        hotkey_items = [
            ("fullscreen", tr("全屏截图:"), tr("例如: Ctrl+Shift+F")),
            ("region", tr("矩形截图:"), tr("例如: Ctrl+Shift+A")),
            ("control", tr("窗口控件截图:"), tr("例如: Ctrl+Shift+W")),
            ("color_picker", tr("取色器:"), tr("例如: Ctrl+Shift+C")),
            ("repeat_capture", tr("重复截取:"), tr("例如: F8")),
            ("whiteboard", tr("白板:"), tr("例如: Win+Shift+W")),
            ("screen_record", tr("开始/停止录屏:"), tr("例如: Ctrl+Shift+R")),
        ]
        
        self.hotkey_labels = {}
        self.hotkey_placeholders = {}
        for name, label, placeholder in hotkey_items:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            
            edit = HotkeyEdit()
            edit.setPlaceholderText(placeholder)
            edit.setProperty("hotkey_name", name)
            edit.textChanged.connect(lambda text, n=name: self._on_hotkey_changed(n, text))
            row_layout.addWidget(edit)
            
            status = QLabel("")
            status.setFixedWidth(20)
            status.setStyleSheet("font-size: 14px;")
            row_layout.addWidget(status)
            
            label_widget = QLabel(label)
            self.hotkey_labels[name] = label_widget
            self.hotkey_placeholders[name] = placeholder
            self.hotkey_inputs[name] = edit
            self.hotkey_status[name] = status
            
            hotkey_layout.addRow(label_widget, row_widget)
        
        # 兼容旧属性名
        self.hotkey_fullscreen = self.hotkey_inputs["fullscreen"]
        self.hotkey_region = self.hotkey_inputs["region"]
        self.hotkey_control = self.hotkey_inputs["control"]
        self.hotkey_color = self.hotkey_inputs["color_picker"]
        self.hotkey_repeat = self.hotkey_inputs["repeat_capture"]
        self.hotkey_whiteboard = self.hotkey_inputs["whiteboard"]
        self.hotkey_screen_record = self.hotkey_inputs["screen_record"]
        
        layout.addWidget(self.hotkey_group)
        
        # 冲突提示
        self.conflict_label = QLabel("")
        self.conflict_label.setStyleSheet("color: #c42b1c; font-size: 11px;")
        self.conflict_label.setWordWrap(True)
        layout.addWidget(self.conflict_label)
        
        # 预设方案
        self.preset_group = QGroupBox(tr("预设方案"))
        preset_layout = QHBoxLayout(self.preset_group)
        
        self.default_preset_btn = QPushButton(tr("默认"))
        self.default_preset_btn.setProperty("secondary", True)
        self.default_preset_btn.clicked.connect(lambda _: self._apply_hotkey_preset(tr("默认")))
        preset_layout.addWidget(self.default_preset_btn)

        self.hypersnap_preset_btn = QPushButton(tr("HyperSnap风格"))
        self.hypersnap_preset_btn.setProperty("secondary", True)
        self.hypersnap_preset_btn.clicked.connect(lambda _: self._apply_hotkey_preset(tr("HyperSnap风格")))
        preset_layout.addWidget(self.hypersnap_preset_btn)

        self.snagit_preset_btn = QPushButton(tr("Snagit风格"))
        self.snagit_preset_btn.setProperty("secondary", True)
        self.snagit_preset_btn.clicked.connect(lambda _: self._apply_hotkey_preset(tr("Snagit风格")))
        preset_layout.addWidget(self.snagit_preset_btn)
        
        layout.addWidget(self.preset_group)
        
        # 提示信息
        self.hotkey_hint = QLabel(tr("💡 快捷键修改后保存即可生效，无需重启程序"))
        self.hotkey_hint.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.hotkey_hint)
        
        layout.addStretch()
        
        return widget
    
    def _on_hotkey_changed(self, name: str, text: str):
        """快捷键输入变化时检查冲突"""
        # 检查与其他快捷键的冲突
        conflict_with = None
        for other_name, edit in self.hotkey_inputs.items():
            if other_name != name and edit.text() and edit.text().upper() == text.upper():
                conflict_with = other_name
                break
        
        status_label = self.hotkey_status.get(name)
        if status_label:
            if conflict_with:
                status_label.setText("⚠️")
                status_label.setToolTip(tr("与 {name} 冲突").format(name=self._get_hotkey_display_name(conflict_with)))
                self.conflict_label.setText(tr("⚠️ 快捷键冲突: {text} 已被 {name} 使用").format(text=text, name=self._get_hotkey_display_name(conflict_with)))
            elif text:
                status_label.setText("✓")
                status_label.setToolTip(tr("有效"))
                self.conflict_label.setText("")
            else:
                status_label.setText("")
                status_label.setToolTip("")
    
    def _get_hotkey_display_name(self, name: str) -> str:
        """获取快捷键显示名称"""
        names = {
            "fullscreen": tr("全屏截图"),
            "region": tr("矩形截图"),
            "control": tr("窗口控件截图"),
            "color_picker": tr("取色器"),
            "repeat_capture": tr("重复截取"),
            "whiteboard": tr("白板"),
            "screen_record": tr("屏幕录制"),
        }
        return names.get(name, name)
    
    def _create_naming_tab(self) -> QWidget:
        """命名规则"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        self.naming_group = QGroupBox(tr("文件命名规则"))
        naming_layout = QVBoxLayout(self.naming_group)
        
        self.prefix_label = QLabel(tr("自定义前缀:"))
        naming_layout.addWidget(self.prefix_label)
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText(tr("Screenshot"))
        naming_layout.addWidget(self.prefix_edit)
        
        self.template_label = QLabel(tr("命名模板:"))
        naming_layout.addWidget(self.template_label)
        self.template_combo = QComboBox()
        self.template_combo.setEditable(True)
        naming_layout.addWidget(self.template_combo)
        
        # 变量说明
        self.vars_label = QLabel(tr("""
可用变量:
  ${YYYY} - 年份 (2024)
  ${MM} - 月份 (01-12)
  ${DD} - 日期 (01-31)
  ${HH} - 小时 (00-23)
  ${YYYYMMDD} - 日期 (20241201)
  ${HHMMSS} - 时间 (143052)
  ${MODE} - 截图模式
  ${PREFIX} - 自定义前缀
  ${SEQ} - 序号 (001, 002...)
        """))
        self.vars_label.setStyleSheet("color: #666; font-size: 11px; background: #f0f0f0; padding: 10px; border-radius: 4px;")
        naming_layout.addWidget(self.vars_label)
        
        layout.addWidget(self.naming_group)
        
        # 预览
        self.preview_group = QGroupBox(tr("预览"))
        preview_layout = QVBoxLayout(self.preview_group)
        self.preview_label = QLabel(tr("screenshot_20241201_001.png"))
        self.preview_label.setStyleSheet("font-family: Consolas; font-size: 12px;")
        preview_layout.addWidget(self.preview_label)
        
        layout.addWidget(self.preview_group)
        layout.addStretch()
        
        return widget
    
    def load_settings(self):
        """加载设置"""
        # 常规
        self.path_edit.setText(self.config.get("save_path", ""))
        format_map = {"png": 0, "jpg": 1, "bmp": 2}
        self.format_combo.setCurrentIndex(format_map.get(self.config.get("default_format", "png"), 0))
        self.auto_save_check.setChecked(self.config.get("auto_save", False))
        self.clipboard_check.setChecked(self.config.get("copy_to_clipboard", True))
        self.notification_check.setChecked(self.config.get("show_notification", True))
        self.editor_fullscreen_check.setChecked(self.config.get("editor_fullscreen", True))
        self.editor_remember_size_check.setChecked(self.config.get("editor_remember_size", True))
        
        lang = self.config.get("language", current_language())
        idx = self.language_combo.findData(lang)
        if idx < 0:
            idx = self.language_combo.findData("auto")
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)
        
        # 截图
        self.scroll_delay_spin.setValue(int(self.config.get("scroll_delay", 0.5) * 10))
        speed_map = {"slow": 0, "medium": 1, "fast": 2}
        self.scroll_speed_combo.setCurrentIndex(speed_map.get(self.config.get("scroll_speed", "medium"), 1))
        
        # 快捷键
        hotkeys = self.config.get("hotkeys", {})
        self.hotkey_fullscreen.setText(hotkeys.get("fullscreen", "Ctrl+Shift+F"))
        self.hotkey_region.setText(hotkeys.get("region", "Ctrl+Shift+A"))
        self.hotkey_control.setText(hotkeys.get("control", "Ctrl+Shift+W"))
        self.hotkey_color.setText(hotkeys.get("color_picker", "Ctrl+Shift+C"))
        self.hotkey_repeat.setText(hotkeys.get("repeat_capture", "F8"))
        self.hotkey_whiteboard.setText(hotkeys.get("whiteboard", "Win+Shift+W"))
        self.hotkey_screen_record.setText(hotkeys.get("screen_record", "Ctrl+Shift+R"))
        
        # 命名
        self.prefix_edit.setText(self.config.get("naming_prefix", "Screenshot"))
        templates = self.config.get("naming_templates", [])
        self.template_combo.clear()
        self.template_combo.addItems(templates)
        current_template = self.config.get("naming_template", "")
        idx = self.template_combo.findText(current_template)
        if idx >= 0:
            self.template_combo.setCurrentIndex(idx)
        else:
            self.template_combo.setCurrentText(current_template)
    
    def _refresh_language_dependent_texts(self):
        self.setWindowTitle(tr("程序设置"))
        self.tabs.setTabText(0, tr("常规"))
        self.tabs.setTabText(1, tr("截图"))
        self.tabs.setTabText(2, tr("快捷键"))
        self.tabs.setTabText(3, tr("命名规则"))
        self.brand_label.setText(tr("鲲穹AI旗下产品"))
        self.cancel_btn.setText(tr("取消"))
        self.save_btn.setText(tr("保存设置"))

        self.save_group.setTitle(tr("保存设置"))
        self.path_label.setText(tr("默认保存路径:"))
        self.path_edit.setPlaceholderText(tr("选择截图保存目录..."))
        self.browse_btn.setText(tr("浏览"))
        self.format_label.setText(tr("默认格式:"))
        self.language_label.setText(tr("界面语言:"))
        self.editor_group.setTitle(tr("编辑器设置"))
        self.update_group.setTitle(tr("版本与更新"))
        from PySide6.QtWidgets import QApplication
        self.version_label.setText(tr("当前版本: {current_version}").format(current_version=QApplication.applicationVersion()))
        self.check_update_btn.setText(tr("检查更新"))
        self.feedback_btn.setText(tr("反馈问题"))

        self.scroll_group.setTitle(tr("滚动截图"))
        self.scroll_delay_label.setText(tr("滚动延迟:"))
        self.scroll_speed_label.setText(tr("滚动速度:"))
        self.scroll_delay_spin.setSuffix(tr(" × 0.1秒"))

        speed_texts = [tr("慢速"), tr("中速"), tr("快速")]
        current_speed_index = self.scroll_speed_combo.currentIndex()
        self.scroll_speed_combo.clear()
        self.scroll_speed_combo.addItems(speed_texts)
        if current_speed_index >= 0:
            self.scroll_speed_combo.setCurrentIndex(min(current_speed_index, len(speed_texts) - 1))

        self.repeat_group.setTitle(tr("重复截取"))
        self.repeat_hint_label.setText(tr("按 F8 可重复上次截图操作"))

        self.hotkey_group.setTitle(tr("快捷键设置"))
        hotkey_label_map = {
            "fullscreen": tr("全屏截图:"),
            "region": tr("矩形截图:"),
            "control": tr("窗口控件截图:"),
            "color_picker": tr("取色器:"),
            "repeat_capture": tr("重复截取:"),
            "whiteboard": tr("白板:"),
            "screen_record": tr("开始/停止录屏:"),
        }
        hotkey_placeholder_map = {
            "fullscreen": tr("例如: Ctrl+Shift+F"),
            "region": tr("例如: Ctrl+Shift+A"),
            "control": tr("例如: Ctrl+Shift+W"),
            "color_picker": tr("例如: Ctrl+Shift+C"),
            "repeat_capture": tr("例如: F8"),
            "whiteboard": tr("例如: Win+Shift+W"),
            "screen_record": tr("例如: Ctrl+Shift+R"),
        }
        for name, label_widget in self.hotkey_labels.items():
            label_widget.setText(hotkey_label_map.get(name, label_widget.text()))
        for name, edit in self.hotkey_inputs.items():
            edit.setPlaceholderText(hotkey_placeholder_map.get(name, ""))
        self.preset_group.setTitle(tr("预设方案"))
        self.default_preset_btn.setText(tr("默认"))
        self.hypersnap_preset_btn.setText(tr("HyperSnap风格"))
        self.snagit_preset_btn.setText(tr("Snagit风格"))
        self.hotkey_hint.setText(tr("💡 快捷键修改后保存即可生效，无需重启程序"))

        self.naming_group.setTitle(tr("文件命名规则"))
        self.prefix_label.setText(tr("自定义前缀:"))
        self.template_label.setText(tr("命名模板:"))
        self.vars_label.setText(tr("""
可用变量:
  ${YYYY} - 年份 (2024)
  ${MM} - 月份 (01-12)
  ${DD} - 日期 (01-31)
  ${HH} - 小时 (00-23)
  ${YYYYMMDD} - 日期 (20241201)
  ${HHMMSS} - 时间 (143052)
  ${MODE} - 截图模式
  ${PREFIX} - 自定义前缀
  ${SEQ} - 序号 (001, 002...)
        """))
        self.preview_group.setTitle(tr("预览"))

    def _browse_path(self):
        path = QFileDialog.getExistingDirectory(self, tr("选择保存目录"), self.path_edit.text())
        if path:
            self.path_edit.setText(path)
    
    def _apply_hotkey_preset(self, preset: str):
        presets = {
            tr("默认"): {
                "fullscreen": "Ctrl+Shift+F",
                "region": "Ctrl+Shift+A",
                "control": "Ctrl+Shift+W",
                "color_picker": "Ctrl+Shift+C",
            },
            tr("HyperSnap风格"): {
                "fullscreen": "Ctrl+Shift+S",
                "region": "Ctrl+Shift+R",
                "control": "Ctrl+Shift+W",
                "color_picker": "Ctrl+Shift+P",
            },
            tr("Snagit风格"): {
                "fullscreen": "Print",
                "region": "Ctrl+Shift+Print",
                "control": "Alt+Print",
                "color_picker": "Ctrl+Shift+O",
            },
        }
        
        if preset in presets:
            p = presets[preset]
            self.hotkey_fullscreen.setText(p.get("fullscreen", ""))
            self.hotkey_region.setText(p.get("region", ""))
            self.hotkey_control.setText(p.get("control", ""))
            self.hotkey_color.setText(p.get("color_picker", ""))
    
    def _save_settings(self):
        # 检查快捷键冲突
        hotkey_values = {}
        for name, edit in self.hotkey_inputs.items():
            text = edit.text().strip().upper()
            if text:
                if text in hotkey_values.values():
                    ModernMessageBox.warning(self, tr("快捷键冲突"), 
                        f"快捷键 {text} 被多个功能使用，请修改后再保存。")
                    return
                hotkey_values[name] = text
        
        # 常规
        self.config.set("save_path", self.path_edit.text())
        format_map = {0: "png", 1: "jpg", 2: "bmp"}
        self.config.set("default_format", format_map[self.format_combo.currentIndex()])
        self.config.set("auto_save", self.auto_save_check.isChecked())
        self.config.set("copy_to_clipboard", self.clipboard_check.isChecked())
        self.config.set("show_notification", self.notification_check.isChecked())
        self.config.set("editor_fullscreen", self.editor_fullscreen_check.isChecked())
        self.config.set("editor_remember_size", self.editor_remember_size_check.isChecked())
        self.config.set("language", self.language_combo.currentData())
        
        # 截图
        self.config.set("scroll_delay", self.scroll_delay_spin.value() / 10)
        speed_map = {0: "slow", 1: "medium", 2: "fast"}
        self.config.set("scroll_speed", speed_map[self.scroll_speed_combo.currentIndex()])
        
        # 快捷键
        new_hotkeys = {
            "fullscreen": self.hotkey_fullscreen.text(),
            "region": self.hotkey_region.text(),
            "control": self.hotkey_control.text(),
            "color_picker": self.hotkey_color.text(),
            "repeat_capture": self.hotkey_repeat.text(),
            "whiteboard": self.hotkey_whiteboard.text(),
            "screen_record": self.hotkey_screen_record.text(),
        }
        self.config.set("hotkeys", new_hotkeys)
        
        # 命名
        self.config.set("naming_prefix", self.prefix_edit.text())
        self.config.set("naming_template", self.template_combo.currentText())
        
        self.config.save_config()
        
        app = self.window().windowHandle().screen().context().objectName() if False else None
        apply_language(self.language_combo.currentData())
        self._refresh_language_dependent_texts()
        
        parent = self.parent()
        if parent and hasattr(parent, 'refresh_i18n'):
            try:
                parent.refresh_i18n()
            except Exception:
                pass
        
        # 通知主窗口重新加载快捷键（即时生效）
        if self.parent() and hasattr(self.parent(), 'hotkey_manager'):
            self.parent().hotkey_manager.reload_hotkeys()
        
        self.accept()
