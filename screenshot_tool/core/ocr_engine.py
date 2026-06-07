from typing import Optional, Callable

import numpy as np
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import QThread, Signal, QObject

try:
    from rapidocr_onnxruntime import RapidOCR
except Exception:
    RapidOCR = None


class OCRWorker(QThread):
    """异步 OCR 工作线程"""
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, image: QImage, parent=None):
        super().__init__(parent)
        self.image = image

    def run(self):
        try:
            text = OCREngine.instance().recognize_qimage(self.image)
            self.finished.emit(text)
        except Exception as e:
            self.error.emit(str(e))


class OCREngine:
    _instance: Optional["OCREngine"] = None

    def __init__(self) -> None:
        if RapidOCR is None:
            raise RuntimeError("rapidocr_onnxruntime 未安装，无法使用本地 OCR 功能")
        
        # 尝试启用硬件加速
        import onnxruntime as ort
        providers = ort.get_available_providers()
        
        # 优先级：DirectML (Windows 优选) > CUDA (NVIDIA) > CPU
        preferred_providers = []
        if 'DmlExecutionProvider' in providers:
            preferred_providers.append('DmlExecutionProvider')
        if 'CUDAExecutionProvider' in providers:
            preferred_providers.append('CUDAExecutionProvider')
        preferred_providers.append('CPUExecutionProvider')
        
        # 初始化引擎，传入指定的 providers
        self._ocr = RapidOCR(det_use_cuda='CUDAExecutionProvider' in preferred_providers, 
                             cls_use_cuda='CUDAExecutionProvider' in preferred_providers,
                             rec_use_cuda='CUDAExecutionProvider' in preferred_providers)
        
        # 如果是 DirectML，需要通过 session_options 进一步优化，但 RapidOCR 封装层级较深
        # 这里简单处理：RapidOCR 默认会尝试使用可用硬件。
        # 我们主要通过多线程来解决 UI 卡顿感。

    @classmethod
    def instance(cls) -> "OCREngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def recognize_qimage(self, image: QImage) -> str:
        if image is None or image.isNull():
            return ""

        img = image.convertToFormat(QImage.Format.Format_RGBA8888)
        width = img.width()
        height = img.height()
        if width <= 0 or height <= 0:
            return ""

        ptr = img.constBits()
        buffer = bytes(ptr)
        if len(buffer) < width * height * 4:
            return ""
        arr = np.frombuffer(buffer, np.uint8).reshape((height, width, 4))
        rgb = arr[:, :, :3]
        bgr = rgb[:, :, ::-1].copy()

        result, _ = self._ocr(bgr)
        if not result:
            return ""

        texts = [item[1] for item in result if len(item) >= 2 and item[1]]
        return "\n".join(texts)

    def recognize_qpixmap(self, pixmap: QPixmap) -> str:
        if pixmap is None or pixmap.isNull():
            return ""
        return self.recognize_qimage(pixmap.toImage())
