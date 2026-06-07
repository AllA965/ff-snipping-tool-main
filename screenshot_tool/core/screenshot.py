"""Screen capture implementation with Windows API and cross-platform Qt fallback."""

from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    from ctypes import wintypes

    SRCCOPY = 0x00CC0020
    DIB_RGB_COLORS = 0
    BI_RGB = 0

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]


    class BITMAPINFO(ctypes.Structure):
        _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


class ScreenCapture:
    """Capture screen content."""

    def __init__(self):
        self.user32 = None
        self.gdi32 = None

        if IS_WINDOWS:
            self.user32 = ctypes.windll.user32
            self.gdi32 = ctypes.windll.gdi32
            try:
                self.user32.SetProcessDPIAware()
            except Exception:
                pass

    def _virtual_geometry(self) -> QRect:
        screens = QApplication.screens()
        total_rect = QRect()
        for screen in screens:
            total_rect = total_rect.united(screen.geometry())
        return total_rect

    def capture_full_screen(self) -> QPixmap:
        screen = QApplication.primaryScreen()
        if screen:
            return screen.grabWindow(0)
        return QPixmap()

    def capture_all_screens(self) -> QPixmap:
        screens = QApplication.screens()
        if not screens:
            return QPixmap()

        total_rect = self._virtual_geometry()

        if IS_WINDOWS:
            return self._capture_region_win32(
                total_rect.x(),
                total_rect.y(),
                total_rect.width(),
                total_rect.height(),
            )

        # Cross-platform composition from each screen
        result = QPixmap(total_rect.size())
        result.fill(Qt.GlobalColor.transparent)

        painter = QPainter(result)
        for screen in screens:
            geometry = screen.geometry()
            pixmap = screen.grabWindow(0)
            offset = geometry.topLeft() - total_rect.topLeft()
            painter.drawPixmap(offset, pixmap)
        painter.end()

        return result

    def capture_region(self, x: int, y: int, width: int, height: int) -> QPixmap:
        if width <= 0 or height <= 0:
            return QPixmap()

        if IS_WINDOWS:
            return self._capture_region_win32(x, y, width, height)

        virtual_rect = self._virtual_geometry()
        whole = self.capture_all_screens()
        if whole.isNull():
            return QPixmap()

        return whole.copy(
            x - virtual_rect.x(),
            y - virtual_rect.y(),
            width,
            height,
        )

    def _capture_region_win32(self, x: int, y: int, width: int, height: int) -> QPixmap:
        hdesktop = self.user32.GetDesktopWindow()
        desktop_dc = self.user32.GetWindowDC(hdesktop)

        mem_dc = self.gdi32.CreateCompatibleDC(desktop_dc)

        bitmap = self.gdi32.CreateCompatibleBitmap(desktop_dc, width, height)
        old_bitmap = self.gdi32.SelectObject(mem_dc, bitmap)

        self.gdi32.BitBlt(mem_dc, 0, 0, width, height, desktop_dc, x, y, SRCCOPY)

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = width
        bmi.bmiHeader.biHeight = -height
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB

        buffer_size = width * height * 4
        buffer = ctypes.create_string_buffer(buffer_size)

        self.gdi32.GetDIBits(
            mem_dc,
            bitmap,
            0,
            height,
            buffer,
            ctypes.byref(bmi),
            DIB_RGB_COLORS,
        )

        self.gdi32.SelectObject(mem_dc, old_bitmap)
        self.gdi32.DeleteObject(bitmap)
        self.gdi32.DeleteDC(mem_dc)
        self.user32.ReleaseDC(hdesktop, desktop_dc)

        image = QImage(buffer, width, height, width * 4, QImage.Format_ARGB32)
        image = image.copy()

        return QPixmap.fromImage(image)

    def capture_window(self, hwnd: int) -> QPixmap:
        if not IS_WINDOWS:
            return QPixmap()

        rect = wintypes.RECT()
        self.user32.GetWindowRect(hwnd, ctypes.byref(rect))

        x = rect.left
        y = rect.top
        width = rect.right - rect.left
        height = rect.bottom - rect.top

        return self._capture_region_win32(x, y, width, height)

    def get_window_at_cursor(self):
        if not IS_WINDOWS:
            return None

        point = wintypes.POINT()
        self.user32.GetCursorPos(ctypes.byref(point))
        return self.user32.WindowFromPoint(point)

    def get_all_windows(self) -> list:
        if not IS_WINDOWS:
            return []

        windows = []

        GWL_EXSTYLE = -20
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_APPWINDOW = 0x00040000

        def enum_callback(hwnd, _lparam):
            if not self.user32.IsWindow(hwnd):
                return True
            if not self.user32.IsWindowVisible(hwnd):
                return True

            ex_style = self.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if (ex_style & WS_EX_TOOLWINDOW) and not (ex_style & WS_EX_APPWINDOW):
                return True

            length = self.user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True

            buffer = ctypes.create_unicode_buffer(length + 1)
            self.user32.GetWindowTextW(hwnd, buffer, length + 1)
            title = buffer.value

            if not title or title in ["Program Manager", "Windows Input Experience"]:
                return True

            rect = wintypes.RECT()
            self.user32.GetWindowRect(hwnd, ctypes.byref(rect))

            width = rect.right - rect.left
            height = rect.bottom - rect.top
            if width < 50 or height < 50:
                return True

            if rect.right < 0 or rect.bottom < 0:
                return True

            windows.append(
                {
                    "hwnd": hwnd,
                    "title": title,
                    "rect": (rect.left, rect.top, width, height),
                }
            )
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        self.user32.EnumWindows(WNDENUMPROC(enum_callback), 0)

        return windows
