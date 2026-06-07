"""
动画辅助模块 - 提供常用的UI动画
"""
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtWidgets import QWidget, QGraphicsOpacityEffect


class FadeInOutAnimation:
    """淡入淡出动画"""
    
    @staticmethod
    def fade_out(widget: QWidget, duration: int = 300, callback=None):
        """淡出动画"""
        effect = QGraphicsOpacityEffect()
        widget.setGraphicsEffect(effect)
        
        animation = QPropertyAnimation(effect, b"opacity")
        animation.setDuration(duration)
        animation.setStartValue(1.0)
        animation.setEndValue(0.0)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        if callback:
            animation.finished.connect(callback)
        
        animation.start()
        return animation
    
    @staticmethod
    def fade_in(widget: QWidget, duration: int = 300, callback=None):
        """淡入动画"""
        effect = QGraphicsOpacityEffect()
        widget.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        
        animation = QPropertyAnimation(effect, b"opacity")
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        if callback:
            animation.finished.connect(callback)
        
        animation.start()
        return animation
    
    @staticmethod
    def fade_transition(widget: QWidget, duration: int = 300, callback=None):
        """淡入淡出过渡动画"""
        def on_fade_out_finished():
            if callback:
                callback()
            FadeInOutAnimation.fade_in(widget, duration)
        
        FadeInOutAnimation.fade_out(widget, duration // 2, on_fade_out_finished)
