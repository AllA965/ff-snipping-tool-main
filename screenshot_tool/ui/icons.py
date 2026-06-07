import os
import sys
from PySide6.QtGui import QIcon, QColor, QPixmap, QPainter
from PySide6.QtCore import QSize

def get_app_icon_path():
    """获取应用程序图标路径"""
    if getattr(sys, 'frozen', False):
        # 打包环境
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        # 开发环境 - 此时 __file__ 在 screenshot_tool/ui/icons.py
        # 需要回退一级到 screenshot_tool
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 优先使用用户指定的最新图标
    icon_names = ['截图贴图工具图标.ico', '截图贴图工具.ico', '鲲穹01.ico', 'icon.ico']
    
    # 调试：打印搜索路径
    # print(f"Icon search base path: {base_path}")
    
    for name in icon_names:
        path = os.path.join(base_path, name)
        if os.path.exists(path):
            return path
            
    # 如果没找到，尝试在当前执行目录下找
    for name in icon_names:
        path = os.path.join(os.getcwd(), name)
        if os.path.exists(path):
            return path
            
    return None

def set_window_icon(window):
    """为窗口设置统一的应用程序图标"""
    icon_path = get_app_icon_path()
    if icon_path:
        window.setWindowIcon(QIcon(icon_path))
    else:
        # 如果找不到图标文件，创建一个默认的蓝色方块图标
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 120, 215))
        painter = QPainter(pixmap)
        painter.setPen(QColor(255, 255, 255))
        painter.drawRect(6, 6, 12, 12)
        painter.drawRect(14, 14, 12, 12)
        painter.end()
        window.setWindowIcon(QIcon(pixmap))
