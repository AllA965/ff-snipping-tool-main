from pathlib import Path

settings_path = Path(r"C:\Users\admin\Desktop\ff\截图贴图工具\screenshot_tool\ui\settings_dialog.py")
text = settings_path.read_text(encoding="utf-8")
if 'from core.i18n import tr, get_supported_languages, apply_language' not in text:
    text = text.replace('from ui.icons import set_window_icon\n', 'from ui.icons import set_window_icon\nfrom core.i18n import tr, get_supported_languages, apply_language\n')
repls = {
    'self.setWindowTitle("程序设置")':'self.setWindowTitle(tr("程序设置"))',
    'self.tabs.addTab(self._create_general_tab(), "常规")':'self.tabs.addTab(self._create_general_tab(), tr("常规"))',
    'self.tabs.addTab(self._create_capture_tab(), "截图")':'self.tabs.addTab(self._create_capture_tab(), tr("截图"))',
    'self.tabs.addTab(self._create_hotkey_tab(), "快捷键")':'self.tabs.addTab(self._create_hotkey_tab(), tr("快捷键"))',
    'self.tabs.addTab(self._create_naming_tab(), "命名规则")':'self.tabs.addTab(self._create_naming_tab(), tr("命名规则"))',
    'brand_label = QLabel("鲲穹AI旗下产品")':'brand_label = QLabel(tr("鲲穹AI旗下产品"))',
    'cancel_btn = QPushButton("取消")':'cancel_btn = QPushButton(tr("取消"))',
    'save_btn = QPushButton("保存设置")':'save_btn = QPushButton(tr("保存设置"))',
    'save_group = QGroupBox("保存设置")':'save_group = QGroupBox(tr("保存设置"))',
    'path_label = QLabel("默认保存路径:")':'path_label = QLabel(tr("默认保存路径:"))',
    'self.path_edit.setPlaceholderText("选择截图保存目录...")':'self.path_edit.setPlaceholderText(tr("选择截图保存目录..."))',
    'browse_btn = QPushButton("浏览")':'browse_btn = QPushButton(tr("浏览"))',
    'format_layout.addWidget(QLabel("默认格式:"))':'format_layout.addWidget(QLabel(tr("默认格式:")))',
    'self.auto_save_check = QCheckBox("截图后自动保存到默认目录")':'self.auto_save_check = QCheckBox(tr("截图后自动保存到默认目录"))',
    'self.clipboard_check = QCheckBox("截图后自动复制到剪贴板")':'self.clipboard_check = QCheckBox(tr("截图后自动复制到剪贴板"))',
    'self.notification_check = QCheckBox("操作完成后显示通知")':'self.notification_check = QCheckBox(tr("操作完成后显示通知"))',
    'language_layout.addWidget(QLabel("界面语言:"))':'language_layout.addWidget(QLabel(tr("界面语言:")))',
    'editor_group = QGroupBox("编辑器设置")':'editor_group = QGroupBox(tr("编辑器设置"))',
    'self.editor_fullscreen_check = QCheckBox("编辑器默认全屏显示")':'self.editor_fullscreen_check = QCheckBox(tr("编辑器默认全屏显示"))',
    'self.editor_remember_size_check = QCheckBox("记住编辑器窗口大小")':'self.editor_remember_size_check = QCheckBox(tr("记住编辑器窗口大小"))',
    'update_group = QGroupBox("版本与更新")':'update_group = QGroupBox(tr("版本与更新"))',
    'version_label = QLabel(f"当前版本: {current_version}")':'version_label = QLabel(tr("当前版本: {current_version}").format(current_version=current_version))',
    'self.check_update_btn = QPushButton("检查更新")':'self.check_update_btn = QPushButton(tr("检查更新"))',
    'self.feedback_btn = QPushButton("反馈问题")':'self.feedback_btn = QPushButton(tr("反馈问题"))',
    'scroll_group = QGroupBox("滚动截图")':'scroll_group = QGroupBox(tr("滚动截图"))',
    'self.scroll_delay_spin.setSuffix(" × 0.1秒")':'self.scroll_delay_spin.setSuffix(tr(" × 0.1秒"))',
    'scroll_layout.addRow("滚动延迟:", self.scroll_delay_spin)':'scroll_layout.addRow(tr("滚动延迟:"), self.scroll_delay_spin)',
    'self.scroll_speed_combo.addItems(["慢速", "中速", "快速"])':'self.scroll_speed_combo.addItems([tr("慢速"), tr("中速"), tr("快速")])',
    'scroll_layout.addRow("滚动速度:", self.scroll_speed_combo)':'scroll_layout.addRow(tr("滚动速度:"), self.scroll_speed_combo)',
    'repeat_group = QGroupBox("重复截取")':'repeat_group = QGroupBox(tr("重复截取"))',
    'repeat_layout.addWidget(QLabel("按 F8 可重复上次截图操作"))':'repeat_layout.addWidget(QLabel(tr("按 F8 可重复上次截图操作")))',
    'hotkey_group = QGroupBox("快捷键设置")':'hotkey_group = QGroupBox(tr("快捷键设置"))',
    'preset_group = QGroupBox("预设方案")':'preset_group = QGroupBox(tr("预设方案"))',
    'hint = QLabel("💡 快捷键修改后保存即可生效，无需重启程序")':'hint = QLabel(tr("💡 快捷键修改后保存即可生效，无需重启程序"))',
    'naming_group = QGroupBox("文件命名规则")':'naming_group = QGroupBox(tr("文件命名规则"))',
    'naming_layout.addWidget(QLabel("自定义前缀:"))':'naming_layout.addWidget(QLabel(tr("自定义前缀:")))',
    'self.prefix_edit.setPlaceholderText("Screenshot")':'self.prefix_edit.setPlaceholderText(tr("Screenshot"))',
    'naming_layout.addWidget(QLabel("命名模板:"))':'naming_layout.addWidget(QLabel(tr("命名模板:")))',
    'preview_group = QGroupBox("预览")':'preview_group = QGroupBox(tr("预览"))',
    'self.preview_label = QLabel("screenshot_20241201_001.png")':'self.preview_label = QLabel(tr("screenshot_20241201_001.png"))',
}
for old, new in repls.items():
    text = text.replace(old, new)
text = text.replace('for name in ["默认", "HyperSnap风格", "Snagit风格"]:', 'for name in [tr("默认"), tr("HyperSnap风格"), tr("Snagit风格")]:')
text = text.replace('status_label.setToolTip(f"与 {self._get_hotkey_display_name(conflict_with)} 冲突")', 'status_label.setToolTip(tr("与 {name} 冲突").format(name=self._get_hotkey_display_name(conflict_with)))')
text = text.replace('self.conflict_label.setText(f"⚠️ 快捷键冲突: {text} 已被 {self._get_hotkey_display_name(conflict_with)} 使用")', 'self.conflict_label.setText(tr("⚠️ 快捷键冲突: {text} 已被 {name} 使用").format(text=text, name=self._get_hotkey_display_name(conflict_with)))')
text = text.replace('status_label.setToolTip("有效")', 'status_label.setToolTip(tr("有效"))')
settings_path.write_text(text, encoding="utf-8")

main_path = Path(r"C:\Users\admin\Desktop\ff\截图贴图工具\screenshot_tool\ui\main_window.py")
text = main_path.read_text(encoding="utf-8")
if 'from core.i18n import tr' not in text:
    text = text.replace('from ui.icons import set_window_icon\n', 'from ui.icons import set_window_icon\nfrom core.i18n import tr\n')
repls = {
    'print(f"加载头像失败: {e}")':'print(tr("加载头像失败: {error}").format(error=e))',
    'self.setWindowTitle("截图贴图工具")':'self.setWindowTitle(tr("截图贴图工具"))',
    'logo_text = QLabel("截图贴图工具")':'logo_text = QLabel(tr("截图贴图工具"))',
    'self.return_preview_btn = SidebarButton("↩️ 返回预览")':'self.return_preview_btn = SidebarButton(tr("↩️ 返回预览"))',
    'self.return_preview_btn.setToolTip("返回上次的预览状态")':'self.return_preview_btn.setToolTip(tr("返回上次的预览状态"))',
    '("🏠 主页", self.show_home),':'(tr("🏠 主页"), self.show_home),',
    '("📄 新建", self.new_image),':'(tr("📄 新建"), self.new_image),',
    '("📂 打开", self.open_file),':'(tr("📂 打开"), self.open_file),',
    '("✂️ 截图", self.start_capture),':'(tr("✂️ 截图"), self.start_capture),',
    '("🎨 白板", self.start_whiteboard),':'(tr("🎨 白板"), self.start_whiteboard),',
    '("📌 贴图", self.start_paste),':'(tr("📌 贴图"), self.start_paste),',
    '("👤 登录", self.show_login),':'(tr("👤 登录"), self.show_login),',
}
for old, new in repls.items():
    text = text.replace(old, new)
main_path.write_text(text, encoding="utf-8")
print('patched')
