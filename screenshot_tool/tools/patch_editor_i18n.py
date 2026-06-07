from pathlib import Path

p = Path(r"C:\Users\admin\Desktop\ff\截图贴图工具\screenshot_tool\ui\editor_window.py")
text = p.read_text(encoding="utf-8")
if 'from core.i18n import tr' not in text:
    text = text.replace('from tools.palette import PaletteWindow\n', 'from tools.palette import PaletteWindow\nfrom core.i18n import tr\n')
repls = {
    'self.setWindowTitle("图像编辑器 - PyScreenshot")':'self.setWindowTitle(tr("图像编辑器 - PyScreenshot"))',
    'self._add_image_tab(pixmap, title="新建图像")':'self._add_image_tab(pixmap, title=tr("新建图像"))',
    'f"尺寸: {s.width()}×{s.height()} | {tab_data.title}"':'tr("尺寸: {width}×{height} | {title}").format(width=s.width(), height=s.height(), title=tab_data.title)',
    'tab_icons = {"文件": "📄", "编辑": "✏️", "绘图": "🎨", "效果": "✨"}':'tab_icons = {tr("文件"): "📄", tr("编辑"): "✏️", tr("绘图"): "🎨", tr("效果"): "✨"}',
    'for tab_name in ["文件", "编辑", "绘图", "效果"]:':'for tab_name in [tr("文件"), tr("编辑"), tr("绘图"), tr("效果")]:',
    'self.ribbon_tabs["编辑"].setChecked(True)':'self.ribbon_tabs[tr("编辑")].setChecked(True)',
    'tab_index = {"文件": 0, "编辑": 1, "绘图": 2, "效果": 3}.get(tab_name, 1)':'tab_index = {tr("文件"): 0, tr("编辑"): 1, tr("绘图"): 2, tr("效果"): 3}.get(tab_name, 1)',
    'return_group = self._create_ribbon_group_frame("返回")':'return_group = self._create_ribbon_group_frame(tr("返回"))',
    'return_btn = self._create_ribbon_tool("返回", "返回主界面", btn_style, large=True)':'return_btn = self._create_ribbon_tool(tr("返回"), tr("返回主界面"), btn_style, large=True)',
    'file_group = self._create_ribbon_group_frame("文件")':'file_group = self._create_ribbon_group_frame(tr("文件"))',
    'new_btn = self._create_ribbon_tool("新建", "新建图像", btn_style)':'new_btn = self._create_ribbon_tool(tr("新建"), tr("新建图像"), btn_style)',
    'open_btn = self._create_ribbon_tool("打开", "打开文件", btn_style)':'open_btn = self._create_ribbon_tool(tr("打开"), tr("打开文件"), btn_style)',
    'save_btn = self._create_ribbon_tool("保存", "保存 Ctrl+S", btn_style, large=True)':'save_btn = self._create_ribbon_tool(tr("保存"), tr("保存 Ctrl+S"), btn_style, large=True)',
    'saveas_btn = self._create_ribbon_tool("另存为", "另存为", btn_style)':'saveas_btn = self._create_ribbon_tool(tr("另存为"), tr("另存为"), btn_style)',
    'share_group = self._create_ribbon_group_frame("分享")':'share_group = self._create_ribbon_group_frame(tr("分享"))',
    'share_btn = self._create_ribbon_tool("分享", "分享到...", btn_style, large=True)':'share_btn = self._create_ribbon_tool(tr("分享"), tr("分享到..."), btn_style, large=True)',
    'batch_btn = self._create_ribbon_tool("批量", "批量导出所有标签页", btn_style)':'batch_btn = self._create_ribbon_tool(tr("批量"), tr("批量导出所有标签页"), btn_style)',
    'print_group = self._create_ribbon_group_frame("打印")':'print_group = self._create_ribbon_group_frame(tr("打印"))',
    'print_btn = self._create_ribbon_tool("打印", "打印 Ctrl+P", btn_style, large=True)':'print_btn = self._create_ribbon_tool(tr("打印"), tr("打印 Ctrl+P"), btn_style, large=True)',
    'action_group = self._create_ribbon_group_frame("操作")':'action_group = self._create_ribbon_group_frame(tr("操作"))',
    'undo_btn = self._create_ribbon_tool("撤销", "撤销上一步操作", btn_style)':'undo_btn = self._create_ribbon_tool(tr("撤销"), tr("撤销上一步操作"), btn_style)',
    'reset_btn = self._create_ribbon_tool("重置", "恢复为原始图像", btn_style)':'reset_btn = self._create_ribbon_tool(tr("重置"), tr("恢复为原始图像"), btn_style)',
    'self, "打开图像", "",':'self, tr("打开图像"), "",',
    '"图像文件 (*.png *.jpg *.jpeg *.bmp *.gif);;所有文件 (*.*)"':'tr("图像文件 (*.png *.jpg *.jpeg *.bmp *.gif);;所有文件 (*.*)")',
    'ModernMessageBox.warning(self, "错误", "无法打开该图像文件")':'ModernMessageBox.warning(self, tr("错误"), tr("无法打开该图像文件"))',
    'history_group = self._create_ribbon_group_frame("历史")':'history_group = self._create_ribbon_group_frame(tr("历史"))',
    'clip_group = self._create_ribbon_group_frame("剪贴板")':'clip_group = self._create_ribbon_group_frame(tr("剪贴板"))',
    'transform_group = self._create_ribbon_group_frame("变换")':'transform_group = self._create_ribbon_group_frame(tr("变换"))',
    'crop_group = self._create_ribbon_group_frame("裁剪")':'crop_group = self._create_ribbon_group_frame(tr("裁剪"))',
    'ocr_group = self._create_ribbon_group_frame("文字识别")':'ocr_group = self._create_ribbon_group_frame(tr("文字识别"))',
    'select_group = self._create_ribbon_group_frame("选择")':'select_group = self._create_ribbon_group_frame(tr("选择"))',
    'pen_group = self._create_ribbon_group_frame("画笔")':'pen_group = self._create_ribbon_group_frame(tr("画笔"))',
    'shape_group = self._create_ribbon_group_frame("形状")':'shape_group = self._create_ribbon_group_frame(tr("形状"))',
    'text_group = self._create_ribbon_group_frame("文本")':'text_group = self._create_ribbon_group_frame(tr("文本"))',
    'size_group = self._create_ribbon_group_frame("大小")':'size_group = self._create_ribbon_group_frame(tr("大小"))',
    'size_layout.addWidget(QLabel("宽度:"))':'size_layout.addWidget(QLabel(tr("宽度:")))',
    'size_layout.addWidget(QLabel("字号:"))':'size_layout.addWidget(QLabel(tr("字号:")))',
    'color_group = self._create_ribbon_group_frame("颜色")':'color_group = self._create_ribbon_group_frame(tr("颜色"))',
    'self.color_btn.setToolTip("当前颜色 - 点击选择")':'self.color_btn.setToolTip(tr("当前颜色 - 点击选择"))',
    'self._stroke_mode_action = QAction("擦除描边", menu)':'self._stroke_mode_action = QAction(tr("擦除描边"), menu)',
    'self._area_mode_action = QAction("局部擦除", menu)':'self._area_mode_action = QAction(tr("局部擦除"), menu)',
    'size_layout.addWidget(QLabel("大小:"))':'size_layout.addWidget(QLabel(tr("大小:")))',
    'effects_group = self._create_ribbon_group_frame("基础效果")':'effects_group = self._create_ribbon_group_frame(tr("基础效果"))',
    'local_group = self._create_ribbon_group_frame("局部效果")':'local_group = self._create_ribbon_group_frame(tr("局部效果"))',
    'panel_group = self._create_ribbon_group_frame("面板")':'panel_group = self._create_ribbon_group_frame(tr("面板"))',
    'self.statusBar().showMessage(f"✓ 已应用 {effect} 效果", 2000)':'self.statusBar().showMessage(tr("✓ 已应用 {effect} 效果").format(effect=effect), 2000)',
    'self.statusBar().showMessage(f"✗ 效果应用失败: {str(e)}", 3000)':'self.statusBar().showMessage(tr("✗ 效果应用失败: {error}").format(error=str(e)), 3000)',
    'self._add_image_tab(pixmap, None, "粘贴的图像")':'self._add_image_tab(pixmap, None, tr("粘贴的图像"))',
    'self.statusBar().showMessage("✓ 已粘贴图像", 2000)':'self.statusBar().showMessage(tr("✓ 已粘贴图像"), 2000)',
    'self.statusBar().showMessage("剪贴板中没有图像", 2000)':'self.statusBar().showMessage(tr("剪贴板中没有图像"), 2000)',
}
for old, new in repls.items():
    text = text.replace(old, new)
p.write_text(text, encoding='utf-8')
print('patched')
