"""
文本管理混入类 - 提供通用的文本框创建、管理和交互逻辑
"""
from PySide6.QtCore import Qt, QPoint, QRect, QSize, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from ui.text_box import TextBoxWidget

class TextManagerMixin:
    """
    文本管理混入类。
    要求子类具有以下属性/方法：
    - self.font_size: int
    - self.pen_color: QColor
    - self.text_boxes: list
    - self.active_text_box: TextBoxWidget
    - self.update(): method
    - self._get_image_pos(QPoint) -> QPoint (可选，用于同步图像坐标)
    - self._get_widget_pos(QPoint) -> QPoint (可选)
    - self.zoom_level: float (可选)
    """

    def init_text_manager(self):
        """初始化文本管理相关的变量"""
        self.text_boxes = []
        self.active_text_box = None
        self.creating_text_box = False
        self.text_box_start_pos = None
        self.text_box_preview_rect = None
        self.temp_pixmap = None

    def _add_text_at(self, widget_pos: QPoint, image_pos: QPoint = None):
        """在指定位置添加默认大小的文本框"""
        self._deactivate_all_text_boxes()
        
        text_box = TextBoxWidget(self)
        text_box.set_font_size(getattr(self, 'font_size', 20))
        text_box.set_color(getattr(self, 'pen_color', QColor(255, 0, 0)))
        
        # 计算边距，调整位置使鼠标在文本框正中间
        margin = text_box._handle_radius + 2
        top_margin = text_box._rotate_handle_distance + margin
        
        # 文本框居中于点击位置
        adjusted_x = widget_pos.x() - text_box.width() // 2
        adjusted_y = widget_pos.y() - text_box.height() // 2
        text_box.move(adjusted_x, adjusted_y)
        
        # 处理缩放和图像坐标（如果支持）
        zoom = getattr(self, 'zoom_level', 1.0)
        if image_pos:
            content_width = text_box.width() - margin * 2
            content_height = text_box.height() - top_margin - margin
            image_content_width = int(content_width / zoom) if zoom > 0 else content_width
            image_content_height = int(content_height / zoom) if zoom > 0 else content_height
            
            text_box.image_pos = QPoint(image_pos)
            text_box.image_content_size = QSize(image_content_width, image_content_height)
            text_box.base_zoom = zoom
            text_box.display_scale = zoom
            
        self._setup_text_box(text_box)
        return text_box
        
    def _add_text_with_rect(self, widget_rect: QRect, image_rect: QRect = None):
        """创建指定矩形区域的文本框"""
        self._deactivate_all_text_boxes()
        
        text_box = TextBoxWidget(self)
        text_box.set_font_size(getattr(self, 'font_size', 20))
        text_box.set_color(getattr(self, 'pen_color', QColor(255, 0, 0)))
        
        margin = text_box._handle_radius + 2
        top_margin = text_box._rotate_handle_distance + margin
        
        # 调整位置：使内容区域与预览框对齐
        adjusted_x = widget_rect.x() - margin
        adjusted_y = widget_rect.y() - top_margin
        adjusted_width = widget_rect.width() + margin * 2
        adjusted_height = widget_rect.height() + top_margin + margin
        text_box.setGeometry(adjusted_x, adjusted_y, adjusted_width, adjusted_height)
        
        zoom = getattr(self, 'zoom_level', 1.0)
        if image_rect:
            text_box.image_pos = QPoint(image_rect.topLeft())
            text_box.image_content_size = QSize(image_rect.width(), image_rect.height())
            text_box.base_zoom = zoom
            text_box.display_scale = zoom
            
        self._setup_text_box(text_box)
        return text_box

    def _setup_text_box(self, text_box):
        """设置文本框的信号连接和显示状态"""
        text_box.show()
        text_box.setFocus()
        text_box.set_active(True)
        
        # 连接信号
        text_box.text_confirmed.connect(lambda t, tb=text_box: self._on_text_confirmed(t, tb))
        text_box.cancelled.connect(lambda tb=text_box: self._on_text_cancelled(tb))
        text_box.activated.connect(self._on_text_box_activated)
        text_box.delete_requested.connect(self._on_text_box_delete)
        
        self.text_boxes.append(text_box)
        self.active_text_box = text_box

    def _activate_text_box(self, text_box):
        """激活指定的文本框"""
        self._deactivate_all_text_boxes()
        text_box.set_active(True)
        text_box.setFocus()
        self.active_text_box = text_box
        
    def _deactivate_all_text_boxes(self):
        """取消所有文本框的激活状态"""
        for tb in self.text_boxes:
            tb.set_active(False)
        self.active_text_box = None
            
    def _on_text_box_activated(self, text_box):
        """处理文本框激活信号"""
        self._activate_text_box(text_box)
        
    def _on_text_box_delete(self, text_box):
        """处理文本框删除信号"""
        self._remove_text_box(text_box)
        
    def _remove_text_box(self, text_box):
        """安全移除文本框"""
        if text_box in self.text_boxes:
            self.text_boxes.remove(text_box)
        if self.active_text_box == text_box:
            self.active_text_box = None
        text_box.cleanup()
        text_box.deleteLater()
        self.update()

    def _draw_text_box_preview(self, painter: QPainter, rect: QRect, color: QColor = QColor(0, 120, 215)):
        """绘制文本框拖拽预览框"""
        # 绘制虚线边框预览
        pen = QPen(color, 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)
        
        # 绘制半透明填充
        fill_color = QColor(color.red(), color.green(), color.blue(), 30)
        painter.fillRect(rect, fill_color)
        
        # 绘制尺寸提示
        size_text = f"{rect.width()} × {rect.height()}"
        font = QFont("Microsoft YaHei", 10)
        painter.setFont(font)
        painter.setPen(color)
        
        # 在矩形下方显示尺寸
        text_x = rect.center().x() - 30
        text_y = rect.bottom() + 18
        painter.drawText(text_x, text_y, size_text)

    def _on_text_confirmed(self, text: str, text_box: TextBoxWidget):
        """文本确认的回调（子类需实现具体逻辑）"""
        pass
        
    def _on_text_cancelled(self, text_box: TextBoxWidget):
        """文本取消的回调"""
        self._remove_text_box(text_box)

    def _check_click_on_text_box(self, widget_pos: QPoint) -> bool:
        """检查是否点击在现有文本框上，若是则激活它"""
        for text_box in self.text_boxes:
            local_pos = text_box.mapFromParent(widget_pos)
            if text_box.rect().contains(local_pos):
                self._activate_text_box(text_box)
                return True
        return False
