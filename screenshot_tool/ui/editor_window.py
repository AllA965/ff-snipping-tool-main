"""
图像编辑器窗口 - 双行工具栏版本 + 标签页管理
"""
import os
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QToolButton, QLabel, QFileDialog, QSpinBox, QStatusBar, QApplication,
    QSlider, QFrame, QDialog,
    QPushButton, QDockWidget, QMenu, QStackedWidget,
    QWidgetAction
)
from PySide6.QtCore import Qt, Signal, QPoint, QRect, QTimer
from PySide6.QtGui import (
    QPixmap, QColor, QImage, QAction, QTransform, QPainter, QBrush, QFont
)

from core.history_manager import HistoryManager, RecentFoldersManager
from core.temp_storage import TempStorageManager
from core.preview_cache import get_preview_cache_manager
from ui.modern_dialog import ModernMessageBox
from ui.tab_manager import TabManager
from ui.save_dialog import EnhancedSaveDialog, BatchExportDialog
from ui.history_panel import HistoryPanel
from ui.ad_widget import AdWidget
from ui.icons import set_window_icon
from ui.styles import MODERN_SPINBOX_STYLE
from tools.palette import PaletteWindow
from core.i18n import tr

# 从拆分后的文件导入组件
from ui.drawing_canvas import DrawingCanvas
from ui.editor_panels import EffectsPanel, AdjustmentsPanel


class EditorWindow(QMainWindow):
    """图像编辑器 - 全屏优化增强版"""

    closed = Signal()
    preview_saved = Signal(str)  # 预览已保存信号，参数为cache_id

    def __init__(self, pixmap, config, file_path: str = None):
        super().__init__()
        self.config = config
        
        # 统一存储为 QImage 以支持大图
        if isinstance(pixmap, QPixmap):
            self.pixmap = pixmap.toImage()
        else:
            self.pixmap = pixmap
            
        self.current_file_path = file_path
        self.current_color = QColor(255, 0, 0)
        self.is_modified = False
        
        # 初始化管理器
        self.history_manager = HistoryManager(config.config_dir)
        self.recent_folders = RecentFoldersManager(config.config_dir)
        self.temp_storage = TempStorageManager(config.config_dir)
        
        # 标签页管理
        self.tab_manager = None
        self.canvases = {}  # tab_id -> DrawingCanvas
        
        # 自动保存定时器
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self._auto_save_temp)
        self.auto_save_timer.start(5000)  # 每5秒自动保存一次

        self.setup_ui()
        
        # 添加初始标签页
        if pixmap and not pixmap.isNull():
            self._add_image_tab(pixmap, file_path)

    def setup_ui(self):
        self.setWindowTitle(tr("图像编辑器 - PyScreenshot"))
        
        # 设置窗口图标
        self._set_window_icon()

        # 全屏或最大化显示
        screen = QApplication.primaryScreen().geometry()
        
        if self.config.get("editor_fullscreen", True):
            self.setGeometry(0, 0, screen.width(), screen.height())
        else:
            last_size = self.config.get("editor_last_size")
            if last_size:
                self.setGeometry(last_size[0], last_size[1], last_size[2], last_size[3])
            else:
                self.setGeometry(50, 50, screen.width() - 100, screen.height() - 100)
        
        self.setMinimumSize(1500, 800)

        # 应用现代美化样式
        from ui.styles import EDITOR_STYLE_LIGHT
        self.setStyleSheet(EDITOR_STYLE_LIGHT + """
            QLabel {
                font-size: 13px;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #d0d0d0;
                border-radius: 5px;
                min-height: 30px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: #b0b0b0;
            }
            QScrollBar:horizontal {
                background: transparent;
                height: 10px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #d0d0d0;
                border-radius: 5px;
                min-width: 30px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #b0b0b0;
            }
            QScrollBar::add-line, QScrollBar::sub-line {
                background: none;
                border: none;
            }
            
            /* 侧边栏停靠组件美化 */
            QDockWidget {
                border: none;
                background: #ffffff;
            }
            QDockWidget::title {
                background: #f8f9fa;
                padding: 10px 15px;
                border-bottom: 1px solid #eaeaea;
                font-weight: 600;
                color: #333;
            }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 创建标签页管理器
        self.tab_manager = TabManager()
        self.tab_manager.current_tab_changed.connect(self._on_tab_changed)
        self.tab_manager.all_tabs_closed.connect(self.close)
        self.tab_manager.new_tab_requested.connect(self._on_new_tab_requested)
        layout.addWidget(self.tab_manager)

        self._create_toolbar(layout)
        self._create_canvas_area(layout)
        self._create_statusbar()
        self._create_side_panels()
    
    def _set_window_icon(self):
        """设置窗口图标"""
        set_window_icon(self)
    
    def _add_image_tab(self, pixmap, file_path: str = None, title: str = None) -> str:
        """添加图像标签页"""
        tab_id = self.tab_manager.add_tab(pixmap, file_path, title)
        
        # 创建对应的画布
        canvas = DrawingCanvas(pixmap)
        self.canvases[tab_id] = canvas
        
        # 连接文本框创建完成信号
        canvas.text_box_created.connect(self._on_text_box_created)
        # 连接 OCR 选区完成信号
        canvas.ocr_selection_done.connect(self._on_ocr_selection_done)
        
        # 添加到 QStackedWidget
        if hasattr(self, 'canvas_stack'):
            self.canvas_stack.addWidget(canvas)
        
        # 切换到新画布
        self._switch_canvas(tab_id)
        
        return tab_id
    
    def _on_tab_changed(self, tab_id: str):
        """标签页切换"""
        self._switch_canvas(tab_id)
    
    def _on_new_tab_requested(self):
        """处理新建标签页请求"""
        # 创建一个默认大小的空白画布 (1200x800)
        pixmap = QPixmap(1200, 800)
        pixmap.fill(Qt.GlobalColor.white)
        self._add_image_tab(pixmap, title=tr("新建图像"))
    
    def _switch_canvas(self, tab_id: str):
        """切换画布"""
        if tab_id not in self.canvases:
            return
        
        # 保存当前画布状态
        if hasattr(self, 'canvas') and self.canvas and hasattr(self, 'tab_manager'):
            current_tab = self.tab_manager.current_tab_id
            if current_tab and current_tab in self.canvases and current_tab != tab_id:
                # 更新标签数据
                self.tab_manager.update_tab_pixmap(current_tab, self.canvas.get_pixmap())
        
        # 切换到新画布
        self.canvas = self.canvases[tab_id]
        
        # 同步当前的工具设置到新画布
        if hasattr(self, 'current_tool'):
            self.canvas.set_tool(self.current_tool)
        if hasattr(self, 'current_color'):
            self.canvas.set_color(self.current_color)
        if hasattr(self, 'pen_width'):
            self.canvas.set_pen_width(self.pen_width)
        if hasattr(self, 'eraser_size_slider'):
            self.canvas.set_eraser_size(self.eraser_size_slider.value())
        if hasattr(self, '_area_mode_action') and hasattr(self, '_stroke_mode_action'):
            mode = 'area' if self._area_mode_action.isChecked() else 'stroke'
            self.canvas.set_eraser_mode(mode)
        
        # 使用 QStackedWidget 切换画布
        if hasattr(self, 'canvas_stack'):
            # 找到画布在 stack 中的索引
            for i in range(self.canvas_stack.count()):
                if self.canvas_stack.widget(i) == self.canvas:
                    self.canvas_stack.setCurrentIndex(i)
                    break
        
        # 更新状态栏
        if hasattr(self, 'tab_manager'):
            tab_data = self.tab_manager.get_tab_data(tab_id)
            if tab_data:
                s = tab_data.current_pixmap.size()
                self.statusBar().showMessage(
                    tr("尺寸: {width}×{height} | {title}").format(width=s.width(), height=s.height(), title=tab_data.title)
                )
    
    def _create_canvas_area(self, layout):
        """创建画布区域（支持标签页切换）- PicPick 风格"""
        # 创建滚动区域容器
        scroll_container = QFrame()
        scroll_container.setStyleSheet("""
            QFrame {
                background: #e9eaed;
                border: none;
            }
        """)
        
        scroll_layout = QVBoxLayout(scroll_container)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标尺区域（顶部）- PicPick 风格
        self.ruler_widget = self._create_ruler()
        scroll_layout.addWidget(self.ruler_widget)
        
        # 使用 QStackedWidget 来管理多个画布
        self.canvas_stack = QStackedWidget()
        self.canvas_stack.setStyleSheet("""
            QStackedWidget { 
                background: #d1d4d9;
                border: none;
            }
        """)
        
        # 不创建初始画布，等待标签页添加时创建
        self.canvas = None
        scroll_layout.addWidget(self.canvas_stack, 1)
        
        layout.addWidget(scroll_container, 1)
    
    def _create_ruler(self) -> QWidget:
        """创建 PicPick 风格标尺"""
        ruler = QWidget()
        ruler.setFixedHeight(24)
        ruler.setStyleSheet("""
            QWidget {
                background: #ffffff;
                border-bottom: 1px solid #eaeaea;
            }
        """)
        
        # 标尺刻度会在 paintEvent 中绘制
        # 这里只是占位
        ruler_layout = QHBoxLayout(ruler)
        ruler_layout.setContentsMargins(0, 0, 0, 0)
        
        ruler_label = QLabel("0        100       200       300       400       500       600       700       800       900       1000")
        ruler_label.setStyleSheet("color: #888; font-size: 9px; font-family: Consolas;")
        ruler_layout.addWidget(ruler_label)
        
        return ruler

    def _create_toolbar(self, layout):
        """创建 PicPick 风格 Ribbon 工具栏 - 带选项卡"""
        # 主工具栏容器
        toolbar_container = QFrame()
        toolbar_container.setStyleSheet("""
            QFrame { 
                background: #ffffff;
            }
        """)
        
        # 整体改为垂直布局：上方是选项卡，下方是按钮区+广告
        main_toolbar_layout = QVBoxLayout(toolbar_container)
        main_toolbar_layout.setContentsMargins(0, 0, 0, 0)
        main_toolbar_layout.setSpacing(0)
        
        # ========== Ribbon 选项卡栏 ==========
        tab_bar = QFrame()
        tab_bar.setFixedHeight(32)
        tab_bar.setStyleSheet("""
            QFrame { 
                background: #f8f9fa;
                border-bottom: 1px solid #eaeaea;
            }
        """)
        tab_bar_layout = QHBoxLayout(tab_bar)
        tab_bar_layout.setContentsMargins(10, 0, 10, 0)
        tab_bar_layout.setSpacing(5)
        
        # Ribbon 选项卡按钮
        self.ribbon_tabs = {}
        ribbon_tab_style = """
            QPushButton {
                background: transparent;
                border: none;
                padding: 4px 20px 10px 20px;
                font-size: 14px;
                color: #64748b;
                border-radius: 6px 6px 0px 0px;
                margin-top: 2px;
                font-weight: 500;
                min-height: 28px;
            }
            QPushButton:hover { 
                background: #f1f5f9; 
                color: #3b82f6;
            }
            QPushButton:checked { 
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-bottom: 2px solid #3b82f6;
                padding-bottom: 8px;
                color: #2563eb;
                font-weight: 600;
            }
        """
        
        tab_icons = {"文件": "📁", "编辑": "✏️", "绘图": "🎨", "特效": "✨"}
        for tab_name in ["文件", "编辑", "绘图", "特效"]:
            icon = tab_icons.get(tab_name, "")
            btn = QPushButton(f"{icon} {tab_name}")
            btn.setCheckable(True)
            btn.setStyleSheet(ribbon_tab_style)
            btn.clicked.connect(lambda c, n=tab_name: self._on_ribbon_tab_clicked(n))
            tab_bar_layout.addWidget(btn)
            self.ribbon_tabs[tab_name] = btn
        
        tab_bar_layout.addStretch()
        main_toolbar_layout.addWidget(tab_bar)
        
        # ========== Ribbon 下方区域（按钮区 + 广告） ==========
        content_with_ad_widget = QWidget()
        content_with_ad_layout = QHBoxLayout(content_with_ad_widget)
        content_with_ad_layout.setContentsMargins(0, 0, 0, 0)
        content_with_ad_layout.setSpacing(0)
        
        # Ribbon 内容堆栈
        self.ribbon_stack = QStackedWidget()
        self.ribbon_stack.setFixedHeight(60)
        self.ribbon_stack.setStyleSheet("""
            QStackedWidget {
                background: #ffffff;
                border-bottom: 1px solid #eaeaea;
            }
        """)
        
        # 创建各个选项卡内容
        self.ribbon_stack.addWidget(self._create_file_ribbon())      # 0: 文件
        self.ribbon_stack.addWidget(self._create_edit_ribbon())      # 1: 编辑
        self.ribbon_stack.addWidget(self._create_draw_ribbon())      # 2: 绘图
        self.ribbon_stack.addWidget(self._create_effects_ribbon())   # 3: 特效
        
        content_with_ad_layout.addWidget(self.ribbon_stack, 1)
        
        main_toolbar_layout.addWidget(content_with_ad_widget)
        
        # 默认选中"编辑"
        self.ribbon_tabs["编辑"].setChecked(True)
        self.ribbon_stack.setCurrentIndex(1)
        
        layout.addWidget(toolbar_container)
    
    def _on_ribbon_tab_clicked(self, tab_name: str):
        """Ribbon 选项卡点击 - 带有平滑切换效果"""
        current_index = self.ribbon_stack.currentIndex()
        tab_index = {"文件": 0, "编辑": 1, "绘图": 2, "特效": 3}.get(tab_name, 1)
        
        if current_index == tab_index:
            return
            
        for name, btn in self.ribbon_tabs.items():
            btn.setChecked(name == tab_name)
        
        # 切换动画
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        
        # new_widget = self.ribbon_stack.widget(tab_index)
        
        # 简单淡入动画
        # opacity_effect = QGraphicsOpacityEffect(new_widget)
        # new_widget.setGraphicsEffect(opacity_effect)
        
        # self.tab_anim = QPropertyAnimation(opacity_effect, b"opacity")
        # self.tab_anim.setDuration(250)
        # self.tab_anim.setStartValue(0)
        # self.tab_anim.setEndValue(1)
        # self.tab_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.ribbon_stack.setCurrentIndex(tab_index)
        # self.tab_anim.start()
    
    def _create_file_ribbon(self) -> QWidget:
        """创建文件选项卡内容 - 文件操作、分享、打印"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        
        btn_style = self._get_ribbon_btn_style()
        
        # ===== 返回组 =====
        return_group = self._create_ribbon_group_frame(tr("返回"))
        return_layout = return_group.layout()
        
        return_btn = self._create_ribbon_tool(tr("返回"), tr("返回主页面"), btn_style, large=True)
        return_btn.clicked.connect(self._on_return_to_main)
        return_layout.addWidget(return_btn)
        
        layout.addWidget(return_group)
        
        # ===== 文件操作组 =====
        file_group = self._create_ribbon_group_frame(tr("文件"))
        file_layout = file_group.layout()
        
        new_btn = self._create_ribbon_tool(tr("新建"), tr("新建图像"), btn_style)
        new_btn.clicked.connect(self._call_main_new_image)
        file_layout.addWidget(new_btn)
        
        open_btn = self._create_ribbon_tool(tr("打开"), tr("打开文件"), btn_style)
        open_btn.clicked.connect(self._open_file)
        file_layout.addWidget(open_btn)
        
        save_btn = self._create_ribbon_tool(tr("保存"), tr("保存 Ctrl+S"), btn_style, large=True)
        save_btn.clicked.connect(self._save_file)
        file_layout.addWidget(save_btn)
        
        saveas_btn = self._create_ribbon_tool(tr("另存为"), tr("另存为"), btn_style)
        saveas_btn.clicked.connect(self._save_as)
        file_layout.addWidget(saveas_btn)
        
        layout.addWidget(file_group)
        
        # ===== 分享组 =====
        share_group = self._create_ribbon_group_frame(tr("分享"))
        share_layout = share_group.layout()
        
        share_btn = self._create_ribbon_tool(tr("分享"), tr("分享到..."), btn_style, large=True)
        share_btn.clicked.connect(self._show_share_panel)
        share_layout.addWidget(share_btn)
        
        batch_btn = self._create_ribbon_tool("导出", "批量导出所有标签页", btn_style)
        batch_btn.clicked.connect(self._batch_export)
        share_layout.addWidget(batch_btn)
        
        layout.addWidget(share_group)
        
        # ===== 打印组 =====
        print_group = self._create_ribbon_group_frame(tr("打印"))
        print_layout = print_group.layout()
        
        print_btn = self._create_ribbon_tool(tr("打印"), tr("打印 Ctrl+P"), btn_style, large=True)
        print_btn.clicked.connect(self._print)
        print_layout.addWidget(print_btn)
        
        layout.addWidget(print_group)
        
        # ===== 操作组 =====
        action_group = self._create_ribbon_group_frame(tr("操作"))
        action_layout = action_group.layout()
        
        undo_btn = self._create_ribbon_tool(tr("撤销"), tr("撤销上一步操作"), btn_style)
        undo_btn.clicked.connect(self._undo)
        action_layout.addWidget(undo_btn)
        
        reset_btn = self._create_ribbon_tool("重置", "重置为原始图像", btn_style)
        reset_btn.clicked.connect(self._reset_to_original)
        action_layout.addWidget(reset_btn)
        
        layout.addWidget(action_group)
        
        layout.addStretch()
        return widget
    
    def _open_file(self):
        """打开文件"""
        path, _ = QFileDialog.getOpenFileName(
            self, tr("打开图像"), "",
            tr("图像文件 (*.png *.jpg *.jpeg *.bmp *.gif);;所有文件 (*.*)")
        )
        if path:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self._add_image_tab(pixmap, path)
            else:
                ModernMessageBox.warning(self, tr("错误"), tr("无法打开该图像文件"))
    
    def _create_edit_ribbon(self) -> QWidget:
        """创建编辑选项卡内容 - 撤销、剪贴板、变换操作"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        
        btn_style = self._get_ribbon_btn_style()
        
        # ===== 撤销/重置组 =====
        history_group = self._create_ribbon_group_frame(tr("历史"))
        history_layout = history_group.layout()
        
        undo_btn = self._create_ribbon_tool(tr("撤销"), tr("撤销 Ctrl+Z"), btn_style, large=True)
        undo_btn.clicked.connect(self._undo)
        history_layout.addWidget(undo_btn)
        
        reset_btn = self._create_ribbon_tool("重置", "重置到原图 (移除所有编辑)", btn_style, large=True)
        reset_btn.clicked.connect(self._reset_to_original)
        history_layout.addWidget(reset_btn)
        
        layout.addWidget(history_group)
        
        # ===== 剪贴板组 =====
        clip_group = self._create_ribbon_group_frame(tr("剪贴板"))
        clip_layout = clip_group.layout()
        
        copy_btn = self._create_ribbon_tool(tr("复制"), tr("复制 Ctrl+C"), btn_style, large=True)
        copy_btn.clicked.connect(self._copy)
        clip_layout.addWidget(copy_btn)
        
        paste_btn = self._create_ribbon_tool(tr("粘贴"), tr("粘贴 Ctrl+V"), btn_style, large=True)
        paste_btn.clicked.connect(self._paste)
        clip_layout.addWidget(paste_btn)
        
        layout.addWidget(clip_group)
        
        # ===== 变换组 =====
        transform_group = self._create_ribbon_group_frame(tr("变换"))
        transform_layout = transform_group.layout()
        
        rotate_left_btn = self._create_ribbon_tool("左旋", "左旋90度", btn_style)
        rotate_left_btn.clicked.connect(lambda: self._rotate(-90))
        transform_layout.addWidget(rotate_left_btn)
        
        rotate_right_btn = self._create_ribbon_tool("右旋", "右旋90度", btn_style)
        rotate_right_btn.clicked.connect(lambda: self._rotate(90))
        transform_layout.addWidget(rotate_right_btn)
        
        flip_h_btn = self._create_ribbon_tool(tr("水平翻"), tr("水平翻转"), btn_style)
        flip_h_btn.clicked.connect(self._flip_h)
        transform_layout.addWidget(flip_h_btn)
        
        flip_v_btn = self._create_ribbon_tool(tr("垂直翻"), tr("垂直翻转"), btn_style)
        flip_v_btn.clicked.connect(self._flip_v)
        transform_layout.addWidget(flip_v_btn)
        
        layout.addWidget(transform_group)
        
        # ===== 裁剪组 =====
        crop_group = self._create_ribbon_group_frame(tr("裁剪"))
        crop_layout = crop_group.layout()
        
        crop_btn = self._create_ribbon_tool(tr("裁剪"), tr("裁剪图像"), btn_style, checkable=True)
        crop_btn.clicked.connect(self._toggle_crop_mode)
        crop_layout.addWidget(crop_btn)
        self.crop_btn = crop_btn
        
        layout.addWidget(crop_group)

        ocr_group = self._create_ribbon_group_frame(tr("文字识别"))
        ocr_layout = ocr_group.layout()

        ocr_btn = self._create_ribbon_tool("识别文字", "识别裁剪区域文字并复制", btn_style, large=True)
        ocr_btn.clicked.connect(self._ocr_current_selection)
        ocr_layout.addWidget(ocr_btn)

        layout.addWidget(ocr_group)
        
        layout.addStretch()
        return widget
    
    def _create_draw_ribbon(self) -> QWidget:
        """创建绘图选项卡内容 - 绘图工具、形状、颜色"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        
        btn_style = self._get_ribbon_btn_style()
        
        # ===== 选择工具组 =====
        select_group = self._create_ribbon_group_frame(tr("选择"))
        select_layout = select_group.layout()
        
        self.tool_buttons = {}
        
        move_btn = self._create_ribbon_tool("移动", "移动工具", btn_style, checkable=True, large=True)
        move_btn.clicked.connect(lambda c: self._on_tool_selected('move'))
        select_layout.addWidget(move_btn)
        self.tool_buttons['move'] = move_btn
        
        layout.addWidget(select_group)
        
        # ===== 画笔工具组 =====
        pen_group = self._create_ribbon_group_frame(tr("画笔"))
        pen_layout = pen_group.layout()
        
        pen_tools = [
            (tr("画笔"), tr("画笔"), "pen"),
            (tr("荧光笔"), tr("荧光笔"), "highlighter"),
        ]
        
        for icon, tip, tool in pen_tools:
            btn = self._create_ribbon_tool(icon, tip, btn_style, checkable=True)
            btn.clicked.connect(lambda c, t=tool: self._on_tool_selected(t))
            pen_layout.addWidget(btn)
            self.tool_buttons[tool] = btn
        
        # 橡皮擦按钮 - 带选项面板
        eraser_btn = self._create_ribbon_tool(tr("橡皮擦"), tr("橡皮擦"), btn_style, checkable=True)
        eraser_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        eraser_btn.setStyleSheet(eraser_btn.styleSheet() + "QToolButton::menu-indicator { image: none; }")
        # 当菜单弹出时，自动切换到橡皮擦工具
        eraser_btn.pressed.connect(lambda: self._on_tool_selected('eraser'))
        pen_layout.addWidget(eraser_btn)
        self.tool_buttons['eraser'] = eraser_btn
        
        # 创建橡皮选项菜单
        self._create_eraser_options_menu(eraser_btn)
        
        layout.addWidget(pen_group)
        
        # ===== 形状工具组 =====
        shape_group = self._create_ribbon_group_frame(tr("形状"))
        shape_layout = shape_group.layout()
        
        shape_tools = [
            (tr("箭头"), tr("箭头"), "arrow"),
            (tr("直线"), tr("直线"), "line"),
            (tr("矩形"), tr("空心矩形"), "rect"),
            (tr("实心矩形"), tr("填充矩形"), "filled_rect"),
            (tr("椭圆"), tr("空心椭圆"), "ellipse"),
            (tr("实心椭圆"), tr("填充椭圆"), "filled_ellipse"),
        ]
        
        for icon, tip, tool in shape_tools:
            btn = self._create_ribbon_tool(icon, tip, btn_style, checkable=True)
            btn.clicked.connect(lambda c, t=tool: self._on_tool_selected(t))
            shape_layout.addWidget(btn)
            self.tool_buttons[tool] = btn
        
        layout.addWidget(shape_group)
        
        # ===== 文字工具组 =====
        text_group = self._create_ribbon_group_frame("文字")
        text_layout = text_group.layout()
        
        text_btn = self._create_ribbon_tool("文字", "添加文字", btn_style, checkable=True, large=True)
        text_btn.clicked.connect(lambda c: self._on_tool_selected('text'))
        text_layout.addWidget(text_btn)
        self.tool_buttons['text'] = text_btn
        
        layout.addWidget(text_group)
        
        # ===== 大小组 =====
        size_group = self._create_ribbon_group_frame(tr("大小"))
        size_layout = size_group.layout()
        
        spin_style = MODERN_SPINBOX_STYLE
        
        size_layout.addWidget(QLabel(tr("宽度:")))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 100)  # 笔触宽度
        self.width_spin.setValue(3)
        self.width_spin.setFixedWidth(70)
        self.width_spin.setStyleSheet(spin_style)
        self.width_spin.valueChanged.connect(self._on_width_changed)
        size_layout.addWidget(self.width_spin)
        
        size_layout.addWidget(QLabel(tr("字号:")))
        self.font_spin = QSpinBox()
        self.font_spin.setRange(8, 72)
        self.font_spin.setValue(16)
        self.font_spin.setFixedWidth(70)
        self.font_spin.setStyleSheet(spin_style)
        self.font_spin.valueChanged.connect(self._on_font_size_changed)
        size_layout.addWidget(self.font_spin)
        
        layout.addWidget(size_group)
        
        # ===== 颜色组 =====
        color_group = self._create_ribbon_group_frame(tr("颜色"))
        color_layout = color_group.layout()
        
        self.color_btn = QToolButton()
        self.color_btn.setFixedSize(28, 28)
        self.color_btn.setStyleSheet(f"background: {self.current_color.name()}; border: 2px solid #555; border-radius: 4px;")
        self.color_btn.clicked.connect(self._select_color)
        self.color_btn.setToolTip(tr("当前颜色 - 点击选择"))
        color_layout.addWidget(self.color_btn)
        
        # 快速颜色选择
        quick_colors = ["#000000", "#FF0000", "#00FF00", "#0000FF", "#FFFF00", 
                        "#FF00FF", "#00FFFF", "#FFFFFF", "#808080", "#FFA500"]
        for c in quick_colors:
            btn = QToolButton()
            btn.setFixedSize(16, 16)
            btn.setStyleSheet(f"background: {c}; border: 1px solid #aaa;")
            btn.setToolTip(c)
            btn.clicked.connect(lambda _, col=c: self._set_color(col))
            color_layout.addWidget(btn)
        
        layout.addWidget(color_group)
        
        # ===== 历史组 =====
        history_group = self._create_ribbon_group_frame(tr("历史"))
        history_layout = history_group.layout()
        
        undo_btn = self._create_ribbon_tool(tr("撤销"), tr("撤销 Ctrl+Z"), btn_style, large=True)
        undo_btn.clicked.connect(self._undo)
        history_layout.addWidget(undo_btn)
        
        reset_btn = self._create_ribbon_tool("重置", "重置绘图 (移除所有编辑)", btn_style, large=True)
        reset_btn.clicked.connect(self._reset_to_original)
        history_layout.addWidget(reset_btn)
        
        layout.addWidget(history_group)
        
        # 默认选中移动工具
        self.tool_buttons['move'].setChecked(True)
        
        layout.addStretch()
        return widget

    def _create_eraser_options_menu(self, parent_btn: QToolButton):
        """创建橡皮擦选项菜单"""
        menu = QMenu(parent_btn)
        menu.setStyleSheet("""
            QMenu {
                background: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 15px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #0078D7;
                color: white;
            }
        """)
        
        self._stroke_mode_action = QAction("对象擦除", menu)
        self._stroke_mode_action.setCheckable(True)
        self._stroke_mode_action.setChecked(True)
        self._stroke_mode_action.triggered.connect(lambda: self._on_eraser_mode_changed('stroke', menu, self._stroke_mode_action, self._area_mode_action))
        menu.addAction(self._stroke_mode_action)
        
        self._area_mode_action = QAction(tr("局部擦除"), menu)
        self._area_mode_action.setCheckable(True)
        self._area_mode_action.triggered.connect(lambda: self._on_eraser_mode_changed('area', menu, self._stroke_mode_action, self._area_mode_action))
        menu.addAction(self._area_mode_action)
        
        menu.addSeparator()
        
        size_widget = QWidget(menu)
        size_layout = QHBoxLayout(size_widget)
        size_layout.setContentsMargins(5, 5, 5, 5)
        size_layout.setSpacing(5)
        
        size_layout.addWidget(QLabel(tr("大小:")))
        self.eraser_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.eraser_size_slider.setRange(5, 100)
        self.eraser_size_slider.setValue(20)
        self.eraser_size_slider.setFixedWidth(100)
        self.eraser_size_slider.valueChanged.connect(self._on_eraser_size_changed)
        size_layout.addWidget(self.eraser_size_slider)
        
        self.eraser_size_label = QLabel("20")
        self.eraser_size_label.setFixedWidth(25)
        size_layout.addWidget(self.eraser_size_label)
        
        size_action = QWidgetAction(menu)
        size_action.setDefaultWidget(size_widget)
        menu.addAction(size_action)
        
        parent_btn.setMenu(menu)
        
        self._eraser_menu = menu

    def _on_eraser_mode_changed(self, mode: str, menu: QMenu, stroke_action: QAction, area_action: QAction):
        """橡皮擦模式切换"""
        if mode == 'stroke':
            stroke_action.setChecked(True)
            area_action.setChecked(False)
        else:
            stroke_action.setChecked(False)
            area_action.setChecked(True)
        
        if self.canvas:
            self.canvas.set_eraser_mode(mode)
        
        if hasattr(self, 'tool_buttons') and 'eraser' in self.tool_buttons:
            self.tool_buttons['eraser'].setChecked(True)
        self._on_tool_selected('eraser')
        
        menu.hide()

    def _on_eraser_size_changed(self, value: int):
        """橡皮擦大小改变"""
        if hasattr(self, 'eraser_size_label'):
            self.eraser_size_label.setText(str(value))
        if self.canvas:
            self.canvas.set_eraser_size(value)
            self.canvas.eraser_size = value

    def _create_effects_ribbon(self) -> QWidget:
        """创建特效选项卡内容 - 画质特效、色彩调整"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        
        btn_style = self._get_ribbon_btn_style()
        
        # ===== 画质特效组 =====
        effects_group = self._create_ribbon_group_frame("画质特效")
        effects_layout = effects_group.layout()
        
        blur_btn = self._create_ribbon_tool(tr("模糊"), tr("模糊效果"), btn_style)
        blur_btn.clicked.connect(lambda: self._apply_quick_effect("blur"))
        effects_layout.addWidget(blur_btn)
        
        sharpen_btn = self._create_ribbon_tool(tr("锐化"), tr("锐化效果"), btn_style)
        sharpen_btn.clicked.connect(lambda: self._apply_quick_effect("sharpen"))
        effects_layout.addWidget(sharpen_btn)
        
        pixelate_btn = self._create_ribbon_tool(tr("像素化"), tr("像素化效果"), btn_style)
        pixelate_btn.clicked.connect(lambda: self._apply_quick_effect("pixelate"))
        effects_layout.addWidget(pixelate_btn)
        
        emboss_btn = self._create_ribbon_tool(tr("浮雕"), tr("浮雕效果"), btn_style)
        emboss_btn.clicked.connect(lambda: self._apply_quick_effect("emboss"))
        effects_layout.addWidget(emboss_btn)
        
        noise_btn = self._create_ribbon_tool(tr("噪点"), tr("添加噪点"), btn_style)
        noise_btn.clicked.connect(lambda: self._apply_quick_effect("noise"))
        effects_layout.addWidget(noise_btn)
        
        layout.addWidget(effects_group)
        
        # ===== 局部特效组 =====
        local_group = self._create_ribbon_group_frame("局部特效")
        local_layout = local_group.layout()
        
        blur_brush_btn = self._create_ribbon_tool(tr("模糊笔刷"), tr("局部模糊"), btn_style, checkable=True)
        blur_brush_btn.clicked.connect(lambda c: self._on_tool_selected('blur_brush'))
        local_layout.addWidget(blur_brush_btn)
        if hasattr(self, 'tool_buttons'):
            self.tool_buttons['blur_brush'] = blur_brush_btn
        
        pixelate_brush_btn = self._create_ribbon_tool("马赛克", "局部马赛克", btn_style, checkable=True)
        pixelate_brush_btn.clicked.connect(lambda c: self._on_tool_selected('pixelate_brush'))
        local_layout.addWidget(pixelate_brush_btn)
        if hasattr(self, 'tool_buttons'):
            self.tool_buttons['pixelate_brush'] = pixelate_brush_btn
        
        layout.addWidget(local_group)
        
        # ===== 面板组 =====
        panel_group = self._create_ribbon_group_frame(tr("面板"))
        panel_layout = panel_group.layout()
        
        self.adjust_btn = self._create_ribbon_tool("色彩", "打开色彩调整面板", btn_style, checkable=True)
        self.adjust_btn.clicked.connect(self._toggle_adjustments_panel)
        panel_layout.addWidget(self.adjust_btn)
        
        self.effects_btn = self._create_ribbon_tool("特效", "打开特效面板", btn_style, checkable=True)
        self.effects_btn.clicked.connect(self._toggle_effects_panel)
        panel_layout.addWidget(self.effects_btn)
        
        layout.addWidget(panel_group)
        
        # ===== 历史组 =====
        history_group = self._create_ribbon_group_frame(tr("历史"))
        history_layout = history_group.layout()
        
        undo_btn = self._create_ribbon_tool("撤销", "撤销 Ctrl+Z", btn_style)
        undo_btn.clicked.connect(self._undo)
        history_layout.addWidget(undo_btn)
        
        reset_btn = self._create_ribbon_tool("重置", "重置特效", btn_style)
        reset_btn.clicked.connect(self._reset_to_original)
        history_layout.addWidget(reset_btn)
        
        layout.addWidget(history_group)
        
        layout.addStretch()
        return widget
    
    def _apply_quick_effect(self, effect: str):
        """快速应用特效"""
        if not self.canvas or not self.canvas.current_pixmap or self.canvas.current_pixmap.isNull():
            return
        
        try:
            if effect == "blur":
                self.canvas.apply_blur(5)
            elif effect == "sharpen":
                self.canvas.apply_sharpen()
            elif effect == "pixelate":
                self.canvas.apply_pixelate(10)
            elif effect == "emboss":
                self.canvas.apply_emboss()
            elif effect == "noise":
                self.canvas.add_noise(30)
            self.is_modified = True
            self.statusBar().showMessage(f"✓ 已应用 {effect} 特效", 2000)
        except Exception as e:
            self.statusBar().showMessage(f"✗ 特效应用失败: {str(e)}", 3000)
    
    def _paste(self):
        """粘贴剪贴板图像"""
        clipboard = QApplication.clipboard()
        pixmap = clipboard.pixmap()
        if pixmap and not pixmap.isNull():
            self._add_image_tab(pixmap, None, tr("粘贴的图像"))
            self.statusBar().showMessage(tr("✓ 已粘贴图像"), 2000)
        else:
            self.statusBar().showMessage(tr("剪贴板中没有图像"), 2000)
    

    
    def _get_ribbon_btn_style(self) -> str:
        return """
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 3px;
                color: #333;
                font-size: 14px;
                padding: 3px 5px;
                min-width: 38px;
            }
            QToolButton:hover { background: #e5f3ff; border-color: #cce8ff; }
            QToolButton:pressed, QToolButton:checked { background: #cce8ff; border-color: #0078d7; }
        """
    
    def _get_tool_icon(self, text: str) -> str:
        """获取工具对应的图标"""
        icons = {
            # 文件操作
            "返回": "←", "新建": "📄", "打开": "📂", "保存": "💾", "另存为": "📋",
            "分享": "📤", "导出": "📦", "打印": "🖨",
            # 编辑操作
            "撤销": "↩", "重置": "🔄", "复制": "📋", "粘贴": "📌", "裁剪": "✂",
            # 变换
            "左旋": "↺", "右旋": "↻", "水平翻": "⇔", "垂直翻": "⇕",
            # 绘图工具
            "移动": "☐", "画笔": "✎", "荧光笔": "▬", "橡皮擦": "◇", "文字": "T",
            "箭头": "→", "直线": "/", "矩形": "□", "实心矩形": "■", 
            "椭圆": "○", "实心椭圆": "●", "清除": "✕",
            # 特效
            "模糊": "◎", "锐化": "✦", "像素化": "▦", "浮雕": "◈", "噪点": "▒",
            "模糊笔刷": "◐", "马赛克": "▣", "色彩": "◕", "特效": "✧",
        }
        return icons.get(text, "")
    
    def _create_ribbon_tool(self, text: str, tooltip: str, style: str, 
                            checkable: bool = False, large: bool = False) -> QToolButton:
        btn = QToolButton()
        icon = self._get_tool_icon(text)
        
        # 统一使用紧凑横排模式，适应 60px 高度
        btn.setText(f"{icon} {text}" if icon else text)
        btn.setToolTip(tooltip)
        btn.setCheckable(checkable)
        btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                color: #444;
                font-size: 12px;
                padding: 3px 8px 5px 8px;
            }
            QToolButton:hover { 
                background: #f0f7ff; 
                border: 1px solid #d0e7ff; 
                color: #0078d7;
            }
            QToolButton:pressed, QToolButton:checked { 
                background: #e1efff; 
                border: 1px solid #0078d7; 
                color: #005a9e;
            }
        """)
        return btn
    
    def _create_ribbon_group_frame(self, title: str) -> QFrame:
        """创建现代化的 Ribbon 分组框架 - 简化版（移除标题和边框）"""
        frame = QFrame()
        # 直接使用水平布局，移除所有额外的装饰和标题
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        
        # 为了兼容现有代码调用 layout() 的方式
        frame.layout = lambda: layout
        return frame
    
    def _create_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(50)
        sep.setStyleSheet("background: #d0d0d0; margin: 8px 4px;")
        return sep
    
    def _create_color_palette(self) -> QVBoxLayout:
        """创建 PicPick 风格颜色调色板 - 网格布局美化版"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)
        
        # PicPick 风格颜色 - 2行10列
        color_rows = [
            # 第一行 - 基础色
            ["#000000", "#7F7F7F", "#880015", "#ED1C24", "#FF7F27", 
             "#FFF200", "#22B14C", "#00A2E8", "#3F48CC", "#A349A4"],
            # 第二行 - 浅色
            ["#FFFFFF", "#C3C3C3", "#B97A57", "#FFAEC9", "#FFC90E",
             "#EFE4B0", "#B5E61D", "#99D9EA", "#7092BE", "#C8BFE7"],
        ]
        
        for row_colors in color_rows:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(2)
            row_layout.setContentsMargins(0, 0, 0, 0)
            
            for color in row_colors:
                btn = QToolButton()
                btn.setFixedSize(14, 14)
                btn.setStyleSheet(f"""
                    QToolButton {{
                        background: {color};
                        border: 1px solid #d0d0d0;
                        border-radius: 2px;
                    }}
                    QToolButton:hover {{
                        border: 1.5px solid #0078d7;
                    }}
                """)
                btn.setToolTip(color)
                btn.clicked.connect(lambda _, c=color: self._set_color(c))
                row_layout.addWidget(btn)
            
            main_layout.addLayout(row_layout)
        
        return main_layout

    def _add_sep(self, layout):
        """添加分隔符"""
        sep = QFrame()
        sep.setFixedSize(1, 24)
        sep.setStyleSheet("background: #d0d0d0;")
        layout.addWidget(sep)

    def _create_statusbar(self):
        """创建 PicPick 风格状态栏 - 现代美化版"""
        sb = QStatusBar()
        sb.setStyleSheet("""
            QStatusBar {
                background: #ffffff;
                border-top: 1px solid #eaeaea;
                color: #666;
                font-size: 12px;
                padding: 4px 10px;
            }
        """)
        self.setStatusBar(sb)
        
        # 添加坐标显示
        self.coord_label = QLabel(tr("坐标: 0, 0"))
        self.coord_label.setStyleSheet("color: #777; margin-right: 20px; font-weight: 500;")
        sb.addPermanentWidget(self.coord_label)
        
        # 添加尺寸显示
        self.size_label = QLabel()
        self.size_label.setStyleSheet("color: #777; margin-right: 20px; font-weight: 500;")
        sb.addPermanentWidget(self.size_label)
        
        # 添加缩放显示
        self.zoom_label = QLabel("100%")
        self.zoom_label.setStyleSheet("color: #0078d7; font-weight: bold;")
        sb.addPermanentWidget(self.zoom_label)
        
        if self.pixmap and not self.pixmap.isNull():
            s = self.pixmap.size()
            self.size_label.setText(tr("尺寸: {width} × {height}").format(width=s.width(), height=s.height()))
            sb.showMessage(tr("就绪"))
        else:
            self.size_label.setText(tr("尺寸: - × -"))
            sb.showMessage(tr("就绪"))
    
    def _create_side_panels(self):
        """创建侧边面板（改为悬浮窗形式）"""
        
        # 统一的 Dock 样式表
        dock_style = """
            QDockWidget {
                border: 1px solid #d0d0d0;
                titlebar-close-icon: url(ui/icons/close.png);
                titlebar-normal-icon: url(ui/icons/restore.png);
            }
            QDockWidget::title {
                background: #f0f0f0;
                padding-left: 8px;
                padding-top: 4px;
                padding-bottom: 4px;
            }
            QDockWidget::close-button, QDockWidget::float-button {
                background: transparent;
                border: none;
                padding: 2px;
                icon-size: 14px;
            }
            QDockWidget::close-button:hover, QDockWidget::float-button:hover {
                background: #e0e0e0;
                border-radius: 2px;
            }
            QDockWidget::close-button:pressed, QDockWidget::float-button:pressed {
                background: #d0d0d0;
            }
        """

        # 特效面板
        self.effects_dock = QDockWidget("特效", self)
        self.effects_dock.setStyleSheet(dock_style)
        self.effects_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable | QDockWidget.DockWidgetFeature.DockWidgetFloatable | QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.effects_dock.setAllowedAreas(Qt.DockWidgetArea.NoDockWidgetArea)
        self.effects_panel = EffectsPanel()
        self.effects_panel.effect_applied.connect(self._apply_effect)
        self.effects_panel.undo_clicked.connect(self._undo)
        self.effects_panel.reset_clicked.connect(self._reset_to_original)
        self.effects_dock.setWidget(self.effects_panel)
        self.effects_dock.setFloating(True)
        self.effects_dock.visibilityChanged.connect(lambda visible: self.effects_btn.setChecked(visible))
        self.effects_dock.hide()
        
        # 调整面板
        self.adjustments_dock = QDockWidget(tr("调整"), self)
        self.adjustments_dock.setStyleSheet(dock_style)
        self.adjustments_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable | QDockWidget.DockWidgetFeature.DockWidgetFloatable | QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.adjustments_dock.setAllowedAreas(Qt.DockWidgetArea.NoDockWidgetArea)
        self.adjustments_panel = AdjustmentsPanel()
        self.adjustments_panel.adjustment_changed.connect(self._on_adjustment_changed)
        self.adjustments_panel.apply_clicked.connect(self._on_apply_adjustments)
        self.adjustments_panel.reset_clicked.connect(self._on_reset_adjustments)
        self.adjustments_dock.setWidget(self.adjustments_panel)
        self.adjustments_dock.setFloating(True)
        self.adjustments_dock.visibilityChanged.connect(lambda visible: self.adjust_btn.setChecked(visible))
        self.adjustments_dock.hide()


    def _on_tool_selected(self, tool: str):
        for n, b in self.tool_buttons.items():
            b.setChecked(n == tool)
        if self.canvas:
            self.canvas.set_tool(tool)
    
    def _on_text_box_created(self):
        """文本框创建完成后的回调 - 取消文本工具选中状态"""
        # 取消所有工具按钮的选中状态
        for n, b in self.tool_buttons.items():
            b.setChecked(n == 'move')
        # 切换到移动工具
        if self.canvas:
            self.canvas.set_tool('move')

    def _select_color(self):
        """打开调色板窗口选择颜色"""
        color = PaletteWindow.getColor(self.current_color, self, tr("调色板"), self.config)
        if color.isValid():
            self._set_color(color.name())

    def _set_color(self, color: str):
        self.current_color = QColor(color)
        if self.canvas:
            self.canvas.set_color(self.current_color)
        self.color_btn.setStyleSheet(f"background: {color}; border: 2px solid #555; border-radius: 4px;")

    def _rotate(self, angle):
        if self.canvas:
            self.canvas.rotate(angle)
            self.is_modified = True

    def _flip_h(self):
        if self.canvas:
            self.canvas.flip_horizontal()
            self.is_modified = True

    def _flip_v(self):
        if self.canvas:
            self.canvas.flip_vertical()
            self.is_modified = True
    
    def _clear_annotations(self):
        if self.canvas:
            self.canvas.clear_annotations()
            self.statusBar().showMessage("已清除标注", 2000)

    def _copy(self):
        if self.canvas:
            QApplication.clipboard().setPixmap(self.canvas.get_pixmap())
            self.statusBar().showMessage(tr("✓ 已复制到剪贴板"), 3000)

    def _save_file(self):
        """保存文件 - 使用增强保存对话框"""
        if not self.canvas:
            ModernMessageBox.warning(self, "错误", "没有可保存的图像")
            return
        pixmap = self.canvas.get_pixmap()
        default_name = self.config.generate_filename("region")
        
        # 如果已有文件路径，直接保存
        if self.current_file_path and os.path.exists(os.path.dirname(self.current_file_path)):
            try:
                if pixmap.save(self.current_file_path):
                    self.is_modified = False
                    self._update_tab_saved()
                    self._show_toast(tr("✓ 已保存: {name}").format(name=os.path.basename(self.current_file_path)))
                    return
            except Exception:
                pass
        
        #打开增强保存对话框
        dialog = EnhancedSaveDialog(
            pixmap, self.config, self.recent_folders, 
            default_name, self
        )
        if dialog.exec():
            saved_path = dialog.get_saved_path()
            if saved_path:
                self.current_file_path = saved_path
                self.is_modified = False
                self._update_tab_saved()
                
                # 添加到历史记录
                self.history_manager.add_record(saved_path, pixmap)
                
                self._show_toast(tr("✓ 已保存: {name}").format(name=os.path.basename(saved_path)))
    
    def _update_tab_saved(self):
        """更新标签页保存状态"""
        if self.tab_manager and self.tab_manager.current_tab_id:
            self.tab_manager.mark_tab_saved(
                self.tab_manager.current_tab_id, 
                self.current_file_path
            )

    def _save_as(self):
        """另存为 - 使用增强保存对话框"""
        if not self.canvas:
            ModernMessageBox.warning(self, "错误", "没有可保存的图像")
            return
        pixmap = self.canvas.get_pixmap()
        default_name = self.config.generate_filename("region")
        
        dialog = EnhancedSaveDialog(
            pixmap, self.config, self.recent_folders,
            default_name, self
        )
        if dialog.exec():
            saved_path = dialog.get_saved_path()
            if saved_path:
                self.current_file_path = saved_path
                self.is_modified = False
                self._update_tab_saved()
                
                # 添加到历史记录
                self.history_manager.add_record(saved_path, pixmap)
                
                self._show_toast(tr("✓ 已保存: {name}").format(name=os.path.basename(saved_path)))
    
    def _batch_export(self):
        """批量导出所有标签页图像"""
        if not self.tab_manager or self.tab_manager.get_tab_count() == 0:
            ModernMessageBox.information(self, "提示", "没有可导出的图像。")
            return
        
        # 收集所有图像
        images = []
        for tab_data in self.tab_manager.get_all_tabs_data():
            if tab_data.tab_id in self.canvases:
                canvas = self.canvases[tab_data.tab_id]
                images.append((tab_data.title, canvas.get_pixmap()))
        
        if not images:
            ModernMessageBox.information(self, "提示", "没有可导出的图像。")
            return
        
        dialog = BatchExportDialog(images, self.config, self.recent_folders, self)
        dialog.export_completed.connect(self._on_batch_export_completed)
        dialog.exec()
    
    def _on_batch_export_completed(self, saved_paths: list):
        """批量导出完成"""
        for path in saved_paths:
            pixmap = QPixmap(path)
            self.history_manager.add_record(path, pixmap)
    
    def _show_history_panel(self):
        """显示历史记录面板"""
        if not hasattr(self, 'history_dock') or not self.history_dock:
            self.history_dock = QDockWidget(tr("历史记录"), self)
            self.history_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable)
            self.history_panel = HistoryPanel(self.history_manager)
            self.history_panel.edit_file_requested.connect(self._open_history_file)
            self.history_dock.setWidget(self.history_panel)
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.history_dock)
        else:
            if self.history_dock.isVisible():
                self.history_dock.hide()
            else:
                self.history_panel.refresh()
                self.history_dock.show()
    
    def _open_history_file(self, file_path: str):
        """从历史记录打开文件"""
        if os.path.exists(file_path):
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                self._add_image_tab(pixmap, file_path)
        else:
            ModernMessageBox.warning(self, tr("文件不存在"), tr("该文件已被移动或删除。"))

    def _save_pdf(self, path):
        if not self.canvas:
            return
        from PySide6.QtGui import QPdfWriter, QPageSize
        pm = self.canvas.get_pixmap()
        w = QPdfWriter(path)
        w.setPageSize(QPageSize(pm.size()))
        p = QPainter(w)
        p.drawPixmap(0, 0, pm)
        p.end()

    def _show_toast(self, message: str):
        """显示 PicPick 风格 Toast 提示 - 增强美化版"""
        toast = QLabel(message, self)
        toast.setStyleSheet("""
            QLabel {
                background: rgba(0, 120, 215, 0.95);
                color: white;
                padding: 14px 28px;
                border-radius: 25px;
                font-size: 14px;
                font-weight: 500;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
        """)
        toast.adjustSize()
        
        # 居中对齐
        x = (self.width() - toast.width()) // 2
        y = self.height() - 100
        toast.move(x, y)
        
        # 阴影效果
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(toast)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 4)
        toast.setGraphicsEffect(shadow)
        
        # 进场动画 (从下往上淡入)
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QPoint
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        
        opacity_effect = QGraphicsOpacityEffect(toast)
        toast.setGraphicsEffect(opacity_effect)
        
        # 同时应用阴影和透明度效果 (需要嵌套容器，这里简单处理)
        # 动画1：透明度
        anim_opacity = QPropertyAnimation(opacity_effect, b"opacity")
        anim_opacity.setDuration(400)
        anim_opacity.setStartValue(0)
        anim_opacity.setEndValue(1)
        anim_opacity.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # 动画2：位置
        anim_pos = QPropertyAnimation(toast, b"pos")
        anim_pos.setDuration(400)
        anim_pos.setStartValue(QPoint(x, y + 20))
        anim_pos.setEndValue(QPoint(x, y))
        anim_pos.setEasingCurve(QEasingCurve.Type.OutBack)
        
        toast.show()
        anim_opacity.start()
        anim_pos.start()
        
        # 自动消失
        def fade_out():
            anim_out = QPropertyAnimation(opacity_effect, b"opacity")
            anim_out.setDuration(500)
            anim_out.setStartValue(1)
            anim_out.setEndValue(0)
            anim_out.finished.connect(toast.deleteLater)
            anim_out.start()
            
        QTimer.singleShot(2500, fade_out)

    def _show_save_error(self, error: str, file_path: str):
        """显示保存错误并提供重试选项"""
        reply = ModernMessageBox.question(
            self, tr("保存失败"),
            f"无法保存文件: {error}\\n\\n文件路径: {file_path}\\n\\n请检查磁盘空间和写入权限。",
            yes_text=tr("重试"), no_text=tr("取消")
        )
        if reply == QDialog.DialogCode.Accepted:
            self._save_file()

    def _print(self):
        """打开打印对话框"""
        if not self.canvas:
            ModernMessageBox.warning(self, "错误", "没有可打印的图像")
            return
        from ui.print_dialog import PrintDialog
        pm = self.canvas.get_pixmap()
        dialog = PrintDialog(pm, self)
        dialog.exec()
    
    def _show_share_panel(self):
        """显示分享面板"""
        if not self.canvas:
            ModernMessageBox.warning(self, "错误", "没有可分享的图像")
            return
        
        from ui.share_panel import SharePanel
        from PySide6.QtWidgets import QDialog, QVBoxLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("分享"))
        dialog.setMinimumSize(900, 800)
        dialog.resize(900, 800)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        
        share_panel = SharePanel(dialog)
        share_panel.set_pixmap(self.canvas.get_pixmap())
        
        layout.addWidget(share_panel)
        
        dialog.exec()

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
    
    def _toggle_effects_panel(self):
        if self.effects_dock.isVisible():
            self.effects_dock.hide()
            self.effects_btn.setChecked(False)
        else:
            self._position_floating_dock(self.effects_dock)
            self.effects_dock.show()
            self.effects_btn.setChecked(True)
    
    def _toggle_adjustments_panel(self):
        if self.adjustments_dock.isVisible():
            self.adjustments_dock.hide()
            self.adjust_btn.setChecked(False)
        else:
            self._position_floating_dock(self.adjustments_dock)
            self.adjustments_dock.show()
            self.adjust_btn.setChecked(True)
    
    def _position_floating_dock(self, dock):
        """将悬浮面板定位在主窗口右侧"""
        if not dock.isFloating():
            return
            
        # 获取主窗口几何信息
        main_geo = self.geometry()
        
        # 默认宽度
        dock_width = 220
        
        # 计算位置：主窗口右侧边缘往里一点，或者直接在右侧弹出
        # 这里选择在主窗口内部右侧悬浮
        x = main_geo.right() - dock_width - 20
        y = main_geo.top() + 120
        
        # 如果有多个面板打开，可以稍微偏移避免完全重叠
        if dock == self.adjustments_dock:
            y += 40
            x -= 20
            
        dock.resize(dock_width, dock.sizeHint().height())
        dock.move(x, y)

    
    def _toggle_crop_mode(self):
        """切换裁剪模式"""
        if not self.canvas:
            return
        
        if self.canvas.crop_mode:
            # 退出裁剪模式，显示确认对话框
            self._show_crop_toolbar(False)
            self.canvas.exit_crop_mode(False)
            self.crop_btn.setChecked(False)
        else:
            # 进入裁剪模式
            self.canvas.enter_crop_mode()
            self._show_crop_toolbar(True)
            self.crop_btn.setChecked(True)
    
    def _show_crop_toolbar(self, show: bool):
        """显示/隐藏裁剪工具栏"""
        if show:
            # 创建裁剪工具栏（如果不存在）
            if not hasattr(self, 'crop_toolbar') or not self.crop_toolbar:
                self._create_crop_toolbar()
            self.crop_toolbar.show()
        else:
            if hasattr(self, 'crop_toolbar') and self.crop_toolbar:
                self.crop_toolbar.hide()
    
    def _create_crop_toolbar(self):
        """创建裁剪工具栏"""
        self.crop_toolbar = QFrame(self)
        self.crop_toolbar.setStyleSheet("""
            QFrame {
                background: #f5f5f5;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
            }
            QPushButton {
                background: white;
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #e5f3ff;
                border-color: #0078d7;
            }
            QPushButton[primary="true"] {
                background: #0078D7;
                color: white;
                border: none;
            }
            QPushButton[primary="true"]:hover {
                background: #005a9e;
            }
            QLabel {
                color: #333;
                font-size: 11px;
            }
            QSpinBox {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 2px 4px;
            }
        """)
        
        layout = QHBoxLayout(self.crop_toolbar)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)
        
        # 尺寸显示
        layout.addWidget(QLabel(tr("宽度:")))
        self.crop_width_spin = QSpinBox()
        self.crop_width_spin.setRange(1, 200000)
        self.crop_width_spin.setSuffix(" px")
        self.crop_width_spin.setFixedWidth(90)
        self.crop_width_spin.setStyleSheet(MODERN_SPINBOX_STYLE)
        self.crop_width_spin.valueChanged.connect(self._on_crop_size_changed)
        layout.addWidget(self.crop_width_spin)
        
        layout.addWidget(QLabel(tr("高度:")))
        self.crop_height_spin = QSpinBox()
        self.crop_height_spin.setRange(1, 200000)
        self.crop_height_spin.setSuffix(" px")
        self.crop_height_spin.setFixedWidth(90)
        self.crop_height_spin.setStyleSheet(MODERN_SPINBOX_STYLE)
        self.crop_height_spin.valueChanged.connect(self._on_crop_size_changed)
        layout.addWidget(self.crop_height_spin)
        
        # 分隔线
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setStyleSheet("background: #ccc;")
        layout.addWidget(sep)
        
        # 应用按钮
        apply_btn = QPushButton(tr("✓ 应用裁剪"))
        apply_btn.setProperty("primary", True)
        apply_btn.clicked.connect(self._apply_crop)
        layout.addWidget(apply_btn)
        
        # 取消按钮
        cancel_btn = QPushButton(tr("✗ 取消"))
        cancel_btn.clicked.connect(self._cancel_crop)
        layout.addWidget(cancel_btn)
        
        layout.addStretch()
        
        # 定位工具栏
        self.crop_toolbar.adjustSize()
        self.crop_toolbar.move(
            (self.width() - self.crop_toolbar.width()) // 2,
            self.height() - self.crop_toolbar.height() - 50
        )
        
        # 更新尺寸显示
        self._update_crop_size_display()
    
    def _update_crop_size_display(self):
        """更新裁剪尺寸显示"""
        if not self.canvas or not self.canvas.crop_rect:
            return
        
        rect = self.canvas.crop_rect
        if hasattr(self, 'crop_width_spin'):
            self.crop_width_spin.blockSignals(True)
            self.crop_height_spin.blockSignals(True)
            self.crop_width_spin.setValue(rect.width())
            self.crop_height_spin.setValue(rect.height())
            self.crop_width_spin.blockSignals(False)
            self.crop_height_spin.blockSignals(False)
    
    def _on_crop_size_changed(self):
        """裁剪尺寸手动修改"""
        if not self.canvas or not self.canvas.crop_rect:
            return
        
        new_width = self.crop_width_spin.value()
        new_height = self.crop_height_spin.value()
        
        # 保持左上角位置不变
        self.canvas.crop_rect.setWidth(new_width)
        self.canvas.crop_rect.setHeight(new_height)
        self.canvas._constrain_crop_rect()
        self.canvas._update_crop_display()
    
    def _apply_crop(self):
        """应用裁剪"""
        if self.canvas and self.canvas.crop_mode:
            self.canvas.exit_crop_mode(True)
            self._show_crop_toolbar(False)
            self.crop_btn.setChecked(False)
            self.is_modified = True
            self.statusBar().showMessage(tr("✓ 已应用裁剪"), 2000)
    
    def _cancel_crop(self):
        """取消裁剪"""
        if self.canvas and self.canvas.crop_mode:
            self.canvas.exit_crop_mode(False)
            self._show_crop_toolbar(False)
            self.crop_btn.setChecked(False)
            self.statusBar().showMessage(tr("已取消裁剪"), 2000)

    def _ocr_current_selection(self):
        if not hasattr(self, "canvas") or not self.canvas or not self.canvas.current_pixmap or self.canvas.current_pixmap.isNull():
            return
        
        # 提示用户进行框选
        self.statusBar().showMessage("请框选要识别的文字区域...", 0)
        self.canvas.enter_ocr_mode()

    def _on_ocr_selection_done(self, img: QImage):
        """当 OCR 选区完成后执行识别"""
        try:
            from core.ocr_engine import OCRWorker
        except Exception:
            ModernMessageBox.warning(self, "OCR 错误", "本地 OCR 引擎未就绪，请检查依赖。")
            return

        # 界面反馈
        self.statusBar().showMessage(tr("正在识别文字，请稍候..."), 0)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        
        # 创建工作线程
        self.ocr_worker = OCRWorker(img)
        
        def on_finished(text):
            QApplication.restoreOverrideCursor()
            self.statusBar().showMessage(tr("识别完成"), 2000)
            
            if not text or not text.strip():
                ModernMessageBox.information(self, tr("识别结果"), tr("未识别到文字。"))
                return

            from ui.modern_dialog import OcrTextDialog
            from PySide6.QtWidgets import QDialog
            dlg = OcrTextDialog(text, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                QApplication.clipboard().setText(dlg.result_text)
        
        def on_error(err_msg):
            QApplication.restoreOverrideCursor()
            self.statusBar().showMessage(tr("识别失败"), 2000)
            ModernMessageBox.warning(self, tr("OCR 错误"), tr("识别失败: {err_msg}").format(err_msg=err_msg))

        self.ocr_worker.finished.connect(on_finished)
        self.ocr_worker.error.connect(on_error)
        self.ocr_worker.start()
    
    def _apply_effect(self, effect: str, intensity: int):
        if not self.canvas or not self.canvas.current_pixmap or self.canvas.current_pixmap.isNull():
            return
        
        try:
            intensity = self.effects_panel.intensity_slider.value()
            if effect == "blur":
                self.canvas.apply_blur(max(1, min(20, intensity)))
            elif effect == "sharpen":
                self.canvas.apply_sharpen()
            elif effect == "pixelate":
                self.canvas.apply_pixelate(max(2, min(40, intensity * 2)))
            elif effect == "emboss":
                self.canvas.apply_emboss()
            elif effect == "noise":
                self.canvas.add_noise(max(5, min(100, intensity * 5)))
            self.is_modified = True
            self.statusBar().showMessage(f"✓ 已应用 {effect} 特效", 2000)
        except Exception as e:
            self.statusBar().showMessage(f"✗ 特效应用失败: {str(e)}", 3000)
    
    def _on_adjustment_changed(self, adj_type: str, value: int):
        if not self.canvas or not self.canvas.current_pixmap or self.canvas.current_pixmap.isNull():
            return
        
        try:
            if adj_type == "brightness":
                self.canvas.adjust_brightness(max(-100, min(100, value)))
            elif adj_type == "contrast":
                self.canvas.adjust_contrast(max(-99, min(99, value)))
            elif adj_type == "saturation":
                self.canvas.adjust_saturation(max(-100, min(100, value)))
        except Exception as e:
            # 静默处理错误，不中断用户操作
            pass
    
    def _on_width_changed(self, value: int):
        """笔宽变化"""
        if self.canvas:
            self.canvas.set_pen_width(value)
    
    def _on_font_size_changed(self, value: int):
        """字体大小变化"""
        if self.canvas:
            self.canvas.set_font_size(value)
    
    # ========== 撤销/重置方法 ==========
    
    def _undo(self):
        """撤销"""
        if self.canvas:
            if self.canvas.undo():
                # 同步 UI 面板状态
                if hasattr(self, 'adjustments_panel'):
                    self.adjustments_panel.set_adjustments(self.canvas._current_adjustments)
                self.statusBar().showMessage("↩ 已撤销", 1500)
            else:
                self.statusBar().showMessage(tr("没有可撤销的操作"), 1500)
    
    def _reset_to_original(self):
        """重置到原图 - 移除所有绘图和特效"""
        if self.canvas:
            if self.canvas.reset_to_original():
                # 重置所有面板 UI
                if hasattr(self, 'effects_panel'):
                    self.effects_panel.reset_ui()
                if hasattr(self, 'adjustments_panel'):
                    self.adjustments_panel.reset_ui()
                self.statusBar().showMessage("🔄 已重置到原图", 1500)
            else:
                self.statusBar().showMessage("重置失败", 1500)
    
    # ========== 缩放方法 ==========
    
    def _zoom_in(self):
        """放大"""
        if self.canvas:
            self.canvas.zoom_in()
    
    def _zoom_out(self):
        """缩小"""
        if self.canvas:
            self.canvas.zoom_out()
    
    def _zoom_reset(self):
        """重置缩放"""
        if self.canvas:
            self.canvas.zoom_reset()
    
    def _on_zoom_changed(self, zoom_level: float):
        """缩放级别变化回调"""
        percent = int(zoom_level * 100)
        if hasattr(self, 'zoom_label'):
            self.zoom_label.setText(f"{percent}%")
        self.statusBar().showMessage(tr("缩放: {percent}%").format(percent=percent), 1000)
    
    def _on_apply_adjustments(self):
        """应用调整"""
        if self.canvas and self.canvas.current_pixmap and not self.canvas.current_pixmap.isNull():
            try:
                self.canvas.apply_adjustments()
                self.is_modified = True
                self.statusBar().showMessage(tr("✓ 已应用调整"), 2000)
            except Exception as e:
                self.statusBar().showMessage(tr("✗ 应用调整失败: {error}").format(error=str(e)), 3000)
    
    def _on_reset_adjustments(self):
        """重置调整"""
        if self.canvas and self.canvas.original_pixmap and not self.canvas.original_pixmap.isNull():
            try:
                self.canvas.reset_adjustments()
                self.statusBar().showMessage(tr("✓ 已重置调整"), 2000)
            except Exception as e:
                self.statusBar().showMessage(tr("✗ 重置调整失败: {error}").format(error=str(e)), 3000)

    def keyPressEvent(self, event):
        # 默认快捷键
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Z:
                self._undo()
                return
            elif event.key() == Qt.Key.Key_S:
                self._save_file()
                return
            elif event.key() == Qt.Key.Key_C:
                self._copy()
                return
            elif event.key() == Qt.Key.Key_P:
                self._print()
                return
        
        if event.key() == Qt.Key.Key_Escape:
            self._on_return_to_main()
            return
        elif event.key() == Qt.Key.Key_F11:
            self._toggle_maximize()
            return
        
        super().keyPressEvent(event)

    def closeEvent(self, event):
        # 停止自动保存定时器
        self.auto_save_timer.stop()
        
        # 保存窗口大小
        if self.config.get("editor_remember_size"):
            geo = self.geometry()
            self.config.set("editor_last_size", [geo.x(), geo.y(), geo.width(), geo.height()])
        
        # 自动保存所有标签页到临时存储
        if self.tab_manager:
            for tab_id, canvas in self.canvases.items():
                tab_data = self.tab_manager.get_tab_data(tab_id)
                if tab_data:
                    pixmap = canvas.get_pixmap()
                    self.temp_storage.save_temp(pixmap, tab_id, tab_data.title)
        
        # 不弹出警告提示，直接关闭
        self.closed.emit()
        super().closeEvent(event)
    
    def add_image(self, pixmap: QPixmap, file_path: str = None, title: str = None):
        """外部调用：添加新图像到编辑器"""
        if pixmap and not pixmap.isNull():
            return self._add_image_tab(pixmap, file_path, title)
        return None
    
    def get_current_pixmap(self) -> QPixmap:
        """获取当前标签页的图像"""
        if self.canvas:
            return self.canvas.get_pixmap()
        return None
    
    def _on_return_to_main(self):
        """返回主页面 - 保存所有标签页的预览状态并显示主窗口"""
        if not self.tab_manager:
            # 发出关闭信号，让主窗口显示
            self.closed.emit()
            self.hide()
            return
        
        # 保存所有标签页到缓存
        cache_manager = get_preview_cache_manager()
        all_tabs_data = self.tab_manager.get_all_tabs_data()
        
        if not all_tabs_data:
            # 发出关闭信号，让主窗口显示
            self.closed.emit()
            self.hide()
            return
        
        # 生成会话ID，用于关联所有标签页
        session_id = f"session_{datetime.now().timestamp()}"
        saved_cache_ids = []
        
        for tab_data in all_tabs_data:
            tab_id = tab_data.tab_id
            
            if tab_id not in self.canvases:
                continue
            
            # 获取画布
            canvas = self.canvases[tab_id]
            pixmap = canvas.get_pixmap()
            
            # 获取滚动位置（仅当前标签页有效）
            scroll_pos = (0, 0)
            
            # 生成缓存ID
            cache_id = f"preview_{session_id}_{tab_id}"
            
            # 保存元数据
            metadata = {
                "title": tab_data.title,
                "file_path": tab_data.file_path,
                "tab_id": tab_id,
                "session_id": session_id,
                "is_modified": tab_data.is_modified,
                "order": len(saved_cache_ids)  # 标签页顺序
            }
            
            # 保存到缓存
            success = cache_manager.save_preview(
                cache_id, pixmap, scroll_pos, 1.0, metadata
            )
            
            if success:
                saved_cache_ids.append(cache_id)
        
        if saved_cache_ids:
            # 发送信号给主窗口，传递会话ID
            if hasattr(self, 'preview_saved'):
                self.preview_saved.emit(session_id)
        
        # 发出关闭信号，让主窗口显示
        self.closed.emit()
        # 隐藏编辑器（不关闭），以便后续截图可以重用
        self.hide()
    
    def _auto_save_temp(self):
        """自动保存临时文件"""
        if self.tab_manager and self.tab_manager.current_tab_id:
            tab_id = self.tab_manager.current_tab_id
            if tab_id in self.canvases:
                canvas = self.canvases[tab_id]
                pixmap = canvas.get_pixmap()
                
                tab_data = self.tab_manager.get_tab_data(tab_id)
                if tab_data:
                    self.temp_storage.save_temp(pixmap, tab_id, tab_data.title)
    
    def _call_main_new_image(self):
        """调用主窗口的新建图像功能"""
        from ui.new_image_dialog import NewImageDialog
        dialog = NewImageDialog(self)
        if dialog.exec():
            size = dialog.get_size()
            color = dialog.get_color()
            pixmap = QPixmap(size)
            pixmap.fill(color)
            self._add_image_tab(pixmap, None, tr("新建图像"))
