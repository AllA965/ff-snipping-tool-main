import os
import sys

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from core.i18n import init_i18n
from core.single_instance import SingleInstanceLock
from ui.modern_dialog import ModernMessageBox

_app_lock = SingleInstanceLock("KunQiong_Screenshot_Tool")


def is_already_running() -> bool:
    return not _app_lock.acquire()


def exception_hook(exctype, value, traceback):
    import traceback as tb

    error_msg = "".join(tb.format_exception(exctype, value, traceback))
    print(error_msg)

    if QApplication.instance():
        ModernMessageBox.error(None, "错误", f"程序发生错误:\n{value}")

    sys.__excepthook__(exctype, value, traceback)


def _default_font() -> QFont:
    if sys.platform == "darwin":
        return QFont("PingFang SC", 12)
    if sys.platform == "win32":
        return QFont("Microsoft YaHei", 9)
    return QFont("Noto Sans", 10)


def main():
    if is_already_running():
        temp_app = QApplication(sys.argv)
        ModernMessageBox.warning(None, "提示", "程序已在运行中，请勿重复启动。")
        sys.exit(0)

    sys.excepthook = exception_hook

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    app.setApplicationName("截图贴图工具")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("鲲穹AI")

    app.setFont(_default_font())
    app.setStyleSheet("QWidget { outline: none; }")

    from ui.icons import get_app_icon_path

    icon_path = get_app_icon_path()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))

    try:
        from core.config import Config
        from core.hotkey_manager import HotkeyManager
        from core.tray_manager import TrayManager
        from core.update_manager import UpdateManager
        from ui.main_window import MainWindow

        config = Config()

        try:
            lang_code = config.get("language", "auto")
            init_i18n(lang_code, app)
        except Exception:
            init_i18n("auto", app)

        main_window = MainWindow(config)

        update_manager = UpdateManager(main_window)
        QTimer.singleShot(3000, lambda: update_manager.check_for_updates())
        main_window.update_manager = update_manager

        tray_manager = TrayManager(main_window, config)
        tray_manager.show()

        hotkey_manager = HotkeyManager(main_window, config)
        main_window.hotkey_manager = hotkey_manager
        hotkey_manager.register_hotkeys()

        main_window.show()

        exit_code = app.exec()
        _app_lock.release()
        sys.exit(exit_code)

    except Exception as e:
        try:
            import traceback as _tb

            with open("startup_traceback.txt", "w", encoding="utf-8") as file:
                file.write(_tb.format_exc())
        except Exception:
            pass

        ModernMessageBox.error(None, "启动错误", f"程序启动失败:\n{e}")
        _app_lock.release()
        sys.exit(1)


if __name__ == "__main__":
    main()
