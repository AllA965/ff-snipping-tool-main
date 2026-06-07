"""
样式定义模块 - 参考 PicPick 现代设计
"""

# 主色调 - PicPick 风格
PRIMARY_COLOR = "#2B579A"  # 深蓝色
PRIMARY_HOVER = "#1E3F6F"
ACCENT_COLOR = "#0078D7"   # 亮蓝色
BG_COLOR = "#F5F5F5"
CARD_BG = "#FFFFFF"
TEXT_COLOR = "#333333"
TEXT_SECONDARY = "#666666"
BORDER_COLOR = "#E0E0E0"

# PicPick 风格颜色
RIBBON_BG = "#F0F0F0"
RIBBON_BORDER = "#D0D0D0"
TOOL_HOVER = "#E5F3FF"
TOOL_ACTIVE = "#CCE8FF"
TOOL_BORDER_ACTIVE = "#0078D7"

MAIN_WINDOW_STYLE = """
QMainWindow {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #f8f9fa, stop:1 #e9ecef);
}
QLabel {
    color: #333;
}
"""

SIDEBAR_STYLE = """
QFrame {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #3366CC, stop:0.5 #2B579A, stop:1 #1E3F6F);
    border-right: 1px solid #1a3a6e;
}
"""

CONTENT_STYLE = """
QFrame {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ffffff, stop:1 #f8f9fa);
    border-radius: 8px;
    margin: 4px;
}
"""

# PicPick 风格编辑器样式 - 现代美化版
EDITOR_STYLE_LIGHT = """
QMainWindow {
    background: #fdfdfd;
}
QToolBar {
    background: #ffffff;
    border: none;
    border-bottom: 1px solid #eaeaea;
    padding: 6px;
    spacing: 4px;
}
QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 6px 10px;
    color: #444;
    font-size: 13px;
    font-weight: 500;
    outline: none;
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
QStatusBar {
    background: #ffffff;
    border-top: 1px solid #eaeaea;
    color: #777;
    padding: 2px;
}
QDockWidget {
    color: #444;
    font-size: 13px;
    border: none;
}
QDockWidget::title {
    background: #f8f9fa;
    padding: 8px;
    border-bottom: 1px solid #eaeaea;
    font-weight: bold;
}
"""

# 深色主题（保留）
EDITOR_STYLE = """
QMainWindow {
    background: #2d2d2d;
}
QToolBar {
    background: #3c3c3c;
    border: none;
    padding: 5px;
    spacing: 5px;
}
QToolButton {
    background: transparent;
    border: none;
    border-radius: 4px;
    padding: 8px;
    color: white;
    outline: none;
}
QToolButton:hover {
    background: #505050;
}
QToolButton:checked {
    background: #0078D7;
}
QStatusBar {
    background: #3c3c3c;
    color: white;
}
"""

# 现代 SpinBox 样式
MODERN_SPINBOX_STYLE = """
    QSpinBox {
        border: 1px solid #dcdcdc;
        border-radius: 4px;
        padding: 2px 4px;
        background: #ffffff;
        color: #333333;
        font-size: 13px;
    }
    QSpinBox:hover { border-color: #0078d7; }
    QSpinBox:focus { border-color: #0078d7; background: #ffffff; }
    QSpinBox::up-button {
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 18px;
        border-left: 1px solid #dcdcdc;
        background: #f5f5f5;
        border-top-right-radius: 4px;
    }
    QSpinBox::up-button:hover { background: #e5f3ff; }
    QSpinBox::up-arrow {
        image: none;
        width: 0;
        height: 0;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-bottom: 5px solid #666;
    }
    QSpinBox::down-button {
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 18px;
        border-left: 1px solid #dcdcdc;
        background: #f5f5f5;
        border-bottom-right-radius: 4px;
    }
    QSpinBox::down-button:hover { background: #e5f3ff; }
    QSpinBox::down-arrow {
        image: none;
        width: 0;
        height: 0;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid #666;
    }
"""

# Ribbon 工具栏分组样式 - 美化版
RIBBON_GROUP_STYLE = """
QFrame#ribbon_group {
    background: #ffffff;
    border: 1px solid #e5e5e5;
    border-radius: 6px;
    margin: 2px;
    padding: 2px;
}
QFrame#ribbon_group:hover {
    border-color: #0078d7;
    background: #fafafa;
}
QLabel#group_title {
    color: #888;
    font-size: 10px;
    font-weight: 600;
    padding: 1px 4px;
    background: #f8f8f8;
    border-radius: 3px;
    margin-top: 1px;
}
"""

# 现代按钮样式 - 带阴影和圆角
MODERN_BUTTON_STYLE = """
QPushButton {
    background-color: #0078d7;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #005a9e;
}
QPushButton:pressed {
    background-color: #004578;
}
QPushButton[secondary="true"] {
    background-color: #f3f3f3;
    color: #333;
    border: 1px solid #dcdcdc;
}
QPushButton[secondary="true"]:hover {
    background-color: #eaeaea;
}
"""

# 颜色选择器网格样式
COLOR_GRID_STYLE = """
QToolButton.color_cell {
    border: 1px solid #ccc;
    border-radius: 2px;
    min-width: 18px;
    min-height: 18px;
    max-width: 18px;
    max-height: 18px;
    margin: 1px;
}
QToolButton.color_cell:hover {
    border: 2px solid #0078d7;
}
QToolButton.color_cell:checked {
    border: 2px solid #005a9e;
}
"""

# 标签页样式 - PicPick 风格现代美化版
TAB_STYLE_PICPICK = """
QTabBar::tab {
    background: #f1f1f1;
    border: 1px solid #e0e0e0;
    border-bottom: none;
    padding: 8px 20px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    color: #666;
    font-size: 13px;
    font-weight: 500;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #0078d7;
    border-bottom: 2px solid #0078d7;
    font-weight: bold;
}
QTabBar::tab:hover:!selected {
    background: #e9eff7;
    color: #0078d7;
}
QTabWidget::pane {
    border: 1px solid #e0e0e0;
    background: #ffffff;
    border-radius: 4px;
}
"""

TOOLBAR_BUTTON_STYLE = """
QPushButton {
    background: #404040;
    border: none;
    border-radius: 4px;
    padding: 8px 12px;
    color: white;
    min-width: 60px;
}
QPushButton:hover {
    background: #505050;
}
QPushButton:pressed {
    background: #0078D7;
}
QPushButton:checked {
    background: #0078D7;
}
"""

DIALOG_STYLE = """
QDialog {
    background: #f5f5f5;
}
QLabel {
    color: #333;
    font-size: 12px;
}
QLineEdit, QSpinBox, QComboBox {
    border: 1px solid #ccc;
    border-radius: 3px;
    padding: 6px 10px;
    background: white;
    color: #333;
    min-height: 18px;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #0078D7;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #666;
}
QPushButton {
    background: #0078D7;
    color: white;
    border: none;
    border-radius: 3px;
    padding: 8px 20px;
    min-width: 80px;
    font-size: 12px;
}
QPushButton:hover {
    background: #005A9E;
}
QPushButton:pressed {
    background: #004578;
}
QPushButton[secondary="true"] {
    background: #e0e0e0;
    color: #333;
}
QPushButton[secondary="true"]:hover {
    background: #d0d0d0;
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
QCheckBox {
    spacing: 8px;
    color: #333;
}
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
"""

COLOR_PICKER_STYLE = """
QWidget {
    background: #f0f0f0;
}
QLabel {
    color: #333;
}
"""

# 新建图像对话框样式
NEW_IMAGE_DIALOG_STYLE = """
QDialog { 
    background: #f5f5f5; 
}
QLabel { 
    color: #333; 
    font-size: 12px; 
}
QLabel[title="true"] {
    font-size: 20px;
    font-weight: bold;
    color: #333;
}
QLabel[section="true"] {
    font-size: 13px;
    font-weight: 500;
    color: #333;
    margin-top: 8px;
}
QSpinBox {
    border: 1px solid #ccc;
    border-radius: 3px;
    padding: 5px 8px;
    background: white;
    color: #333;
    min-width: 80px;
}
QSpinBox:focus {
    border: 1px solid #0078D7;
}
QComboBox {
    border: 1px solid #ccc;
    border-radius: 3px;
    padding: 5px 10px;
    background: white;
    color: #333;
    min-width: 120px;
}
QComboBox:focus {
    border: 1px solid #0078D7;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #666;
    margin-right: 5px;
}
QPushButton {
    background: #0078D7;
    color: white;
    border: none;
    border-radius: 3px;
    padding: 8px 24px;
    font-size: 12px;
}
QPushButton:hover { 
    background: #005A9E; 
}
QPushButton:pressed {
    background: #004578;
}
QPushButton[secondary="true"] {
    background: #e0e0e0;
    color: #333;
}
QPushButton[secondary="true"]:hover { 
    background: #d0d0d0; 
}
"""

# 调色板样式
PALETTE_STYLE = """
QWidget { 
    background: #f5f5f5; 
}
QLabel { 
    color: #333; 
    font-size: 11px; 
}
QLabel[title="true"] {
    font-weight: bold;
    font-size: 12px;
    color: #2B579A;
}
QSpinBox, QLineEdit { 
    background: white; 
    border: 1px solid #ccc; 
    border-radius: 3px; 
    padding: 4px 6px; 
}
QSpinBox:focus, QLineEdit:focus {
    border-color: #0078D7;
}
QComboBox { 
    background: white; 
    border: 1px solid #ccc; 
    border-radius: 3px; 
    padding: 4px 8px; 
}
QPushButton { 
    background: #0078D7; 
    color: white; 
    border: none; 
    border-radius: 3px; 
    padding: 6px 12px; 
    font-size: 11px; 
    outline: none;
}
QPushButton:hover { 
    background: #005A9E; 
}
QPushButton[secondary="true"] { 
    background: #e0e0e0; 
    color: #333; 
}
QPushButton[secondary="true"]:hover { 
    background: #d0d0d0; 
}
"""

# 设置对话框样式
SETTINGS_DIALOG_STYLE = """
QDialog { 
    background: #f5f5f5; 
}
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
QCheckBox { 
    spacing: 8px; 
    color: #333; 
}
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
}
QPushButton:hover { 
    background: #005A9E; 
}
QPushButton[secondary="true"] {
    background: #e0e0e0;
    color: #333;
}
QPushButton[secondary="true"]:hover { 
    background: #d0d0d0; 
}
QLabel { 
    color: #333; 
}
QListWidget {
    border: 1px solid #ddd;
    border-radius: 4px;
    background: white;
}
"""
