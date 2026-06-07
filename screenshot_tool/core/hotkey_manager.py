"""Global/Application hotkey manager with Windows global and cross-platform fallback."""

from __future__ import annotations

import ctypes
import logging
import sys
from datetime import datetime

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut

if sys.platform == "win32":
    from ctypes import wintypes
else:
    wintypes = None


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("HotkeyManager")

IS_WINDOWS = sys.platform == "win32"

# Windows modifiers
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312

VK_CODES = {
    "A": 0x41,
    "B": 0x42,
    "C": 0x43,
    "D": 0x44,
    "E": 0x45,
    "F": 0x46,
    "G": 0x47,
    "H": 0x48,
    "I": 0x49,
    "J": 0x4A,
    "K": 0x4B,
    "L": 0x4C,
    "M": 0x4D,
    "N": 0x4E,
    "O": 0x4F,
    "P": 0x50,
    "Q": 0x51,
    "R": 0x52,
    "S": 0x53,
    "T": 0x54,
    "U": 0x55,
    "V": 0x56,
    "W": 0x57,
    "X": 0x58,
    "Y": 0x59,
    "Z": 0x5A,
    "0": 0x30,
    "1": 0x31,
    "2": 0x32,
    "3": 0x33,
    "4": 0x34,
    "5": 0x35,
    "6": 0x36,
    "7": 0x37,
    "8": 0x38,
    "9": 0x39,
    "F1": 0x70,
    "F2": 0x71,
    "F3": 0x72,
    "F4": 0x73,
    "F5": 0x74,
    "F6": 0x75,
    "F7": 0x76,
    "F8": 0x77,
    "F9": 0x78,
    "F10": 0x79,
    "F11": 0x7A,
    "F12": 0x7B,
    "PRINTSCREEN": 0x2C,
    "PRTSC": 0x2C,
    "PRINT": 0x2C,
    "INSERT": 0x2D,
    "DELETE": 0x2E,
    "HOME": 0x24,
    "END": 0x23,
    "PAGEUP": 0x21,
    "PAGEDOWN": 0x22,
    "LEFT": 0x25,
    "UP": 0x26,
    "RIGHT": 0x27,
    "DOWN": 0x28,
    "SPACE": 0x20,
    "TAB": 0x09,
    "ENTER": 0x0D,
    "RETURN": 0x0D,
    "ESCAPE": 0x1B,
    "ESC": 0x1B,
    "BACKSPACE": 0x08,
    "GRAVE": 0xC0,
    "BACKQUOTE": 0xC0,
    "~": 0xC0,
    "MINUS": 0xBD,
    "-": 0xBD,
    "EQUALS": 0xBB,
    "=": 0xBB,
    "LBRACKET": 0xDB,
    "[": 0xDB,
    "RBRACKET": 0xDD,
    "]": 0xDD,
    "BACKSLASH": 0xDC,
    "\\": 0xDC,
    "SEMICOLON": 0xBA,
    ";": 0xBA,
    "APOSTROPHE": 0xDE,
    "'": 0xDE,
    "COMMA": 0xBC,
    ",": 0xBC,
    "PERIOD": 0xBE,
    ".": 0xBE,
    "SLASH": 0xBF,
    "/": 0xBF,
}


class HotkeyThread(QThread):
    hotkey_triggered = Signal(int)
    registration_result = Signal(int, bool, str)

    def __init__(self):
        super().__init__()
        self.hotkeys: dict[int, tuple[int, int]] = {}
        self.running = True
        self._pending_register: list[tuple[int, int, int]] = []
        self._pending_unregister: list[int] = []
        self.user32 = ctypes.windll.user32 if IS_WINDOWS else None

    def set_hotkeys(self, hotkeys: dict):
        self.hotkeys = hotkeys

    def add_hotkey(self, hotkey_id: int, modifiers: int, vk: int):
        self._pending_register.append((hotkey_id, modifiers, vk))

    def remove_hotkey(self, hotkey_id: int):
        self._pending_unregister.append(hotkey_id)

    def run(self):
        if not IS_WINDOWS:
            return

        for hotkey_id, (modifiers, vk) in self.hotkeys.items():
            self._register_hotkey(hotkey_id, modifiers, vk)

        msg = wintypes.MSG()
        while self.running:
            while self._pending_register:
                hotkey_id, modifiers, vk = self._pending_register.pop(0)
                self._register_hotkey(hotkey_id, modifiers, vk)

            while self._pending_unregister:
                hotkey_id = self._pending_unregister.pop(0)
                self._unregister_hotkey(hotkey_id)

            if self.user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                if msg.message == WM_HOTKEY:
                    self.hotkey_triggered.emit(msg.wParam)
            else:
                self.msleep(50)

        for hotkey_id in list(self.hotkeys.keys()):
            self._unregister_hotkey(hotkey_id)

    def _register_hotkey(self, hotkey_id: int, modifiers: int, vk: int):
        if not IS_WINDOWS:
            self.registration_result.emit(hotkey_id, False, "Global hotkey is only available on Windows")
            return

        if vk == 0:
            self.registration_result.emit(hotkey_id, False, "Invalid hotkey")
            return

        self.user32.UnregisterHotKey(None, hotkey_id)
        result = self.user32.RegisterHotKey(None, hotkey_id, modifiers | MOD_NOREPEAT, vk)

        if result:
            self.hotkeys[hotkey_id] = (modifiers, vk)
            self.registration_result.emit(hotkey_id, True, "Registered")
        else:
            error_code = ctypes.get_last_error()
            if error_code == 1409:
                message = "Hotkey is already used by another app"
            else:
                message = f"Windows error: {error_code}"
            self.registration_result.emit(hotkey_id, False, message)

    def _unregister_hotkey(self, hotkey_id: int):
        if not IS_WINDOWS:
            return
        self.user32.UnregisterHotKey(None, hotkey_id)
        self.hotkeys.pop(hotkey_id, None)

    def stop(self):
        self.running = False
        self.wait()


class HotkeyManager(QObject):
    HOTKEY_FULLSCREEN = 1
    HOTKEY_REGION = 2
    HOTKEY_CONTROL = 3
    HOTKEY_COLOR_PICKER = 4
    HOTKEY_REPEAT = 5
    HOTKEY_WHITEBOARD = 6
    HOTKEY_SMART_PASTE = 7
    HOTKEY_SCREEN_RECORD = 8

    hotkey_registered = Signal(str, bool, str)
    hotkey_conflict = Signal(str, str)

    HOTKEY_NAMES = {
        HOTKEY_FULLSCREEN: "fullscreen",
        HOTKEY_REGION: "region",
        HOTKEY_CONTROL: "control",
        HOTKEY_COLOR_PICKER: "color_picker",
        HOTKEY_REPEAT: "repeat_capture",
        HOTKEY_WHITEBOARD: "whiteboard",
        HOTKEY_SMART_PASTE: "smart_paste",
        HOTKEY_SCREEN_RECORD: "screen_record",
    }

    HOTKEY_DISPLAY_NAMES = {
        "fullscreen": "全屏截图",
        "region": "矩形截图",
        "control": "窗口控件截图",
        "color_picker": "取色器",
        "repeat_capture": "重复截取",
        "whiteboard": "白板",
        "smart_paste": "智能粘贴",
        "screen_record": "录屏",
    }

    def __init__(self, main_window, config):
        super().__init__()
        self.main_window = main_window
        self.config = config
        self.hotkey_thread = None
        self.registered_hotkeys: dict[str, tuple[int, int]] = {}
        self._log_entries: list[str] = []
        self._shortcuts: list[QShortcut] = []

    def parse_hotkey(self, hotkey_str: str) -> tuple[int, int]:
        if not hotkey_str:
            return 0, 0

        parts = hotkey_str.upper().replace(" ", "").split("+")
        modifiers = 0
        vk = 0

        for part in parts:
            if part in ("CTRL", "CONTROL"):
                modifiers |= MOD_CONTROL
            elif part == "ALT":
                modifiers |= MOD_ALT
            elif part == "SHIFT":
                modifiers |= MOD_SHIFT
            elif part in ("WIN", "WINDOWS", "META", "CMD", "COMMAND"):
                modifiers |= MOD_WIN
            elif part in VK_CODES:
                vk = VK_CODES[part]

        return modifiers, vk

    def hotkey_to_string(self, modifiers: int, vk: int) -> str:
        parts = []
        if modifiers & MOD_CONTROL:
            parts.append("Ctrl")
        if modifiers & MOD_ALT:
            parts.append("Alt")
        if modifiers & MOD_SHIFT:
            parts.append("Shift")
        if modifiers & MOD_WIN:
            parts.append("Win")

        for name, code in VK_CODES.items():
            if code == vk:
                parts.append(name)
                break

        return "+".join(parts)

    def check_conflict(self, hotkey_str: str, exclude_name: str = None) -> str | None:
        modifiers, vk = self.parse_hotkey(hotkey_str)
        if vk == 0:
            return None

        for name, (m, v) in self.registered_hotkeys.items():
            if name != exclude_name and m == modifiers and v == vk:
                return self.HOTKEY_DISPLAY_NAMES.get(name, name)
        return None

    def _log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [{level}] {message}"
        self._log_entries.append(entry)
        logger.log(getattr(logging, level, logging.INFO), message)
        if len(self._log_entries) > 100:
            self._log_entries = self._log_entries[-100:]

    def get_log(self) -> list[str]:
        return self._log_entries.copy()

    def _qt_key_sequence(self, hotkey_str: str) -> str:
        if not hotkey_str:
            return ""

        mapping = {
            "CTRL": "Ctrl",
            "CONTROL": "Ctrl",
            "ALT": "Alt",
            "SHIFT": "Shift",
            "WIN": "Meta",
            "WINDOWS": "Meta",
            "META": "Meta",
            "CMD": "Meta",
            "COMMAND": "Meta",
            "RETURN": "Return",
            "ESC": "Esc",
            "PRINTSCREEN": "Print",
            "PRTSC": "Print",
        }

        parts = []
        for part in hotkey_str.upper().replace(" ", "").split("+"):
            parts.append(mapping.get(part, part.capitalize() if len(part) == 1 else part.title()))

        return "+".join(parts)

    def _clear_qt_shortcuts(self):
        for shortcut in self._shortcuts:
            try:
                shortcut.setEnabled(False)
                shortcut.deleteLater()
            except RuntimeError:
                pass
        self._shortcuts.clear()

    def _register_qt_hotkeys(self, hotkeys_config: dict):
        self._clear_qt_shortcuts()

        hotkey_mapping = {
            "fullscreen": self.HOTKEY_FULLSCREEN,
            "region": self.HOTKEY_REGION,
            "control": self.HOTKEY_CONTROL,
            "color_picker": self.HOTKEY_COLOR_PICKER,
            "repeat_capture": self.HOTKEY_REPEAT,
            "whiteboard": self.HOTKEY_WHITEBOARD,
            "smart_paste": self.HOTKEY_SMART_PASTE,
            "screen_record": self.HOTKEY_SCREEN_RECORD,
        }

        self.registered_hotkeys.clear()

        for name, hotkey_id in hotkey_mapping.items():
            hotkey_str = hotkeys_config.get(name)
            if not hotkey_str:
                continue

            modifiers, vk = self.parse_hotkey(hotkey_str)
            if vk == 0:
                self.hotkey_registered.emit(name, False, "Invalid hotkey format")
                continue

            qt_sequence = self._qt_key_sequence(hotkey_str)
            shortcut = QShortcut(QKeySequence(qt_sequence), self.main_window)
            shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            shortcut.activated.connect(lambda hid=hotkey_id: self.on_hotkey_triggered(hid))
            self._shortcuts.append(shortcut)

            self.registered_hotkeys[name] = (modifiers, vk)
            self.hotkey_registered.emit(name, True, "Registered in-app shortcut")

        self._log("Non-Windows hotkeys registered as application shortcuts")

    def register_hotkeys(self):
        hotkeys_config = self.config.get("hotkeys", {})

        if not IS_WINDOWS:
            self._register_qt_hotkeys(hotkeys_config)
            return

        hotkeys = {}
        hotkey_mapping = {
            "fullscreen": self.HOTKEY_FULLSCREEN,
            "region": self.HOTKEY_REGION,
            "control": self.HOTKEY_CONTROL,
            "color_picker": self.HOTKEY_COLOR_PICKER,
            "repeat_capture": self.HOTKEY_REPEAT,
            "whiteboard": self.HOTKEY_WHITEBOARD,
            "smart_paste": self.HOTKEY_SMART_PASTE,
            "screen_record": self.HOTKEY_SCREEN_RECORD,
        }

        self.registered_hotkeys.clear()

        for name, hotkey_id in hotkey_mapping.items():
            hotkey_str = hotkeys_config.get(name)
            if not hotkey_str:
                continue
            modifiers, vk = self.parse_hotkey(hotkey_str)
            if vk != 0:
                hotkeys[hotkey_id] = (modifiers, vk)
                self.registered_hotkeys[name] = (modifiers, vk)

        if self.hotkey_thread:
            self.hotkey_thread.stop()

        self.hotkey_thread = HotkeyThread()
        self.hotkey_thread.set_hotkeys(hotkeys)
        self.hotkey_thread.hotkey_triggered.connect(self.on_hotkey_triggered)
        self.hotkey_thread.registration_result.connect(self._on_registration_result)
        self.hotkey_thread.start()

        self._log("Windows global hotkey listener started")

    def _on_registration_result(self, hotkey_id: int, success: bool, message: str):
        name = self.HOTKEY_NAMES.get(hotkey_id, str(hotkey_id))
        display_name = self.HOTKEY_DISPLAY_NAMES.get(name, name)

        if success:
            self._log(f"Hotkey [{display_name}] registered")
        else:
            self._log(f"Hotkey [{display_name}] registration failed: {message}", "ERROR")

        self.hotkey_registered.emit(name, success, message)

    def update_hotkey(self, name: str, hotkey_str: str) -> tuple[bool, str]:
        conflict = self.check_conflict(hotkey_str, name)
        if conflict:
            msg = f"快捷键与 [{conflict}] 冲突"
            self._log(msg, "WARNING")
            self.hotkey_conflict.emit(name, conflict)
            return False, msg

        if not hotkey_str:
            self._remove_hotkey(name)
            return True, "已禁用"

        modifiers, vk = self.parse_hotkey(hotkey_str)
        if vk == 0:
            return False, "无效的快捷键格式"

        hotkey_id = None
        for hid, hname in self.HOTKEY_NAMES.items():
            if hname == name:
                hotkey_id = hid
                break

        if hotkey_id is None:
            return False, "未知的快捷键名称"

        if not IS_WINDOWS:
            self.register_hotkeys()
            self._log(f"Application shortcut [{name}] updated to {hotkey_str}")
            return True, "更新成功"

        if self.hotkey_thread and self.hotkey_thread.isRunning():
            self.hotkey_thread.remove_hotkey(hotkey_id)
            self.hotkey_thread.add_hotkey(hotkey_id, modifiers, vk)
            self.registered_hotkeys[name] = (modifiers, vk)
            self._log(f"Hotkey [{name}] updated to {hotkey_str}")
            return True, "更新成功"

        return False, "快捷键服务未运行"

    def _remove_hotkey(self, name: str):
        hotkey_id = None
        for hid, hname in self.HOTKEY_NAMES.items():
            if hname == name:
                hotkey_id = hid
                break

        if not IS_WINDOWS:
            self.register_hotkeys()
            self.registered_hotkeys.pop(name, None)
            self._log(f"Application shortcut [{name}] removed")
            return

        if hotkey_id and self.hotkey_thread:
            self.hotkey_thread.remove_hotkey(hotkey_id)
            self.registered_hotkeys.pop(name, None)
            self._log(f"Hotkey [{name}] removed")

    def on_hotkey_triggered(self, hotkey_id: int):
        name = self.HOTKEY_NAMES.get(hotkey_id, "unknown")
        self._log(f"Hotkey triggered: {name}")

        if hotkey_id == self.HOTKEY_FULLSCREEN:
            self.main_window.capture_fullscreen()
        elif hotkey_id == self.HOTKEY_REGION:
            self.main_window.capture_region()
        elif hotkey_id == self.HOTKEY_CONTROL:
            self.main_window.capture_control()
        elif hotkey_id == self.HOTKEY_COLOR_PICKER:
            self.main_window.open_color_picker()
        elif hotkey_id == self.HOTKEY_REPEAT:
            self.main_window.repeat_capture()
        elif hotkey_id == self.HOTKEY_WHITEBOARD:
            self.main_window.open_whiteboard()
        elif hotkey_id == self.HOTKEY_SMART_PASTE:
            self.main_window.smart_paste()
        elif hotkey_id == self.HOTKEY_SCREEN_RECORD:
            self.main_window.open_screen_recorder()

    def unregister_hotkeys(self):
        self._clear_qt_shortcuts()

        if self.hotkey_thread:
            self._log("Unregistering all global hotkeys...")
            self.hotkey_thread.stop()
            self.hotkey_thread = None

        self.registered_hotkeys.clear()

    def reload_hotkeys(self):
        self._log("Reloading hotkey config...")
        self.unregister_hotkeys()
        self.register_hotkeys()
