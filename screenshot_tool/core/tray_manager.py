"""
系统托盘管理模块
"""
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import QSize


class TrayManager:
    """系统托盘管理器"""
    
    def __init__(self, main_window, config):
        self.main_window = main_window
        self.config = config
        
        # 创建托盘图标
        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.setIcon(self._create_icon())
        self.tray_icon.setToolTip("截图贴图工具")
        
        # 创建托盘菜单
        self.menu = self._create_menu()
        self.tray_icon.setContextMenu(self.menu)
        
        # 连接信号
        self.tray_icon.activated.connect(self._on_activated)
    
    def _create_icon(self) -> QIcon:
        """创建托盘图标"""
        import os
        import sys
        
        # 获取应用程序路径（支持打包后和开发环境）
        if getattr(sys, 'frozen', False):
            # 打包后：优先从 _MEIPASS（内部资源），其次从 exe 目录
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
            exe_path = os.path.dirname(sys.executable)
            search_paths = [base_path, exe_path]
        else:
            # 开发环境
            app_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            search_paths = [app_path]
        
        # 尝试加载图标文件（优先使用 截图贴图工具图标.ico）
        icon_names = ['截图贴图工具图标.ico', '截图贴图工具.ico', '鲲穹01.ico', 'icon.ico', 'icon.png']
        for search_path in search_paths:
            for icon_name in icon_names:
                icon_path = os.path.join(search_path, icon_name)
                if os.path.exists(icon_path):
                    return QIcon(icon_path)
        
        # 如果没有图标文件，使用默认图标
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 120, 215))
        
        painter = QPainter(pixmap)
        painter.setPen(QColor(255, 255, 255))
        painter.drawRect(6, 6, 12, 12)
        painter.drawRect(14, 14, 12, 12)
        painter.end()
        
        return QIcon(pixmap)
    
    def _create_menu(self) -> QMenu:
        """创建托盘菜单"""
        menu = QMenu()
        
        # 截图选项
        menu.addAction("全屏截图", self.main_window.capture_fullscreen)
        menu.addAction("区域截图", self.main_window.capture_region)
        menu.addAction("窗口截图", self.main_window.capture_window)
        menu.addSeparator()
        
        # 工具选项
        menu.addAction("取色器", self.main_window.open_color_picker)
        menu.addAction("屏幕录制", self.main_window.open_screen_recorder)
        menu.addSeparator()
        
        # 其他选项
        menu.addAction("显示主窗口", self._show_main_window)
        menu.addAction("设置", self.main_window.open_settings)
        menu.addSeparator()
        menu.addAction("退出", self._quit)
        
        return menu
    
    def _on_activated(self, reason):
        """托盘图标激活处理"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_main_window()
    
    def _show_main_window(self):
        """显示主窗口"""
        self.main_window.show()
        self.main_window.activateWindow()
    
    def _quit(self):
        """退出应用"""
        from PySide6.QtWidgets import QApplication
        QApplication.quit()
    
    def show(self):
        """显示托盘图标"""
        self.tray_icon.show()
    
    def hide(self):
        """隐藏托盘图标"""
        self.tray_icon.hide()
    
    def show_message(self, title: str, message: str):
        """显示托盘通知"""
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)
