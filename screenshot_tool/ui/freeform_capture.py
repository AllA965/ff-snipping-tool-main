"""
任意形状截图模块
"""
from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt, Signal, QPoint, QRect
from PySide6.QtGui import (
    QPainter, QColor, QPen, QPixmap, QPolygon, QPainterPath,
    QGuiApplication, QBrush, QRegion
)
from ui.region_capture import CaptureToolbar
import math


class FreeformCaptureWindow(QWidget):
    """任意形状截图窗口"""
    
    capture_completed = Signal(QPixmap)
    capture_cancelled = Signal()
    
    def __init__(self, screen_capture):
        super().__init__()
        self.screen_capture = screen_capture
        
        # 绘制形状阶段
        self.drawing = False
        self.points = []
        self.background = None
        self.bg_img = None
        
        # 选区完成后的标注阶段
        self.selection_done = False
        self.tool = None
        self.color = QColor(255, 0, 0)
        self.line_width = 2
        self.annotation_drawing = False
        self.draw_start = QPoint()
        self.draw_end = QPoint()
        self.pen_pts = []
        
        # 历史记录
        self.history = []
        
        # 移动形状
        self.moving_shape = False
        self.move_start_pos = QPoint()
        self.original_points = []
        self.original_history = []
        
        self.toolbar = None
        self.bounding_rect = None
        
        self.setup_ui()
    
    def setup_ui(self):
        # 使用 Tool 标志，与 RegionCaptureWindow 保持一致
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        
        screens = QGuiApplication.screens()
        total_rect = QRect()
        for screen in screens:
            total_rect = total_rect.united(screen.geometry())
        
        self.setGeometry(total_rect)
        self.background = self.screen_capture.capture_all_screens()
        if self.background:
            self.bg_img = self.background.toImage()
        
        # 工具栏
        self.toolbar = CaptureToolbar(self)
        self.toolbar.hide()
        self.toolbar.tool_selected.connect(self._set_tool)
        self.toolbar.color_changed.connect(lambda c: setattr(self, 'color', c))
        self.toolbar.width_changed.connect(lambda w: setattr(self, 'line_width', w))
        self.toolbar.undo_clicked.connect(self._undo)
        self.toolbar.save_clicked.connect(self._save)
        self.toolbar.copy_clicked.connect(self._copy)
        self.toolbar.cancel_clicked.connect(self._cancel)
        self.toolbar.confirm_clicked.connect(self._confirm)
        self.toolbar.pin_clicked.connect(self._pin_to_desktop)
        self.toolbar.edit_clicked.connect(self._open_editor)
        self.toolbar.copy_share_clicked.connect(self._copy_and_share)
        
        # 提示标签
        self.hint_label = QLabel(self)
        self.hint_label.setStyleSheet("""
            QLabel {
                background: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
                font-size: 12px;
            }
        """)
        self.hint_label.setText("按住鼠标绘制任意形状 | 松开完成 | ESC 取消")
        self.hint_label.adjustSize()
        self.hint_label.move(20, 20)
    
    def _set_tool(self, t):
        self.tool = t
    
    def _pos_toolbar(self):
        if not self.toolbar or not self.bounding_rect:
            return
        self.toolbar.adjustSize()
        tw, th = self.toolbar.width(), self.toolbar.height()
        
        x = self.bounding_rect.right() - tw
        y = self.bounding_rect.bottom() + 6
        
        if y + th > self.height():
            y = self.bounding_rect.top() - th - 6
        if y < 0:
            y = self.bounding_rect.bottom() - th - 6
        if x < 0:
            x = 0
        if x + tw > self.width():
            x = self.width() - tw
        
        self.toolbar.move(int(x), int(y))
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制背景
        if self.background:
            painter.drawPixmap(0, 0, self.background)
        
        # 绘制遮罩
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        
        # 如果有绘制的路径
        if len(self.points) > 2:
            # 创建路径
            path = QPainterPath()
            path.moveTo(self.points[0])
            for point in self.points[1:]:
                path.lineTo(point)
            path.closeSubpath()
            
            # 清除路径内的遮罩，显示原图
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.setClipPath(path)
            if self.background:
                painter.drawPixmap(0, 0, self.background)
            
            # 绘制标注
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            for tool, data in self.history:
                self._draw_item(painter, tool, data)
            
            # 临时绘制
            if self.annotation_drawing and self.tool:
                self._draw_temp(painter)
            
            # 绘制边框
            painter.setClipping(False)
            painter.setPen(QPen(QColor(0, 120, 215), 2, Qt.PenStyle.SolidLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
        
        # 绘制当前绘制的线条
        if len(self.points) > 1 and not self.selection_done:
            painter.setPen(QPen(QColor(0, 120, 215), 2))
            for i in range(len(self.points) - 1):
                painter.drawLine(self.points[i], self.points[i + 1])
    
    def _draw_item(self, p, tool, data):
        c = data.get('color', self.color)
        w = data.get('width', self.line_width)
        s = data.get('start', QPoint())
        e = data.get('end', QPoint())
        
        pen = QPen(c, w)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        
        if tool == 'rect':
            p.drawRect(QRect(s, e).normalized())
        elif tool == 'ellipse':
            p.drawEllipse(QRect(s, e).normalized())
        elif tool == 'line':
            p.drawLine(s, e)
        elif tool == 'arrow':
            self._draw_arrow(p, s, e, c, w)
        elif tool == 'pen':
            pts = data.get('points', [])
            for i in range(1, len(pts)):
                p.drawLine(pts[i-1], pts[i])
        elif tool == 'mosaic':
            self._draw_mosaic(p, QRect(s, e).normalized())
        elif tool == 'blur':
            self._draw_blur(p, QRect(s, e).normalized())
        elif tool == 'text':
            txt = data.get('text', '')
            if txt:
                p.setPen(c)
                font = p.font()
                font.setPointSize(max(12, w * 4))
                p.setFont(font)
                p.drawText(s, txt)
        elif tool == 'eraser':
            pts = data.get('points', [])
            if pts and self.background:
                eraser_size = max(10, w * 3)
                for pt in pts:
                    rect = QRect(pt.x() - eraser_size//2, pt.y() - eraser_size//2, eraser_size, eraser_size)
                    p.drawPixmap(rect, self.background, rect)
    
    def _draw_temp(self, p):
        data = {
            'color': self.color,
            'width': self.line_width,
            'start': self.draw_start,
            'end': self.draw_end,
        }
        if self.tool in ('pen', 'eraser'):
            data['points'] = self.pen_pts
        self._draw_item(p, self.tool, data)
    
    def _draw_arrow(self, p, s, e, c, w):
        p.drawLine(s, e)
        if s == e:
            return
        angle = math.atan2(e.y() - s.y(), e.x() - s.x())
        sz = max(8, w * 3)
        p1 = QPoint(int(e.x() - sz * math.cos(angle - 0.5)), int(e.y() - sz * math.sin(angle - 0.5)))
        p2 = QPoint(int(e.x() - sz * math.cos(angle + 0.5)), int(e.y() - sz * math.sin(angle + 0.5)))
        p.setBrush(QBrush(c))
        p.drawPolygon(QPolygon([e, p1, p2]))
    
    def _draw_mosaic(self, p, rect):
        if not self.bg_img or rect.isEmpty():
            return
        bs = 8
        for x in range(rect.left(), rect.right(), bs):
            for y in range(rect.top(), rect.bottom(), bs):
                br = QRect(x, y, bs, bs).intersected(rect)
                if br.isEmpty():
                    continue
                cx, cy = br.center().x(), br.center().y()
                if 0 <= cx < self.bg_img.width() and 0 <= cy < self.bg_img.height():
                    p.fillRect(br, QColor(self.bg_img.pixel(cx, cy)))
    
    def _draw_blur(self, p, rect):
        """绘制模糊效果"""
        if not self.bg_img or rect.isEmpty():
            return
        bs = 12
        for x in range(rect.left(), rect.right(), bs):
            for y in range(rect.top(), rect.bottom(), bs):
                br = QRect(x, y, bs, bs).intersected(rect)
                if br.isEmpty():
                    continue
                r_sum, g_sum, b_sum, count = 0, 0, 0, 0
                for px in range(br.left(), br.right(), 2):
                    for py in range(br.top(), br.bottom(), 2):
                        if 0 <= px < self.bg_img.width() and 0 <= py < self.bg_img.height():
                            pixel = QColor(self.bg_img.pixel(px, py))
                            r_sum += pixel.red()
                            g_sum += pixel.green()
                            b_sum += pixel.blue()
                            count += 1
                if count > 0:
                    avg_color = QColor(r_sum // count, g_sum // count, b_sum // count)
                    p.fillRect(br, avg_color)
    
    def _is_in_shape(self, pos):
        """检查点是否在形状内"""
        if len(self.points) < 3:
            return False
        path = QPainterPath()
        path.moveTo(self.points[0])
        for point in self.points[1:]:
            path.lineTo(point)
        path.closeSubpath()
        return path.contains(pos)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            
            # 检查是否点击在工具栏上，如果是则忽略，让工具栏处理
            if self.toolbar and self.toolbar.isVisible():
                toolbar_rect = self.toolbar.geometry()
                if toolbar_rect.contains(pos):
                    # 点击在工具栏上，不处理，让事件传递给工具栏
                    return
            
            # 标注模式
            if self.selection_done and self.tool and self.tool != 'move' and self._is_in_shape(pos):
                if self.tool == 'text':
                    self._input_text(pos)
                    return
                self.annotation_drawing = True
                self.draw_start = pos
                self.draw_end = pos
                self.pen_pts = [pos] if self.tool in ('pen', 'eraser') else []
                return
            
            # 移动模式 (当选择移动工具，或者未选择工具但在形状内点击时)
            if self.selection_done and (not self.tool or self.tool == 'move') and self._is_in_shape(pos):
                self.moving_shape = True
                self.move_start_pos = pos
                self.original_points = list(self.points)
                self.original_history = []
                for tool, data in self.history:
                    self.original_history.append((tool, dict(data)))
                self.setCursor(Qt.CursorShape.SizeAllCursor)
                return
            
            # 绘制形状模式
            if not self.selection_done:
                self.drawing = True
                self.points = [event.pos()]
        elif event.button() == Qt.MouseButton.RightButton:
            if self.selection_done:
                # 重新绘制
                self.selection_done = False
                self.points = []
                self.history.clear()
                self.toolbar.hide()
                self.hint_label.show()
                self.update()
            else:
                self.capture_cancelled.emit()
                self.close()
    
    def mouseMoveEvent(self, event):
        pos = event.pos()
        
        # 检查是否在工具栏上，如果是则忽略
        if self.toolbar and self.toolbar.isVisible():
            toolbar_rect = self.toolbar.geometry()
            if toolbar_rect.contains(pos):
                return
        
        if self.moving_shape:
            delta = pos - self.move_start_pos
            # 移动主形状点
            self.points = [p + delta for p in self.original_points]
            
            # 移动标注历史
            new_history = []
            for tool, data in self.original_history:
                new_data = dict(data)
                if 'start' in data:
                    new_data['start'] = data['start'] + delta
                if 'end' in data:
                    new_data['end'] = data['end'] + delta
                if 'points' in data:
                    new_data['points'] = [p + delta for p in data['points']]
                new_history.append((tool, new_data))
            self.history = new_history
            
            # 更新边界和工具栏
            polygon = QPolygon([QPoint(int(p.x()), int(p.y())) for p in self.points])
            self.bounding_rect = polygon.boundingRect()
            self._pos_toolbar()
            self.update()
            return
            
        if self.annotation_drawing:
            self.draw_end = pos
            if self.tool in ('pen', 'eraser'):
                self.pen_pts.append(pos)
            self.update()
        elif self.drawing:
            self.points.append(pos)
            self.update()
        
        # 光标反馈
        if self.selection_done:
            if self._is_in_shape(pos):
                if not self.tool or self.tool == 'move':
                    self.setCursor(Qt.CursorShape.SizeAllCursor)
                else:
                    self.setCursor(Qt.CursorShape.CrossCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查是否在工具栏上，如果是则忽略
            if self.toolbar and self.toolbar.isVisible():
                toolbar_rect = self.toolbar.geometry()
                if toolbar_rect.contains(event.pos()):
                    return
            
            if self.moving_shape:
                self.moving_shape = False
                self.setCursor(Qt.CursorShape.ArrowCursor)
                return
            
            if self.annotation_drawing:
                # 保存标注
                data = {
                    'color': QColor(self.color),
                    'width': self.line_width,
                    'start': QPoint(self.draw_start),
                    'end': QPoint(self.draw_end),
                }
                if self.tool in ('pen', 'eraser'):
                    data['points'] = list(self.pen_pts)
                self.history.append((self.tool, data))
                self.annotation_drawing = False
                self.update()
                return
            
            if self.drawing:
                self.drawing = False
                
                if len(self.points) > 10:  # 至少需要一些点
                    self._show_toolbar()
                else:
                    self.points = []
                    self.update()
    
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.selection_done and self._is_in_shape(event.pos()):
                self._confirm()
    
    def keyPressEvent(self, event):
        k = event.key()
        mod = event.modifiers()
        
        if k == Qt.Key.Key_Escape:
            self._cancel()
        elif k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.selection_done:
                self._confirm()
        elif k == Qt.Key.Key_Z and mod & Qt.KeyboardModifier.ControlModifier:
            self._undo()
        elif k == Qt.Key.Key_C and mod & Qt.KeyboardModifier.ControlModifier:
            self._copy()
        elif k == Qt.Key.Key_S and mod & Qt.KeyboardModifier.ControlModifier:
            self._save()
    
    def _undo(self):
        if self.history:
            self.history.pop()
            self.update()
    
    def _save(self):
        from PySide6.QtWidgets import QFileDialog, QApplication
        from datetime import datetime
        px = self._result()
        if px and not px.isNull():
            name = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            path, _ = QFileDialog.getSaveFileName(self, "保存", name, "PNG (*.png);;JPEG (*.jpg)")
            if path:
                px.save(path)
    
    def _copy(self):
        from PySide6.QtWidgets import QApplication
        px = self._result()
        if px and not px.isNull():
            QApplication.clipboard().setPixmap(px)
    
    def _cancel(self):
        self.capture_cancelled.emit()
        self.close()
    
    def _confirm(self):
        px = self._result()
        if px and not px.isNull():
            self.capture_completed.emit(px)
        self.close()
    
    def _show_toolbar(self):
        """显示工具栏，进入标注模式"""
        if not self.background or len(self.points) < 3:
            return
        
        self.selection_done = True
        polygon = QPolygon([QPoint(int(p.x()), int(p.y())) for p in self.points])
        self.bounding_rect = polygon.boundingRect()
        
        self._pos_toolbar()
        self.toolbar.show()
        self.hint_label.hide()
        self.update()
    
    def _result(self) -> QPixmap:
        """获取结果"""
        if not self.background or len(self.points) < 3:
            return QPixmap()
        
        # 创建多边形
        polygon = QPolygon([QPoint(int(p.x()), int(p.y())) for p in self.points])
        
        # 获取边界矩形
        bounding_rect = polygon.boundingRect()
        
        # 创建结果图像（带透明背景）
        result = QPixmap(bounding_rect.size())
        result.fill(Qt.GlobalColor.transparent)
        
        # 绘制
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 平移多边形到原点
        translated_polygon = polygon.translated(-bounding_rect.topLeft())
        
        # 设置裁剪区域
        path = QPainterPath()
        path.addPolygon(translated_polygon.toPolygonF())
        painter.setClipPath(path)
        
        # 绘制背景图像的对应部分
        painter.drawPixmap(
            0, 0,
            self.background,
            bounding_rect.x(), bounding_rect.y(),
            bounding_rect.width(), bounding_rect.height()
        )
        
        # 绘制标注
        if self.history:
            offset = bounding_rect.topLeft()
            for tool, data in self.history:
                adj = dict(data)
                if 'start' in adj:
                    adj['start'] = data['start'] - offset
                if 'end' in adj:
                    adj['end'] = data['end'] - offset
                if 'points' in adj:
                    adj['points'] = [pt - offset for pt in data['points']]
                self._draw_item(painter, tool, adj)
        
        painter.end()
        
        return result

    def _input_text(self, pos):
        """输入文字"""
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "输入文字", "请输入要添加的文字:")
        if ok and text:
            data = {
                'color': QColor(self.color),
                'width': self.line_width,
                'start': QPoint(pos),
                'end': QPoint(pos),
                'text': text
            }
            self.history.append(('text', data))
            self.update()
    
    def _pin_to_desktop(self):
        """固定截图到桌面"""
        px = self._result()
        if px and not px.isNull():
            from ui.pin_window import PinWindow
            self.pin_win = PinWindow(px)
            self.pin_win.show()
            self.close()
    
    def _open_editor(self):
        """打开编辑器"""
        px = self._result()
        if px and not px.isNull():
            self.capture_completed.emit(px)
            self.close()
    
    def _copy_and_share(self):
        """复制图片并最小化软件"""
        from PySide6.QtWidgets import QApplication
        px = self._result()
        if px and not px.isNull():
            # 复制到剪贴板
            QApplication.clipboard().setPixmap(px)
            # 关闭截图窗口
            self.close()
            # 最小化主窗口
            for widget in QApplication.topLevelWidgets():
                if widget.isVisible() and hasattr(widget, 'showMinimized'):
                    widget.showMinimized()
                    break
