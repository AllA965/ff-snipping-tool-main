"""
主窗口模块 - 增强版
支持：重复截取、快捷键F8、配置联动、预览缓存
"""
import os
import sys
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QFileDialog,
    QCheckBox, QMenu
)
from PySide6.QtCore import Qt, Signal, QPoint, QRect, QTimer, QThread, QSize
from PySide6.QtGui import QPixmap, QPainter, QColor, QAction, QShortcut, QKeySequence, QFont, QBrush, QPen, QPainterPath, QFontMetrics, QIcon

from ui.region_capture import RegionCaptureWindow
from ui.editor_window import EditorWindow
from ui.styles import MAIN_WINDOW_STYLE, SIDEBAR_STYLE, CONTENT_STYLE
from core.screenshot import ScreenCapture
from core.preview_cache import get_preview_cache_manager
from ui.modern_dialog import ModernMessageBox
from core.kunqiong_login import KunqiongLoginManager
from ui.icons import set_window_icon
from core.i18n import tr


class IconButton(QPushButton):
    """带图标的按钮 - 现代风格"""

    def __init__(self, icon_color: str, text: str, subtitle: str = "", icon: str = "", parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.icon_color = icon_color
        self.text_str = text
        self.subtitle = subtitle
        self.icon_char = icon  # Unicode 图标字符
        self.setFixedHeight(36 if not subtitle else 44)
        self.setFixedWidth(200) # 限制宽度，防止悬停背景过大
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                text-align: left;
                padding: 6px 10px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f0f7ff, stop:1 #e5f3ff);
                border: 1px solid #cce8ff;
            }
            QPushButton:pressed {
                background: #cce8ff;
            }
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制圆角图标背景
        icon_size = 24
        icon_x = 8
        icon_y = (self.height() - icon_size) // 2
        
        # 渐变背景
        from PySide6.QtGui import QLinearGradient
        gradient = QLinearGradient(icon_x, icon_y, icon_x, icon_y + icon_size)
        base_color = QColor(self.icon_color)
        gradient.setColorAt(0, base_color.lighter(110))
        gradient.setColorAt(1, base_color)
        
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(icon_x, icon_y, icon_size, icon_size, 6, 6)
        
        # 绘制图标字符（如果有）
        if self.icon_char:
            painter.setPen(QColor(255, 255, 255))
            font = painter.font()
            font.setPointSize(11)
            painter.setFont(font)
            painter.drawText(icon_x, icon_y, icon_size, icon_size, 
                           Qt.AlignmentFlag.AlignCenter, self.icon_char)

        # 绘制文字
        painter.setPen(QColor(51, 51, 51))
        font = painter.font()
        font.setPointSize(10)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)

        text_x = 40
        if self.subtitle:
            painter.drawText(text_x, 16, tr(self.text_str))
            font.setPointSize(8)
            font.setWeight(QFont.Weight.Normal)
            painter.setFont(font)
            painter.setPen(QColor(128, 128, 128))
            painter.drawText(text_x, 30, tr(self.subtitle) if isinstance(self.subtitle, str) and self.subtitle else "")
        else:
            painter.drawText(text_x, (self.height() + 6) // 2, tr(self.text_str))


class WindowMenuButton(QPushButton):
    """窗口选择按钮 - 简约风格"""

    window_selected = Signal(int)

    def __init__(self, icon_color: str, text: str, screen_capture, icon: str = "", parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.icon_color = icon_color
        self.text_str = text
        self.screen_capture = screen_capture
        self.icon_char = icon
        self.setFixedHeight(36)
        self.setFixedWidth(200) # 限制宽度
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                text-align: left;
                padding: 6px 10px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f0f7ff, stop:1 #e5f3ff);
                border: 1px solid #cce8ff;
            }
            QPushButton:pressed {
                background: #cce8ff;
            }
        """)
        self.clicked.connect(self._show_window_menu)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制圆角图标背景
        icon_size = 24
        icon_x = 8
        icon_y = (self.height() - icon_size) // 2
        
        # 渐变背景
        from PySide6.QtGui import QLinearGradient, QPen
        gradient = QLinearGradient(icon_x, icon_y, icon_x, icon_y + icon_size)
        base_color = QColor(self.icon_color)
        gradient.setColorAt(0, base_color.lighter(110))
        gradient.setColorAt(1, base_color)
        
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(icon_x, icon_y, icon_size, icon_size, 6, 6)
        
        # 绘制窗口图标（自定义绘制）
        painter.setPen(QPen(QColor(255, 255, 255), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # 窗口外框
        win_x = icon_x + 4
        win_y = icon_y + 5
        win_w = 16
        win_h = 14
        painter.drawRoundedRect(win_x, win_y, win_w, win_h, 2, 2)
        
        # 标题栏
        painter.drawLine(win_x, win_y + 4, win_x + win_w, win_y + 4)
        
        # 标题栏按钮（三个小圆点）
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(Qt.PenStyle.NoPen)
        for i in range(3):
            painter.drawEllipse(win_x + win_w - 4 - i * 3, win_y + 2, 2, 2)

        # 绘制文字
        painter.setPen(QColor(51, 51, 51))
        font = painter.font()
        font.setPointSize(10)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.drawText(40, (self.height() + 6) // 2, tr(self.text_str))

    def _show_window_menu(self):
        windows = self.screen_capture.get_all_windows()
        if not windows:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: white;
                border: 1px solid #ddd;
                padding: 5px 0;
            }
            QMenu::item {
                padding: 8px 20px;
                color: #333;
            }
            QMenu::item:selected {
                background: #e8f4fc;
            }
        """)

        for win in windows:
            title = win['title'][:50] + "..." if len(win['title']) > 50 else win['title']
            action = QAction(title, menu)
            action.setData(win['hwnd'])
            action.triggered.connect(lambda checked, h=win['hwnd']: self.window_selected.emit(h))
            menu.addAction(action)

        pos = self.mapToGlobal(QPoint(0, self.height()))
        menu.exec(pos)


import requests
import io

class AvatarLoader(QThread):
    """头像异步加载器"""
    finished = Signal(QPixmap)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            response = requests.get(self.url, timeout=10)
            if response.status_code == 200:
                pixmap = QPixmap()
                if pixmap.loadFromData(response.content):
                    self.finished.emit(pixmap)
        except Exception as e:
            print(tr("加载头像失败: {error}").format(error=e))

class SidebarButton(QPushButton):
    """侧边栏按钮 - 现代风格"""

    def __init__(self, text: str, parent=None):
        self._raw_text = text
        super().__init__(text, parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.avatar_pixmap = None
        self._update_style(False)
        self._apply_elide()

    def setText(self, text: str):
        self._raw_text = text
        self._apply_elide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_elide()

    def _apply_elide(self):
        max_width = max(0, self.width() - 22)
        elided = QFontMetrics(self.font()).elidedText(self._raw_text, Qt.TextElideMode.ElideRight, max_width)
        super().setText(elided)

    def set_avatar(self, pixmap: QPixmap):
        """设置头像"""
        self.avatar_pixmap = pixmap
        self.update()

    def paintEvent(self, event):
        # 如果有头像且不是返回预览等特殊按钮，绘制头像
        if self.avatar_pixmap and "登录" not in self.text() and not self.text().startswith("↩️"):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # 绘制圆形头像
            size = 24
            x = 10
            y = (self.height() - size) // 2
            
            # 创建圆形路径
            path = QPainterPath()
            path.addEllipse(x, y, size, size)
            painter.setClipPath(path)
            
            # 绘制图片
            painter.drawPixmap(x, y, size, size, self.avatar_pixmap)
            painter.setClipping(False)
            
            # 绘制文字
            painter.setPen(QColor(255, 255, 255) if self.isChecked() else QColor(200, 200, 200))
            font = self.font()
            font.setPointSize(10)
            painter.setFont(font)
            
            # 这里的文字处理需要跳过图标字符
            text = tr(self._raw_text)
            if " " in text:
                text = text.split(" ", 1)[1]
            text = QFontMetrics(font).elidedText(text, Qt.TextElideMode.ElideRight, max(0, self.width() - 46))
            painter.drawText(40, 0, self.width() - 40, self.height(), Qt.AlignmentFlag.AlignVCenter, text)
        else:
            super().paintEvent(event)

    def _update_style(self, selected: bool):
        if selected:
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(255,255,255,0.2), stop:1 rgba(255,255,255,0.1));
                    border: none;
                    border-left: 3px solid #4FC3F7;
                    color: white;
                    text-align: left;
                    padding-left: 14px;
                    font-size: 12px;
                    font-weight: 500;
                    border-radius: 0 4px 4px 0;
                    margin-right: 4px;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    border-left: 3px solid transparent;
                    color: rgba(255,255,255,0.8);
                    text-align: left;
                    padding-left: 14px;
                    font-size: 12px;
                    border-radius: 0 4px 4px 0;
                    margin-right: 4px;
                }
                QPushButton:hover {
                    background: rgba(255,255,255,0.1);
                    color: white;
                    border-left: 3px solid rgba(79, 195, 247, 0.5);
                }
            """)

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._update_style(checked)


class MainWindow(QMainWindow):
    """主窗口 - 增强版"""

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.is_windows = sys.platform == "win32"
        self.screen_capture = ScreenCapture()
        self.editor_window = None
        self.sidebar_buttons = []
        
        # 登录管理
        self.login_manager = KunqiongLoginManager()
        self.login_manager.login_success.connect(self._on_login_success)
        self.login_manager.login_failed.connect(self._on_login_failed)
        
        # 最后一次截图参数
        self.last_capture_mode = None
        self.last_capture_rect = None
        
        # 预览缓存相关
        self.preview_cache_manager = get_preview_cache_manager()
        self.current_preview_cache_id = None
        self.return_preview_btn = None

        self.setup_ui()
        self.setup_shortcuts()
        self.setStyleSheet(MAIN_WINDOW_STYLE)
        
        # 后台预初始化 OCR 引擎，减少首次识别延迟
        QTimer.singleShot(1000, self._init_ocr_background)

    def _init_ocr_background(self):
        """后台初始化 OCR 引擎"""
        try:
            from core.ocr_engine import OCREngine
            # 在单独线程初始化，避免主线程卡顿
            class InitThread(QThread):
                def run(self):
                    try:
                        OCREngine.instance()
                    except:
                        pass
            self._ocr_init_thread = InitThread()
            self._ocr_init_thread.start()
        except:
            pass

    def setup_ui(self):
        self.setWindowTitle(tr("截图贴图工具"))
        self.setMinimumSize(700, 520)
        self.resize(800, 560)
        
        # 设置窗口图标
        self._set_window_icon()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)

        content = self._create_content()
        main_layout.addWidget(content, 1)
    
    def setup_shortcuts(self):
        """设置快捷键"""
        # F8 重复截取
        self.repeat_shortcut = QShortcut(QKeySequence("F8"), self)
        self.repeat_shortcut.activated.connect(self.repeat_capture)
    
    def _set_window_icon(self):
        """设置窗口图标"""
        set_window_icon(self)

    def _create_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setFixedWidth(110) # 稍微加宽一点以适应 Logo
        sidebar.setStyleSheet(SIDEBAR_STYLE)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(2)
        
        # ========== 添加侧边栏 Logo (一比一复刻图片展示) ==========
        logo_container = QWidget()
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(10, 0, 10, 10)
        logo_layout.setSpacing(8)
        
        logo_icon = QLabel()
        from ui.icons import get_app_icon_path
        icon_path = get_app_icon_path()
        if icon_path:
            logo_pixmap = QPixmap(icon_path).scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_icon.setPixmap(logo_pixmap)
        else:
            # 备用：绘制简单的蓝块图标
            logo_icon.setFixedSize(20, 20)
            logo_icon.setStyleSheet("background-color: white; border-radius: 4px;")
            
        logo_text = QLabel(tr("截图贴图工具"))
        logo_text.setStyleSheet("color: white; font-weight: bold; font-size: 11px;")
        
        logo_layout.addWidget(logo_icon)
        logo_layout.addWidget(logo_text)
        logo_layout.addStretch()
        
        layout.addWidget(logo_container)
        # =======================================================
        
        # 返回预览按钮（顶部）
        self.return_preview_btn = SidebarButton("↩️ " + tr("返回预览"))
        self.return_preview_btn.setToolTip(tr("返回上次的预览状态"))
        self.return_preview_btn.clicked.connect(self._on_return_preview)
        self.return_preview_btn.setEnabled(False)  # 初始禁用
        layout.addWidget(self.return_preview_btn)
        
        # 分隔线
        sep1 = QFrame()
        sep1.setFixedHeight(1)
        sep1.setStyleSheet("background: rgba(255,255,255,0.2);")
        layout.addWidget(sep1)

        menu_defs = [
            ("🏠", "主页", self.show_home),
            ("📄", "新建", self.new_image),
            ("📂", "打开", self.open_file),
            ("💾", "保存", self._save_current),
            ("📋", "另存为", self._save_as),
            ("🖨️", "打印", self._print),
            ("📤", "分享", self.show_share),
            ("⚙️", "选项", self.open_settings),
        ]

        for i, (icon, label, callback) in enumerate(menu_defs):
            btn = SidebarButton(f"{icon} {tr(label)}")
            btn.clicked.connect(lambda checked, idx=i: self._on_sidebar_click(idx))
            btn.clicked.connect(callback)
            layout.addWidget(btn)
            self.sidebar_buttons.append(btn)

        if self.sidebar_buttons:
            self.sidebar_buttons[0].setChecked(True)

        layout.addStretch()

        # 分隔线
        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background: rgba(255,255,255,0.2);")
        layout.addWidget(separator)

        # 登录/用户按钮
        self.login_btn = SidebarButton("👤 " + tr("登录"))
        self.login_btn.clicked.connect(self._handle_login_click)
        layout.addWidget(self.login_btn)
        self._update_login_ui()

        exit_btn = SidebarButton("🚪 " + tr("退出"))
        exit_btn.clicked.connect(self.quit_app)
        layout.addWidget(exit_btn)
        layout.addSpacing(8)

        return sidebar

    def _on_sidebar_click(self, index: int):
        for i, btn in enumerate(self.sidebar_buttons):
            btn.setChecked(i == index)

    def _create_content(self) -> QFrame:
        content = QFrame()
        content.setStyleSheet(CONTENT_STYLE)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 16, 24, 12)
        layout.setSpacing(8)

        # 顶部标题栏布局
        header_layout = QHBoxLayout()
        
        title = QLabel(tr("选择操作"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2B579A;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        left_panel = self._create_left_panel()
        content_layout.addWidget(left_panel, 1)

        right_panel = self._create_right_panel()
        content_layout.addWidget(right_panel, 1)

        layout.addLayout(content_layout, 1)

        # 底部状态栏
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 5, 0, 5)
        
        # 我要软件定制链接
        self.customize_btn = QPushButton(tr("我要软件定制"))
        
        # 获取图标路径（自适应打包环境）
        from ui.icons import get_app_icon_path
        icon_path = get_app_icon_path()
        if icon_path:
            self.customize_btn.setIcon(QIcon(icon_path))
        else:
            # 备选
            import os
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            specific_icon = os.path.join(base_path, "鲲穹01.ico")
            if os.path.exists(specific_icon):
                self.customize_btn.setIcon(QIcon(specific_icon))
        
        self.customize_btn.setIconSize(QSize(14, 14))
        self.customize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.customize_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #E67E22;
                font-size: 11px;
                font-weight: 500;
                padding: 2px 5px;
            }
            QPushButton:hover {
                color: #D35400;
                text-decoration: underline;
            }
        """)
        self.customize_btn.clicked.connect(self._open_customize_link)
        bottom_layout.addWidget(self.customize_btn)
        
        bottom_layout.addSpacing(10)
        
        self.status_label = QLabel(tr("就绪 | 按 F8 重复上次截图"))
        self.status_label.setStyleSheet("color: #999; font-size: 10px;")
        bottom_layout.addWidget(self.status_label)
        
        # 登录取消按钮（初始隐藏）
        self.cancel_login_btn = QPushButton(tr("取消登录"))
        self.cancel_login_btn.setStyleSheet("""
            QPushButton {
                background: #f44336;
                color: white;
                border: none;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 10px;
            }
            QPushButton:hover { background: #d32f2f; }
        """)
        self.cancel_login_btn.hide()
        self.cancel_login_btn.clicked.connect(self._cancel_login)
        bottom_layout.addWidget(self.cancel_login_btn)
        
        bottom_layout.addStretch()
        
        checkbox = QCheckBox(tr("启动时不显示此窗口"))
        checkbox.setStyleSheet("color: #888; font-size: 10px;")
        bottom_layout.addWidget(checkbox)
        
        # 鲲穹AI品牌标识
        self.brand_label = QLabel(tr("鲲穹AI旗下产品"))
        self.brand_label.setStyleSheet("color: #bbb; font-size: 9px; margin-left: 10px;")
        bottom_layout.addWidget(self.brand_label)
        
        layout.addLayout(bottom_layout)

        return content

    def _create_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        task_title = QLabel("📁 " + tr("新任务"))
        task_title.setStyleSheet("""
            font-size: 13px; 
            font-weight: bold; 
            color: #2B579A; 
            margin-bottom: 6px;
            padding: 4px 0;
        """)
        layout.addWidget(task_title)

        new_btn = IconButton("#0078D7", tr("新建"), tr("新建图像"), "📄")
        new_btn.clicked.connect(self.new_image)
        layout.addWidget(new_btn)

        open_btn = IconButton("#4CAF50", tr("打开"), tr("打开已有文件"), "📂")
        open_btn.clicked.connect(self.open_file)
        layout.addWidget(open_btn)

        layout.addSpacing(12)

        capture_title = QLabel("📷 " + tr("截取屏幕"))
        capture_title.setStyleSheet("""
            font-size: 13px; 
            font-weight: bold; 
            color: #2B579A; 
            margin-bottom: 6px;
            padding: 4px 0;
        """)
        layout.addWidget(capture_title)

        fullscreen_btn = IconButton("#2196F3", tr("全屏"), "", "🖥")
        fullscreen_btn.clicked.connect(self.capture_fullscreen)
        layout.addWidget(fullscreen_btn)

        self.window_btn = WindowMenuButton("#2196F3", tr("??"), self.screen_capture)
        self.window_btn.window_selected.connect(self._on_window_selected)
        if not self.is_windows:
            self.window_btn.setEnabled(False)
            self.window_btn.setToolTip(tr("???????????"))
        layout.addWidget(self.window_btn)

        other_modes = [
            ("#FF9800", tr("????"), self.capture_region, "??"),
            ("#3F51B5", tr("????"), self.capture_scroll_window, "??"),
            ("#009688", tr("????"), self.capture_freeform, "?"),
        ]
        if self.is_windows:
            other_modes.insert(1, ("#9C27B0", tr("????"), self.capture_control, "??"))

        for color, text, callback, icon in other_modes:
            btn = IconButton(color, text, "", icon)
            btn.clicked.connect(callback)
            layout.addWidget(btn)
        
        # 重复截取按钮
        layout.addSpacing(12)
        repeat_btn = IconButton("#78909C", tr("重复截取"), tr("F8 重复上次操作"), "🔄")
        repeat_btn.clicked.connect(self.repeat_capture)
        layout.addWidget(repeat_btn)

        layout.addStretch()
        return panel

    def _create_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        tools_title = QLabel("🛠 " + tr("实用工具"))
        tools_title.setStyleSheet("""
            font-size: 13px; 
            font-weight: bold; 
            color: #2B579A; 
            margin-bottom: 6px;
            padding: 4px 0;
        """)
        layout.addWidget(tools_title)

        tools = [
            ("#F44336", tr("屏幕录制器"), tr("录制桌面视频"), self.open_screen_recorder, "🎬"),
            ("#9C27B0", tr("取色器"), tr("在屏幕上拾取颜色"), self.open_color_picker, "🎨"),
            ("#E91E63", tr("调色板"), tr("在调色板上按需调色"), self.open_palette, "🖌"),
            ("#2196F3", tr("放大镜"), tr("对屏幕像素放大细看"), self.open_magnifier, "🔍"),
            ("#FF9800", tr("标尺"), tr("测量桌面对象的尺寸"), self.open_ruler, "📏"),
            ("#4CAF50", tr("坐标轴"), tr("查测相对坐标"), self.open_crosshair, "⊕"),
            ("#00BCD4", tr("量角器"), tr("在屏幕上测量角度"), self.open_protractor, "📐"),
            ("#795548", tr("白板"), tr("用于演示或绘画"), self.open_whiteboard, "📝"),
        ]

        for color, text, subtitle, callback, icon in tools:
            btn = IconButton(color, text, subtitle, icon)
            btn.clicked.connect(callback)
            layout.addWidget(btn)

        layout.addStretch()
        return panel

    # ========== 截图功能 ==========

    def capture_fullscreen(self):
        self.last_capture_mode = "fullscreen"
        self.hide()
        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, self._do_fullscreen_capture)

    def _do_fullscreen_capture(self):
        pixmap = self.screen_capture.capture_all_screens()
        if not pixmap.isNull():
            self.config.save_last_capture("fullscreen")
            self.open_editor(pixmap)

    def capture_region(self):
        self.last_capture_mode = "region"
        self.hide()
        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, self._do_region_capture)

    def _do_region_capture(self):
        # 使用蓝色选框，直接进入编辑器
        self.region_window = RegionCaptureWindow(self.screen_capture, color_mode="blue")
        self.region_window.capture_completed.connect(self._on_region_captured)
        self.region_window.capture_cancelled.connect(self._on_capture_cancelled)
        self.region_window.showFullScreen()

    def _on_region_captured(self, pixmap):
        if not pixmap.isNull():
            # 保存截图参数
            if hasattr(self, 'region_window') and self.region_window:
                rect = self.region_window.selection_rect
                if rect and not rect.isNull():
                    self.last_capture_rect = (rect.x(), rect.y(), rect.width(), rect.height())
                    self.config.save_last_capture(self.last_capture_mode, self.last_capture_rect)
            self.open_editor(pixmap)

    def _on_capture_cancelled(self):
        self.show()

    # ========== 登录相关功能 ==========

    def _update_login_ui(self):
        """根据登录状态更新 UI"""
        is_logged_in = self.login_manager.is_logged_in()
        if is_logged_in:
            user_info = self.login_manager.get_user_info()
            nickname = user_info.get("nickname", tr("已登录"))
            self.login_btn.setText(f"👤 {nickname}")
            self.login_btn.setToolTip(tr("点击查看用户信息或退出登录"))
            
            # 如果有头像且尚未加载，则加载头像
            avatar_url = user_info.get("avatar")
            if avatar_url and not self.login_btn.avatar_pixmap:
                self._load_avatar(avatar_url)
        else:
            self.login_btn.setText(tr("👤 登录"))
            self.login_btn.setToolTip(tr("点击登录鲲穹AI账号"))
            self.login_btn.set_avatar(None)

    def _load_avatar(self, url):
        """异步加载用户头像"""
        if hasattr(self, "avatar_loader") and self.avatar_loader.isRunning():
            return
        self.avatar_loader = AvatarLoader(url)
        self.avatar_loader.finished.connect(self.login_btn.set_avatar)
        self.avatar_loader.start()

    def _open_customize_link(self):
        """打开软件定制链接"""
        import webbrowser
        # 尝试从接口动态获取定制链接
        custom_url = self.login_manager.get_custom_url()
        if custom_url:
            webbrowser.open(custom_url)
        else:
            # 如果接口调用失败，则回退到默认官网
            webbrowser.open("https://www.kunqiongai.com/")

    def _handle_login_click(self):
        """处理登录按钮点击"""
        if self.login_manager.is_logged_in():
            self._show_user_panel()
        else:
            # 获取图标路径
            from ui.icons import get_app_icon_path
            icon_path = get_app_icon_path()
            if not icon_path:
                import os
                app_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                icon_path = os.path.join(app_path, "鲲穹01.ico")
            
            if ModernMessageBox.question(
                self, tr("登录确认"), 
                "即将打开浏览器进行登录，是否继续？\n\n登录完成后请返回本程序。",
                icon_type=icon_path
            ):
                self.status_label.setText(tr("正在等待网页登录完成..."))
                self.cancel_login_btn.show()
                self.login_manager.start_login()

    def _cancel_login(self):
        """取消登录流程"""
        self.login_manager.stop_polling()
        self.cancel_login_btn.hide()
        self.status_label.setText(tr("登录已取消"))

    def _show_user_panel(self):
        """显示用户信息面板 - 增强版"""
        user_info = self.login_manager.get_user_info()
        menu = QMenu(self)
        menu.setFixedWidth(180)
        menu.setStyleSheet("""
            QMenu {
                background: white;
                border: 1px solid #eee;
                border-radius: 8px;
            }
            QMenu::item {
                padding: 10px 20px;
                border-radius: 4px;
                margin: 2px 5px;
            }
            QMenu::item:selected {
                background: #f0f7ff;
                color: #0078D7;
            }
            QMenu::separator {
                height: 1px;
                background: #eee;
                margin: 5px 10px;
            }
        """)

        # 创建顶部用户信息区域
        from PySide6.QtWidgets import QWidgetAction
        header_action = QWidgetAction(menu)
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(15, 15, 15, 10)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 头像展示
        avatar_label = QLabel()
        avatar_label.setFixedSize(64, 64)
        if self.login_btn.avatar_pixmap:
            # 绘制圆形大头像
            size = 64
            target = QPixmap(size, size)
            target.fill(Qt.GlobalColor.transparent)
            painter = QPainter(target)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            path = QPainterPath()
            path.addEllipse(0, 0, size, size)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, size, size, self.login_btn.avatar_pixmap)
            painter.end()
            avatar_label.setPixmap(target)
        else:
            avatar_label.setStyleSheet("background: #eee; border-radius: 32px;")
            avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar_label.setText("👤")
            font = avatar_label.font()
            font.setPointSize(24)
            avatar_label.setFont(font)
            
        header_layout.addWidget(avatar_label, 0, Qt.AlignmentFlag.AlignCenter)
        
        name_label = QLabel(user_info.get('nickname', '未知'))
        name_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 8px;")
        header_layout.addWidget(name_label, 0, Qt.AlignmentFlag.AlignCenter)
        
        header_action.setDefaultWidget(header_widget)
        menu.addAction(header_action)
        
        menu.addSeparator()

        logout_action = QAction(tr("🚪 退出登录"), menu)
        logout_action.triggered.connect(self._handle_logout)
        menu.addAction(logout_action)

        # 在按钮上方弹出
        pos = self.login_btn.mapToGlobal(QPoint(0, -menu.sizeHint().height() - 5))
        menu.exec(pos)

    def _handle_logout(self):
        """处理退出登录"""
        self.login_manager.logout()
        self._update_login_ui()
        self.status_label.setText(tr("已退出登录"))
        ModernMessageBox.success(self, tr("提示"), tr("已成功退出登录"))

    def _on_login_success(self, user_info):
        """登录成功回调"""
        self.cancel_login_btn.hide()
        self._update_login_ui()

        # 加载头像已在 _update_login_ui 中处理，这里只需处理提示
        self.status_label.setText(tr("登录成功"))
        ModernMessageBox.success(self, "登录成功", "欢迎回来！账号已同步。")

    def _on_login_failed(self, error_msg):
        """登录失败回调"""
        self.cancel_login_btn.hide()
        self.status_label.setText(tr("登录失败"))
        ModernMessageBox.warning(self, "登录失败", f"登录过程中出现错误：\n{error_msg}")

    def _on_window_selected(self, hwnd: int):
        self.last_capture_mode = "window"
        self.last_window_hwnd = hwnd
        self.hide()
        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, lambda: self._do_window_capture(hwnd))

    def capture_window(self):
        if not self.is_windows:
            ModernMessageBox.information(self, tr("??"), tr("?????????????????????"))
            self.capture_region()
            return

        hwnd = self.screen_capture.get_window_at_cursor()
        if hwnd:
            self.last_capture_mode = "window"
            self.last_window_hwnd = hwnd
            self.hide()
            from PySide6.QtCore import QTimer
            QTimer.singleShot(200, lambda: self._do_window_capture(hwnd))

    def _do_window_capture(self, hwnd):
        if self.is_windows:
            import ctypes
            user32 = ctypes.windll.user32
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)

        from PySide6.QtCore import QTimer
        QTimer.singleShot(300, lambda: self._capture_window_final(hwnd))

    def _capture_window_final(self, hwnd):
        pixmap = self.screen_capture.capture_window(hwnd)
        if not pixmap.isNull():
            self.config.save_last_capture("window")
            self.open_editor(pixmap)
        else:
            self.show()

    def capture_control(self):
        if not self.is_windows:
            ModernMessageBox.information(self, tr("??"), tr("?????????????????????"))
            self.capture_region()
            return

        self.last_capture_mode = "control"
        self.hide()
        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, self._do_control_capture)

    def _do_control_capture(self):
        from ui.control_capture import ControlCaptureWindow
        self.control_window = ControlCaptureWindow(self.screen_capture)
        self.control_window.capture_completed.connect(self._on_region_captured)
        self.control_window.capture_cancelled.connect(self._on_capture_cancelled)
        self.control_window.showFullScreen()

    def capture_scroll_window(self):
        self.last_capture_mode = "scroll"
        self.hide()
        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, self._do_scroll_capture)
    
    def _do_scroll_capture(self):
        from ui.scroll_capture import ScrollCaptureWindow
        self.scroll_window = ScrollCaptureWindow(self.screen_capture)
        self.scroll_window.capture_completed.connect(self._on_region_captured)
        self.scroll_window.capture_cancelled.connect(self._on_capture_cancelled)
        self.scroll_window.show()

    def capture_freeform(self):
        self.last_capture_mode = "freeform"
        self.hide()
        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, self._do_freeform_capture)

    def _do_freeform_capture(self):
        from ui.freeform_capture import FreeformCaptureWindow
        self.freeform_window = FreeformCaptureWindow(self.screen_capture)
        self.freeform_window.capture_completed.connect(self._on_region_captured)
        self.freeform_window.capture_cancelled.connect(self._on_capture_cancelled)
        self.freeform_window.showFullScreen()
    
    def repeat_capture(self):
        """重复上次截图操作"""
        last = self.config.get_last_capture()
        
        if not last and not self.last_capture_mode:
            self.status_label.setText("没有可重复的截图操作")
            return
        
        mode = last.get("mode") if last else self.last_capture_mode
        
        if mode == "fullscreen":
            self.capture_fullscreen()
        elif mode == "region":
            self.capture_region()
        elif mode == "window":
            if hasattr(self, 'last_window_hwnd'):
                self._on_window_selected(self.last_window_hwnd)
            else:
                self.capture_window()
        elif mode == "control":
            self.capture_control()
        elif mode == "scroll":
            self.capture_scroll_window()
        elif mode == "freeform":
            self.capture_freeform()
        else:
            self.status_label.setText(tr("未知的截图模式"))

    def open_editor(self, pixmap, file_path=None):
        # 如果编辑器已经存在（可见或隐藏），添加新标签页而不是创建新窗口
        if self.editor_window:
            self.editor_window.add_image(pixmap, file_path)
            # 如果编辑器被隐藏，显示它
            if not self.editor_window.isVisible():
                self.editor_window.show()
        else:
            # 创建新的编辑器窗口
            self.editor_window = EditorWindow(pixmap, self.config, file_path)
            self.editor_window.closed.connect(self._on_editor_closed)
            self.editor_window.preview_saved.connect(self._on_preview_saved)
            self.editor_window.show()
    
    def _on_editor_closed(self):
        """编辑器窗口关闭时的处理"""
        self.show()
    
    def _on_preview_saved(self, cache_id: str):
        """预览已保存到缓存"""
        self.current_preview_cache_id = cache_id
        self.return_preview_btn.setEnabled(True)
        self.return_preview_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.15);
                border: none;
                border-left: 3px solid #0078D7;
                color: white;
                text-align: left;
                padding-left: 12px;
                font-size: 11px;
            }
        """)
    
    def _on_return_preview(self):
        """返回预览 - 从缓存恢复所有标签页"""
        if not self.current_preview_cache_id:
            ModernMessageBox.information(self, tr("提示"), tr("没有可恢复的预览状态"))
            return
        
        # 获取会话ID（即 current_preview_cache_id）
        session_id = self.current_preview_cache_id
        
        # 查找所有属于该会话的缓存项
        cache_manager = self.preview_cache_manager
        session_caches = []
        
        for cache_id, cache_item in cache_manager.cache.items():
            if cache_item.metadata.get("session_id") == session_id:
                session_caches.append((cache_id, cache_item))
        
        if not session_caches:
            ModernMessageBox.warning(self, tr("错误"), tr("预览缓存已过期或不存在"))
            self.return_preview_btn.setEnabled(False)
            return
        
        # 按顺序排序
        session_caches.sort(key=lambda x: x[1].metadata.get("order", 0))
        
        # 显示加载状态
        self.statusBar().showMessage(tr("正在恢复 {count} 个标签页...").format(count=len(session_caches)))
        
        # 使用定时器延迟打开编辑器，实现平滑过渡
        def restore_preview():
            # 打开第一个图像
            first_cache_id, first_cache_item = session_caches[0]
            pixmap = first_cache_item.pixmap
            
            if pixmap and not pixmap.isNull():
                self.open_editor(pixmap)
                
                # 添加其他标签页
                if self.editor_window:
                    def add_remaining_tabs():
                        for cache_id, cache_item in session_caches[1:]:
                            pixmap = cache_item.pixmap
                            title = cache_item.metadata.get("title", tr("未命名"))
                            file_path = cache_item.metadata.get("file_path")
                            
                            if pixmap and not pixmap.isNull():
                                self.editor_window.add_image(pixmap, file_path, title)
                        
                        # 恢复滚动位置（仅第一个标签页）
                        scroll_pos = first_cache_item.scroll_position
                        self._restore_scroll_position(scroll_pos)
                        
                        self.statusBar().showMessage(
                            tr("✓ 已恢复 {count} 个标签页").format(count=len(session_caches)), 3000
                        )
                    
                    QTimer.singleShot(500, add_remaining_tabs)
            else:
                ModernMessageBox.warning(self, tr("错误"), tr("无法加载预览图像"))
        
        QTimer.singleShot(300, restore_preview)
    
    def _restore_scroll_position(self, scroll_pos: tuple):
        """恢复滚动位置"""
        if not self.editor_window or not hasattr(self.editor_window, 'scroll_area'):
            return
        
        scroll_area = self.editor_window.scroll_area
        if scroll_area:
            scroll_area.horizontalScrollBar().setValue(scroll_pos[0])
            scroll_area.verticalScrollBar().setValue(scroll_pos[1])

    # ========== 文件操作 ==========

    def new_image(self):
        from ui.new_image_dialog import NewImageDialog
        dialog = NewImageDialog(self)
        if dialog.exec():
            size = dialog.get_size()
            color = dialog.get_color()
            pixmap = QPixmap(size)
            pixmap.fill(color)
            self.open_editor(pixmap)

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr("打开图像"), "",
            tr("图像文件 (*.png *.jpg *.jpeg *.bmp *.gif);;所有文件 (*.*)")
        )
        if file_path:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                self.open_editor(pixmap, file_path)

    def _save_current(self):
        if self.editor_window and self.editor_window.isVisible():
            self.editor_window._save_file()
        else:
            ModernMessageBox.information(
                self, tr("提示"), 
                "请先打开或截取一张图像，然后在编辑器中进行保存。"
            )

    def _save_as(self):
        if self.editor_window and self.editor_window.isVisible():
            self.editor_window._save_as()
        else:
            ModernMessageBox.information(
                self, tr("提示"), 
                "请先打开或截取一张图像，然后在编辑器中进行另存为。"
            )

    def _print(self):
        if self.editor_window and self.editor_window.isVisible():
            self.editor_window._print()
        else:
            ModernMessageBox.information(
                self, tr("提示"), 
                "请先打开或截取一张图像，然后在编辑器中进行打印。"
            )

    # ========== 工具 ==========

    def open_color_picker(self):
        """直接启动取色器，取色后显示调色板"""
        from tools.palette import start_color_picker
        self.color_picker_overlay = start_color_picker(config=self.config)

    def open_screen_recorder(self):
        """打开或切换录屏器状态"""
        # 如果录屏器窗口已存在且可见，则切换录制状态
        if hasattr(self, 'recorder') and self.recorder and self.recorder.isVisible():
            if self.recorder.recording:
                self.recorder.stop_recording()
            else:
                self.recorder.start_recording()
            return
            
        from tools.screen_recorder import ScreenRecorderWindow
        self.recorder = ScreenRecorderWindow(self.config)
        self.recorder.show()

    def open_palette(self):
        """打开调色板面板"""
        from tools.palette import PaletteWindow
        self.palette = PaletteWindow(self.config)
        self.palette.show()

    def open_magnifier(self):
        from tools.magnifier import MagnifierWindow
        self.magnifier = MagnifierWindow()
        self.magnifier.show()

    def open_ruler(self):
        from tools.ruler import RulerWindow
        self.ruler = RulerWindow()
        self.ruler.show()

    def open_crosshair(self):
        from tools.crosshair import CrosshairWindow
        self.crosshair = CrosshairWindow(self.config)
        self.crosshair.show()

    def open_protractor(self):
        from tools.protractor import ProtractorWindow
        self.protractor = ProtractorWindow(self.config)
        self.protractor.show()

    def open_whiteboard(self):
        self.hide()
        from tools.whiteboard import FullscreenWhiteboard
        self.whiteboard = FullscreenWhiteboard(self.config)
        self.whiteboard.closed.connect(self.show)
        self.whiteboard.showFullScreen()

    def show_home(self):
        pass
    
    def smart_paste(self):
        """智能粘贴 - Ctrl+Shift+V"""
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QClipboard
        
        clipboard = QApplication.clipboard()
        
        # 检查剪贴板是否有图像
        if clipboard.mimeData().hasImage():
            image = clipboard.image()
            if not image.isNull():
                pixmap = QPixmap.fromImage(image)
                self.open_editor(pixmap)
                return
        
        # 检查剪贴板是否有文件路径
        if clipboard.mimeData().hasUrls():
            urls = clipboard.mimeData().urls()
            for url in urls:
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                        pixmap = QPixmap(file_path)
                        if not pixmap.isNull():
                            self.open_editor(pixmap, file_path)
                            return
        
        # 没有可粘贴的图像
        ModernMessageBox.information(self, tr("提示"), "剪贴板中没有可粘贴的图像")
    
    def show_share(self):
        """显示分享面板 - 优化逻辑：先恢复预览再分享"""
        from ui.share_panel import SharePanel
        from PySide6.QtWidgets import QDialog, QVBoxLayout
        
        current_pixmap = None
        
        # 1. 如果编辑器已打开且可见，直接使用当前图像
        if self.editor_window and self.editor_window.isVisible():
            current_pixmap = self.editor_window.get_current_pixmap()
            self._show_share_dialog(current_pixmap)
            return
        
        # 2. 如果编辑器存在但隐藏，显示编辑器并打开分享
        if self.editor_window and not self.editor_window.isVisible():
            self.editor_window.show()
            current_pixmap = self.editor_window.get_current_pixmap()
            if current_pixmap:
                # 延迟显示分享对话框，等待编辑器完全显示
                QTimer.singleShot(300, lambda: self._show_share_in_editor())
                return
        
        # 3. 尝试从预览缓存恢复
        if self.current_preview_cache_id:
            # 恢复预览并打开分享
            self._restore_preview_and_share()
            return
        
        # 4. 没有可分享的图像，提示用户
        ModernMessageBox.information(
            self, tr("提示"), 
            "没有可分享的图像。\n请先截取或打开一张图像。"
        )
    
    def _show_share_dialog(self, pixmap: QPixmap):
        """显示分享对话框"""
        from ui.share_panel import SharePanel
        from PySide6.QtWidgets import QDialog, QVBoxLayout
        
        if not pixmap or pixmap.isNull():
            ModernMessageBox.information(self, tr("提示"), "没有可分享的图像")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("分享"))
        dialog.setMinimumSize(800, 750)
        dialog.resize(800, 750)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        
        share_panel = SharePanel(dialog)
        share_panel.set_pixmap(pixmap)
        
        layout.addWidget(share_panel)
        dialog.exec()
    
    def _show_share_in_editor(self):
        """在编辑器中显示分享面板"""
        if self.editor_window and self.editor_window.isVisible():
            self.editor_window._show_share_panel()
    
    def _restore_preview_and_share(self):
        """恢复预览并打开分享"""
        if not self.current_preview_cache_id:
            return
        
        session_id = self.current_preview_cache_id
        cache_manager = self.preview_cache_manager
        session_caches = []
        
        for cache_id, cache_item in cache_manager.cache.items():
            if cache_item.metadata.get("session_id") == session_id:
                session_caches.append((cache_id, cache_item))
        
        if not session_caches:
            ModernMessageBox.information(self, tr("提示"), "预览缓存已过期，请重新截图")
            return
        
        # 按顺序排序
        session_caches.sort(key=lambda x: x[1].metadata.get("order", 0))
        
        # 恢复第一个图像
        first_cache_id, first_cache_item = session_caches[0]
        pixmap = first_cache_item.pixmap
        
        if pixmap and not pixmap.isNull():
            self.open_editor(pixmap)
            
            # 添加其他标签页并打开分享
            if self.editor_window:
                def restore_and_share():
                    for cache_id, cache_item in session_caches[1:]:
                        p = cache_item.pixmap
                        title = cache_item.metadata.get("title", tr("未命名"))
                        file_path = cache_item.metadata.get("file_path")
                        if p and not p.isNull():
                            self.editor_window.add_image(p, file_path, title)
                    
                    # 打开分享面板
                    QTimer.singleShot(200, self._show_share_in_editor)
                
                QTimer.singleShot(500, restore_and_share)

    def open_settings(self):
        from ui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.config, self)
        dialog.exec()

    def quit_app(self):
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
