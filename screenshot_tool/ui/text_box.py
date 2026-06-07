"""
可缩放文本框组件 - PixPin 风格
支持：拖拽移动、8个圆形手柄缩放、旋转手柄、虚线边框
"""
from PySide6.QtWidgets import QWidget, QApplication, QMenu
from PySide6.QtCore import Qt, Signal, QPoint, QSize, QRect, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QFontMetrics, QAction


class TextBoxWidget(QWidget):
    """PixPin 风格的可缩放文本框"""
    
    text_confirmed = Signal(str)
    cancelled = Signal()
    activated = Signal(object)  # 文本框被激活时发出信号
    delete_requested = Signal(object)  # 请求删除文本框
    
    # 手柄类型
    HANDLE_NONE = 0
    HANDLE_TOP = 1
    HANDLE_BOTTOM = 2
    HANDLE_LEFT = 3
    HANDLE_RIGHT = 4
    HANDLE_TOP_LEFT = 5
    HANDLE_TOP_RIGHT = 6
    HANDLE_BOTTOM_LEFT = 7
    HANDLE_BOTTOM_RIGHT = 8
    HANDLE_ROTATE = 9
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.font_size = 20  # 原始字体大小（用于渲染到图像）
        self.display_scale = 1.0  # 显示缩放比例
        self.text_color = QColor(0, 180, 80)
        self._text = ""
        self._cursor_visible = True
        self._cursor_pos = 0
        self._dragging = False
        self._resizing = False
        self._drag_start = QPoint()
        self._resize_start = QPoint()
        self._original_rect = QRect()
        self._active_handle = self.HANDLE_NONE
        self._handle_radius = 6
        self._rotate_handle_distance = 25
        self._is_active = False  # 是否为当前激活的文本框
        self._setup_ui()
        self._start_cursor_blink()
    
    def _setup_ui(self):
        self.setMinimumSize(50, 40)
        self.resize(100, 70)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # 启用输入法支持（中文输入等）
        self.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, True)
    
    def _start_cursor_blink(self):
        self._cursor_timer = QTimer(self)
        self._cursor_timer.timeout.connect(self._toggle_cursor)
        self._cursor_timer.start(530)
    
    def _toggle_cursor(self):
        self._cursor_visible = not self._cursor_visible
        self.update()

    def set_font_size(self, size: int):
        self.font_size = max(8, min(72, size))
        self.update()
    
    def set_color(self, color: QColor):
        self.text_color = color
        self.update()
    
    def _get_content_rect(self) -> QRect:
        margin = self._handle_radius + 2
        top_margin = self._rotate_handle_distance + margin
        return self.rect().adjusted(margin, top_margin, -margin, -margin)
    
    def _get_handle_positions(self, rect: QRect) -> dict:
        cx, cy = rect.center().x(), rect.center().y()
        l, r, t, b = rect.left(), rect.right(), rect.top(), rect.bottom()
        return {
            self.HANDLE_TOP: QPoint(cx, t),
            self.HANDLE_BOTTOM: QPoint(cx, b),
            self.HANDLE_LEFT: QPoint(l, cy),
            self.HANDLE_RIGHT: QPoint(r, cy),
            self.HANDLE_TOP_LEFT: QPoint(l, t),
            self.HANDLE_TOP_RIGHT: QPoint(r, t),
            self.HANDLE_BOTTOM_LEFT: QPoint(l, b),
            self.HANDLE_BOTTOM_RIGHT: QPoint(r, b),
            self.HANDLE_ROTATE: QPoint(cx, t - self._rotate_handle_distance),
        }
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self._get_content_rect()
        
        # 边框 - 激活状态用蓝色实线，非激活用灰色虚线
        if self._is_active or self.hasFocus():
            pen = QPen(QColor(0, 120, 215), 2, Qt.PenStyle.SolidLine)
        else:
            pen = QPen(QColor(128, 128, 128), 1, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)
        
        # 文本和光标
        self._draw_text(painter, rect)
        
        # 控制手柄 - 只在激活状态显示
        if self._is_active or self.hasFocus():
            self._draw_handles(painter, rect)
    
    def _draw_text(self, painter: QPainter, rect: QRect):
        # 编辑时字体大小固定不变
        font = QFont("Microsoft YaHei", self.font_size)
        painter.setFont(font)
        painter.setPen(self.text_color)
        fm = QFontMetrics(font)
        
        # 内边距固定
        padding_x = 6
        padding_y = 4
        text_rect = rect.adjusted(padding_x, padding_y, -padding_x, -padding_y)
        
        if self._text:
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, self._text)
        
        # 光标
        if self._cursor_visible and self.hasFocus():
            cursor_x = text_rect.left()
            if self._text and self._cursor_pos > 0:
                cursor_x += fm.horizontalAdvance(self._text[:self._cursor_pos])
            painter.setPen(QPen(self.text_color, 2))
            painter.drawLine(cursor_x, text_rect.top(), cursor_x, text_rect.top() + fm.height())
    
    def _draw_handles(self, painter: QPainter, rect: QRect):
        r = self._handle_radius
        handles = self._get_handle_positions(rect)
        
        for handle_type, pos in handles.items():
            painter.setPen(QPen(QColor(128, 128, 128), 1))
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            
            if handle_type == self.HANDLE_ROTATE:
                # 连接线
                painter.drawLine(rect.center().x(), rect.top(), pos.x(), pos.y())
                painter.drawEllipse(pos, r + 2, r + 2)
            else:
                painter.drawEllipse(pos, r, r)

    def _hit_test_handle(self, pos: QPoint) -> int:
        rect = self._get_content_rect()
        handles = self._get_handle_positions(rect)
        
        for handle_type, handle_pos in handles.items():
            detect_r = self._handle_radius + 5
            dx = pos.x() - handle_pos.x()
            dy = pos.y() - handle_pos.y()
            if dx * dx + dy * dy <= detect_r * detect_r:
                return handle_type
        return self.HANDLE_NONE
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            handle = self._hit_test_handle(pos)
            
            # 发出激活信号
            self.activated.emit(self)
            
            if handle != self.HANDLE_NONE and handle != self.HANDLE_ROTATE:
                self._resizing = True
                self._active_handle = handle
                self._resize_start = event.globalPos()
                self._original_rect = self.geometry()
            elif self._get_content_rect().contains(pos):
                self._dragging = True
                self._drag_start = event.pos()
            self.setFocus()
        # 不调用 super()，阻止事件传递到父控件
        event.accept()
    
    def mouseMoveEvent(self, event):
        pos = event.pos()
        
        if self._dragging:
            new_pos = self.mapToParent(pos - self._drag_start)
            # 边界检测 - 确保文本框不会被拖出父控件范围
            if self.parent():
                parent_rect = self.parent().rect()
                new_pos.setX(max(0, min(new_pos.x(), parent_rect.width() - self.width())))
                new_pos.setY(max(0, min(new_pos.y(), parent_rect.height() - self.height())))
            self.move(new_pos)
        elif self._resizing:
            self._apply_resize(event.globalPos())
        else:
            handle = self._hit_test_handle(pos)
            self._update_cursor(handle, pos)
        # 不调用 super()，阻止事件传递到父控件
        event.accept()
    
    def mouseReleaseEvent(self, event):
        self._dragging = False
        self._resizing = False
        self._active_handle = self.HANDLE_NONE
        # 不调用 super()，阻止事件传递到父控件
        event.accept()
    
    def set_active(self, active: bool):
        """设置激活状态"""
        if self._is_active != active:
            self._is_active = active
            self.update()
    
    def is_active(self) -> bool:
        """获取激活状态"""
        return self._is_active
    
    def _update_cursor(self, handle: int, pos: QPoint):
        cursors = {
            self.HANDLE_TOP: Qt.CursorShape.SizeVerCursor,
            self.HANDLE_BOTTOM: Qt.CursorShape.SizeVerCursor,
            self.HANDLE_LEFT: Qt.CursorShape.SizeHorCursor,
            self.HANDLE_RIGHT: Qt.CursorShape.SizeHorCursor,
            self.HANDLE_TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
            self.HANDLE_BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
            self.HANDLE_TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
            self.HANDLE_BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
            self.HANDLE_ROTATE: Qt.CursorShape.CrossCursor,
        }
        if handle in cursors:
            self.setCursor(cursors[handle])
        elif self._get_content_rect().contains(pos):
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def _apply_resize(self, global_pos: QPoint):
        delta = global_pos - self._resize_start
        new_rect = QRect(self._original_rect)
        min_w, min_h = 60, 50
        
        h = self._active_handle
        if h in [self.HANDLE_RIGHT, self.HANDLE_TOP_RIGHT, self.HANDLE_BOTTOM_RIGHT]:
            new_rect.setRight(max(new_rect.left() + min_w, self._original_rect.right() + delta.x()))
        if h in [self.HANDLE_LEFT, self.HANDLE_TOP_LEFT, self.HANDLE_BOTTOM_LEFT]:
            new_rect.setLeft(min(self._original_rect.left() + delta.x(), new_rect.right() - min_w))
        if h in [self.HANDLE_BOTTOM, self.HANDLE_BOTTOM_LEFT, self.HANDLE_BOTTOM_RIGHT]:
            new_rect.setBottom(max(new_rect.top() + min_h, self._original_rect.bottom() + delta.y()))
        if h in [self.HANDLE_TOP, self.HANDLE_TOP_LEFT, self.HANDLE_TOP_RIGHT]:
            new_rect.setTop(min(self._original_rect.top() + delta.y(), new_rect.bottom() - min_h))
        
        self.setGeometry(new_rect)

    def keyPressEvent(self, event):
        key = event.key()
        
        if key == Qt.Key.Key_Escape:
            self.cancelled.emit()
        elif key == Qt.Key.Key_Return:
            if event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                # Shift+回车：换行
                self._text = self._text[:self._cursor_pos] + '\n' + self._text[self._cursor_pos:]
                self._cursor_pos += 1
                self.update()
            else:
                # 回车：确认文本
                self.text_confirmed.emit(self._text)
        elif key == Qt.Key.Key_Backspace:
            if self._cursor_pos > 0:
                self._text = self._text[:self._cursor_pos-1] + self._text[self._cursor_pos:]
                self._cursor_pos -= 1
                self.update()
        elif key == Qt.Key.Key_Delete:
            if self._cursor_pos < len(self._text):
                # 删除光标后的字符
                self._text = self._text[:self._cursor_pos] + self._text[self._cursor_pos+1:]
                self.update()
            elif not self._text:
                # 文本为空时，删除整个文本框
                self.delete_requested.emit(self)
        elif key == Qt.Key.Key_Left:
            if self._cursor_pos > 0:
                self._cursor_pos -= 1
                self.update()
        elif key == Qt.Key.Key_Right:
            if self._cursor_pos < len(self._text):
                self._cursor_pos += 1
                self.update()
        elif key == Qt.Key.Key_Home:
            self._cursor_pos = 0
            self.update()
        elif key == Qt.Key.Key_End:
            self._cursor_pos = len(self._text)
            self.update()
        elif event.text() and event.text().isprintable():
            self._text = self._text[:self._cursor_pos] + event.text() + self._text[self._cursor_pos:]
            self._cursor_pos += len(event.text())
            self.update()
        else:
            super().keyPressEvent(event)
    
    def focusInEvent(self, event):
        self._cursor_visible = True
        self.update()
        super().focusInEvent(event)
    
    def inputMethodEvent(self, event):
        """处理输入法事件（支持中文输入）"""
        commit_string = event.commitString()
        if commit_string:
            # 输入法确认的文本
            self._text = self._text[:self._cursor_pos] + commit_string + self._text[self._cursor_pos:]
            self._cursor_pos += len(commit_string)
            self.update()
        
        # 处理预编辑文本（输入法候选状态）
        preedit_string = event.preeditString()
        # 可以在这里显示预编辑文本，但简单起见我们只处理确认的文本
        
        event.accept()
    
    def inputMethodQuery(self, query):
        """响应输入法查询"""
        from PySide6.QtCore import Qt
        if query == Qt.InputMethodQuery.ImEnabled:
            return True
        elif query == Qt.InputMethodQuery.ImCursorRectangle:
            # 返回光标位置，用于输入法候选框定位
            font = QFont("Microsoft YaHei", self.font_size)
            fm = QFontMetrics(font)
            rect = self._get_content_rect()
            padding_x = 6
            padding_y = 4
            text_rect = rect.adjusted(padding_x, padding_y, -padding_x, -padding_y)
            cursor_x = text_rect.left()
            if self._text and self._cursor_pos > 0:
                cursor_x += fm.horizontalAdvance(self._text[:self._cursor_pos])
            cursor_y = text_rect.top()
            return QRect(cursor_x, cursor_y, 2, fm.height())
        elif query == Qt.InputMethodQuery.ImSurroundingText:
            return self._text
        elif query == Qt.InputMethodQuery.ImCursorPosition:
            return self._cursor_pos
        elif query == Qt.InputMethodQuery.ImAnchorPosition:
            return self._cursor_pos
        return super().inputMethodQuery(query)
    
    def contextMenuEvent(self, event):
        """右键菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: white; border: 1px solid #ddd; padding: 5px; }
            QMenu::item { padding: 6px 20px; border-radius: 3px; }
            QMenu::item:selected { background: #e5f3ff; }
        """)
        
        # 确认文本
        confirm_action = QAction("✓ 确认文本", menu)
        confirm_action.triggered.connect(lambda: self.text_confirmed.emit(self._text))
        menu.addAction(confirm_action)
        
        menu.addSeparator()
        
        # 删除文本框
        delete_action = QAction("🗑 删除文本框", menu)
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self))
        menu.addAction(delete_action)
        
        # 取消
        cancel_action = QAction("✗ 取消", menu)
        cancel_action.triggered.connect(lambda: self.cancelled.emit())
        menu.addAction(cancel_action)
        
        menu.exec(event.globalPos())
        event.accept()
    
    def get_text(self) -> str:
        return self._text
    
    def cleanup(self):
        """清理资源，停止定时器"""
        if hasattr(self, '_cursor_timer') and self._cursor_timer:
            self._cursor_timer.stop()
            self._cursor_timer = None
    
    def deleteLater(self):
        """重写deleteLater，确保先清理资源"""
        self.cleanup()
        super().deleteLater()
