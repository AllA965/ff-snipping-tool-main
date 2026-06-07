"""
区域截图模块 - 类似微信/QQ截图风格
"""
from PySide6.QtWidgets import (
    QWidget, QApplication, QLabel, QHBoxLayout,
    QFrame, QSpinBox, QToolButton, QFileDialog
)
from PySide6.QtCore import Qt, Signal, QRect, QPoint, QTimer
from PySide6.QtGui import (
    QPainter, QColor, QPen, QPixmap, QCursor, QFont,
    QGuiApplication, QBrush, QPolygon
)
from datetime import datetime
import math
from ui.vector_icons import create_icon


class CaptureToolbar(QFrame):
    """截图工具栏 - 精简版（只保留核心功能）"""
    
    tool_selected = Signal(str)
    color_changed = Signal(QColor)
    width_changed = Signal(int)
    undo_clicked = Signal()
    save_clicked = Signal()
    copy_clicked = Signal()
    cancel_clicked = Signal()
    confirm_clicked = Signal()
    pin_clicked = Signal()  # 固定到桌面
    edit_clicked = Signal()  # 进入编辑器
    copy_share_clicked = Signal()  # 复制并分享
    ocr_clicked = Signal()  # 识别文字
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_tool = None
        self.current_color = QColor(255, 0, 0)
        self.setCursor(Qt.CursorShape.ArrowCursor)  # 确保工具栏显示标准光标
        self.setup_ui()
    
    def setup_ui(self):
        self.setStyleSheet("""
            QFrame {
                background: #f5f5f5;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(2)
        
        btn_style = """
            QToolButton {
                background: transparent;
                border: none;
                border-radius: 3px;
                padding: 4px;
                min-width: 26px;
                min-height: 26px;
            }
            QToolButton:hover { background: #e0e0e0; }
            QToolButton:checked { background: #cce8ff; border: 1px solid #99d1ff; }
        """
        
        # 只保留移动工具
        self.tool_buttons = {}
        move_btn = QToolButton()
        move_btn.setIcon(create_icon("move", 20))
        move_btn.setToolTip("移动选区")
        move_btn.setCheckable(True)
        move_btn.setStyleSheet(btn_style)
        move_btn.clicked.connect(lambda: self._on_tool_clicked("move"))
        layout.addWidget(move_btn)
        self.tool_buttons["move"] = move_btn
        
        layout.addWidget(self._sep())
        
        # 取消
        cancel_btn = QToolButton()
        cancel_btn.setIcon(create_icon("cancel", 20))
        cancel_btn.setToolTip("取消 (ESC)")
        cancel_btn.setStyleSheet(btn_style)
        cancel_btn.clicked.connect(self.cancel_clicked.emit)
        layout.addWidget(cancel_btn)
        
        # 固定到桌面
        pin_btn = QToolButton()
        pin_btn.setIcon(create_icon("pin", 20))
        pin_btn.setToolTip("固定到桌面")
        pin_btn.setStyleSheet(btn_style)
        pin_btn.clicked.connect(self.pin_clicked.emit)
        layout.addWidget(pin_btn)
        
        # 保存
        save_btn = QToolButton()
        save_btn.setIcon(create_icon("save", 20))
        save_btn.setToolTip("保存 (Ctrl+S)")
        save_btn.setStyleSheet(btn_style)
        save_btn.clicked.connect(self.save_clicked.emit)
        layout.addWidget(save_btn)
        
        layout.addWidget(self._sep())
        
        # 编辑（进入编辑器）
        edit_btn = QToolButton()
        edit_btn.setIcon(create_icon("edit", 20))
        edit_btn.setToolTip("编辑 (进入编辑器)")
        edit_btn.setStyleSheet(btn_style + "QToolButton { background: #fff3e0; } QToolButton:hover { background: #ffe0b2; }")
        edit_btn.clicked.connect(self.edit_clicked.emit)
        layout.addWidget(edit_btn)
        
        # 复制并分享
        copy_share_btn = QToolButton()
        copy_share_btn.setIcon(create_icon("copy", 20))
        copy_share_btn.setToolTip("复制并分享 (Ctrl+C)")
        copy_share_btn.setStyleSheet(btn_style + "QToolButton { background: #e8f5e9; } QToolButton:hover { background: #c8e6c9; }")
        copy_share_btn.clicked.connect(self.copy_share_clicked.emit)
        layout.addWidget(copy_share_btn)

        # 文字识别
        ocr_btn = QToolButton()
        ocr_btn.setIcon(create_icon("ocr", 20))
        ocr_btn.setToolTip("识别文字")
        ocr_btn.setStyleSheet(btn_style)
        ocr_btn.clicked.connect(self.ocr_clicked.emit)
        layout.addWidget(ocr_btn)
    
    def _sep(self):
        s = QFrame()
        s.setFixedSize(1, 20)
        s.setStyleSheet("background: #ccc;")
        return s
    
    def _on_tool_clicked(self, tid):
        for t, btn in self.tool_buttons.items():
            btn.setChecked(t == tid)
        self.current_tool = tid
        self.tool_selected.emit(tid)
    
    def clear_selection(self):
        for btn in self.tool_buttons.values():
            btn.setChecked(False)
        self.current_tool = None


class RegionCaptureWindow(QWidget):
    """区域截图窗口"""
    
    capture_completed = Signal(QPixmap)
    capture_cancelled = Signal()
    
    @property
    def selection_rect(self):
        """兼容旧接口"""
        return self.selection
    
    def __init__(self, screen_capture, color_mode="blue"):
        super().__init__()
        self.screen_capture = screen_capture
        self.color_mode = color_mode
        
        # 状态
        self.selecting = False
        self.moving = False
        self.resizing = False
        self.drawing = False
        self.resize_handle = None
        self.selection_done = False
        
        # 坐标
        self.start_pt = QPoint()
        self.selection = QRect()
        self.move_start = QPoint()
        self.orig_rect = QRect()
        
        # 绘图
        self.tool = None
        self.color = QColor(255, 0, 0)
        self.line_width = 2
        self.draw_start = QPoint()
        self.draw_end = QPoint()
        self.pen_pts = []
        
        # 历史
        self.history = []
        
        self.bg = None
        self.bg_img = None
        self.toolbar = None
        
        self._setup()

    def _setup(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)  # 启用鼠标追踪，使mouseMoveEvent在未按下时也能触发
        
        # 全屏
        total = QRect()
        for s in QGuiApplication.screens():
            total = total.united(s.geometry())
        self.setGeometry(total)
        
        # 截取背景
        self.bg = self.screen_capture.capture_all_screens()
        if self.bg:
            self.bg_img = self.bg.toImage()
        
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
        self.toolbar.ocr_clicked.connect(self._ocr_selection)
        
        # 提示
        self.hint = QLabel(self)
        self.hint.setStyleSheet("""
            QLabel {
                background: rgba(0,0,0,0.75);
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
        """)
        self.hint.setText("拖动选择区域 | ESC取消")
        self.hint.setCursor(Qt.CursorShape.ArrowCursor)  # 提示文字也使用箭头
        self.hint.adjustSize()
        self.hint.move(15, 15)
    
    def _set_tool(self, t):
        self.tool = t
    
    def _pos_toolbar(self):
        if not self.toolbar or self.selection.isNull():
            return
        self.toolbar.adjustSize()
        tw, th = self.toolbar.width(), self.toolbar.height()
        
        x = self.selection.right() - tw
        y = self.selection.bottom() + 6
        
        if y + th > self.height():
            y = self.selection.top() - th - 6
        if y < 0:
            y = self.selection.bottom() - th - 6
        if x < 0:
            x = 0
        if x + tw > self.width():
            x = self.width() - tw
        
        self.toolbar.move(int(x), int(y))
    
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self.bg:
            p.drawPixmap(0, 0, self.bg)
        
        # 遮罩
        p.fillRect(self.rect(), QColor(0, 0, 0, 80))
        
        if self.selection.isValid() and not self.selection.isNull():
            # 选区内容
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            if self.bg:
                p.drawPixmap(self.selection, self.bg, self.selection)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            
            # 绘制标注
            for tool, data in self.history:
                self._draw_item(p, tool, data)
            
            # 临时绘制
            if self.drawing and self.tool:
                self._draw_temp(p)
            
            # 边框
            bc = QColor(0, 120, 215) if self.color_mode == "blue" else QColor(220, 53, 69)
            p.setPen(QPen(bc, 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(self.selection)
            
            # 手柄
            p.setBrush(QColor(255, 255, 255))
            p.setPen(QPen(bc, 1))
            for h in self._handles().values():
                p.drawRect(h)
            
            # 尺寸
            self._draw_size(p)
    
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
            # 橡皮擦 - 用原图覆盖
            pts = data.get('points', [])
            if pts and self.bg:
                eraser_size = max(10, w * 3)
                for pt in pts:
                    rect = QRect(pt.x() - eraser_size//2, pt.y() - eraser_size//2, eraser_size, eraser_size)
                    p.drawPixmap(rect, self.bg, rect)
    
    def _draw_temp(self, p):
        data = {
            'color': self.color,
            'width': self.line_width,
            'start': self.draw_start,
            'end': self.draw_end,
        }
        if self.tool == 'pen' or self.tool == 'eraser':
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
        # 简单的模糊效果 - 使用更大的块
        bs = 12
        for x in range(rect.left(), rect.right(), bs):
            for y in range(rect.top(), rect.bottom(), bs):
                br = QRect(x, y, bs, bs).intersected(rect)
                if br.isEmpty():
                    continue
                # 计算区域平均颜色
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
    
    def _draw_size(self, p):
        txt = f"{self.selection.width()} × {self.selection.height()}"
        p.setFont(QFont("Microsoft YaHei", 9))
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(txt) + 12
        th = fm.height() + 6
        
        x = self.selection.left()
        y = self.selection.top() - th - 4
        if y < 0:
            y = self.selection.bottom() + 4
        
        p.fillRect(x, y, tw, th, QColor(0, 0, 0, 180))
        p.setPen(Qt.GlobalColor.white)
        p.drawText(x + 6, y + th - 5, txt)
    
    def _handles(self, for_hit_test=False):
        """获取手柄矩形，for_hit_test=True时返回更大的检测区域"""
        r = self.selection
        if for_hit_test:
            sz, h = 16, 8  # 更大的检测区域
        else:
            sz, h = 8, 4   # 绘制大小
        return {
            'tl': QRect(r.left()-h, r.top()-h, sz, sz),
            't': QRect(r.center().x()-h, r.top()-h, sz, sz),
            'tr': QRect(r.right()-h, r.top()-h, sz, sz),
            'l': QRect(r.left()-h, r.center().y()-h, sz, sz),
            'r': QRect(r.right()-h, r.center().y()-h, sz, sz),
            'bl': QRect(r.left()-h, r.bottom()-h, sz, sz),
            'b': QRect(r.center().x()-h, r.bottom()-h, sz, sz),
            'br': QRect(r.right()-h, r.bottom()-h, sz, sz),
        }

    def mousePressEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            if e.button() == Qt.MouseButton.RightButton:
                if self.selection.isNull():
                    self._cancel()
                else:
                    self.selection = QRect()
                    self.selection_done = False
                    self.toolbar.hide()
                    self.hint.show()
                    self.history.clear()
                    self.update()
            return
        
        pos = e.pos()
        
        # 绘图模式
        if self.selection_done and self.tool and self.selection.contains(pos):
            # 移动工具 - 直接进入移动模式
            if self.tool == 'move':
                self.moving = True
                self.move_start = pos
                self.orig_rect = QRect(self.selection)
                self.setCursor(Qt.CursorShape.SizeAllCursor)
                return
            # 文字工具特殊处理
            if self.tool == 'text':
                self._input_text(pos)
                return
            self.drawing = True
            self.draw_start = pos
            self.draw_end = pos
            self.pen_pts = [pos] if self.tool in ('pen', 'eraser') else []
            return
        
        # 调整手柄（使用更大的检测区域）
        if not self.selection.isNull():
            for name, rect in self._handles(for_hit_test=True).items():
                if rect.contains(pos):
                    self.resizing = True
                    self.resize_handle = name
                    self.move_start = pos
                    self.orig_rect = QRect(self.selection)
                    return
            
            # 移动
            if self.selection.contains(pos):
                self.moving = True
                self.move_start = pos
                self.orig_rect = QRect(self.selection)
                self.setCursor(Qt.CursorShape.SizeAllCursor)
                return
        
        # 新选区
        self.selecting = True
        self.selection_done = False
        self.start_pt = pos
        self.selection = QRect()
        self.toolbar.hide()
        self.hint.show()
        self.history.clear()
    
    def mouseMoveEvent(self, e):
        pos = e.pos()
        
        if self.drawing:
            self.draw_end = pos
            if self.tool in ('pen', 'eraser'):
                self.pen_pts.append(pos)
            self.update()
        elif self.selecting:
            self.selection = QRect(self.start_pt, pos).normalized()
            self.update()
        elif self.moving:
            delta = pos - self.move_start
            new_r = self.orig_rect.translated(delta)
            # 边界检查
            if new_r.left() >= 0 and new_r.right() <= self.width():
                if new_r.top() >= 0 and new_r.bottom() <= self.height():
                    self.selection = new_r
                    self._pos_toolbar()
                    self.update()
        elif self.resizing:
            self._do_resize(pos)
            self._pos_toolbar()
            self.update()
        
        # 始终更新光标样式
        self._update_cursor(pos)
    
    def _do_resize(self, pos):
        r = QRect(self.orig_rect)
        d = pos - self.move_start
        h = self.resize_handle
        
        if 'l' in h:
            r.setLeft(self.orig_rect.left() + d.x())
        if 'r' in h:
            r.setRight(self.orig_rect.right() + d.x())
        if 't' in h:
            r.setTop(self.orig_rect.top() + d.y())
        if 'b' in h:
            r.setBottom(self.orig_rect.bottom() + d.y())
        
        self.selection = r.normalized()
    
    def _update_cursor(self, pos):
        # 如果正在移动，保持移动光标
        if self.moving:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
            return
        
        # 如果正在调整大小，保持对应的调整光标
        if self.resizing and self.resize_handle:
            cursors = {
                'tl': Qt.CursorShape.SizeFDiagCursor, 'br': Qt.CursorShape.SizeFDiagCursor,
                'tr': Qt.CursorShape.SizeBDiagCursor, 'bl': Qt.CursorShape.SizeBDiagCursor,
                't': Qt.CursorShape.SizeVerCursor, 'b': Qt.CursorShape.SizeVerCursor,
                'l': Qt.CursorShape.SizeHorCursor, 'r': Qt.CursorShape.SizeHorCursor,
            }
            self.setCursor(cursors.get(self.resize_handle, Qt.CursorShape.CrossCursor))
            return
        
        # 如果正在绘图，使用十字光标
        if self.drawing:
            self.setCursor(Qt.CursorShape.CrossCursor)
            return
        
        # 如果选区完成且有工具选中，在选区内使用十字光标
        if self.selection_done and self.tool and self.selection.contains(pos):
            self.setCursor(Qt.CursorShape.CrossCursor)
            return
        
        # 检查是否在手柄上（使用更大的检测区域）
        if not self.selection.isNull():
            cursors = {
                'tl': Qt.CursorShape.SizeFDiagCursor, 'br': Qt.CursorShape.SizeFDiagCursor,
                'tr': Qt.CursorShape.SizeBDiagCursor, 'bl': Qt.CursorShape.SizeBDiagCursor,
                't': Qt.CursorShape.SizeVerCursor, 'b': Qt.CursorShape.SizeVerCursor,
                'l': Qt.CursorShape.SizeHorCursor, 'r': Qt.CursorShape.SizeHorCursor,
            }
            for name, rect in self._handles(for_hit_test=True).items():
                if rect.contains(pos):
                    self.setCursor(cursors[name])
                    return
            
            # 在选区内使用移动光标
            if self.selection.contains(pos):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
                return
        
        # 默认使用十字光标
        self.setCursor(Qt.CursorShape.CrossCursor)
    
    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        
        if self.drawing:
            # 保存
            data = {
                'color': QColor(self.color),
                'width': self.line_width,
                'start': QPoint(self.draw_start),
                'end': QPoint(self.draw_end),
            }
            if self.tool == 'pen':
                data['points'] = list(self.pen_pts)
            self.history.append((self.tool, data))
            self.drawing = False
            self.update()
            return
        
        was_selecting = self.selecting
        self.selecting = False
        self.moving = False
        self.resizing = False
        self.resize_handle = None
        
        # 显示工具栏
        if was_selecting and self.selection.width() > 10 and self.selection.height() > 10:
            self.selection_done = True
            self._pos_toolbar()
            self.toolbar.show()
            self.hint.hide()
        
        self._update_cursor(e.pos())
    
    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if self.selection.contains(e.pos()):
                self._confirm()
    
    def keyPressEvent(self, e):
        k = e.key()
        mod = e.modifiers()
        
        if k == Qt.Key.Key_Escape:
            self._cancel()
        elif k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if not self.selection.isNull():
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
        px = self._result()
        if px and not px.isNull():
            name = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            path, _ = QFileDialog.getSaveFileName(self, "保存", name, "PNG (*.png);;JPEG (*.jpg)")
            if path:
                px.save(path)
    
    def _copy(self):
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
    
    def _result(self) -> QPixmap:
        """获取结果"""
        if not self.bg or self.selection.isNull():
            return QPixmap()
        
        result = self.bg.copy(self.selection)
        
        if self.history:
            p = QPainter(result)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            offset = self.selection.topLeft()
            
            for tool, data in self.history:
                adj = dict(data)
                if 'start' in adj:
                    adj['start'] = data['start'] - offset
                if 'end' in adj:
                    adj['end'] = data['end'] - offset
                if 'points' in adj:
                    adj['points'] = [pt - offset for pt in data['points']]
                self._draw_item(p, tool, adj)
            
            p.end()
        
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
        """打开编辑器窗口"""
        px = self._result()
        if px and not px.isNull():
            from ui.editor_window import EditorWindow
            from core.config import Config
            config = Config()
            self.editor_win = EditorWindow(px, config)
            self.editor_win.show()
            self.close()
    
    def _copy_and_share(self):
        """复制图片并最小化软件"""
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

    def _ocr_selection(self):
        px = self._result()
        if not px or px.isNull():
            return
        
        try:
            from core.ocr_engine import OCREngine, OCRWorker
        except Exception:
            from ui.modern_dialog import ModernMessageBox
            ModernMessageBox.warning(self, "OCR 错误", "本地 OCR 引擎未就绪，请检查依赖。")
            return

        # 禁用工具栏防止重复点击
        self.toolbar.setEnabled(False)
        self.setCursor(Qt.CursorShape.WaitCursor)
        
        # 创建工作线程
        self.ocr_worker = OCRWorker(px.toImage())
        
        def on_finished(text):
            self.toolbar.setEnabled(True)
            self.setCursor(Qt.CursorShape.CrossCursor)
            
            if not text or not text.strip():
                from ui.modern_dialog import ModernMessageBox
                ModernMessageBox.information(self, "识别结果", "未识别到文字。")
                return

            from ui.modern_dialog import OcrTextDialog
            from PySide6.QtWidgets import QApplication, QDialog
            dlg = OcrTextDialog(text, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                QApplication.clipboard().setText(dlg.result_text)
        
        def on_error(err_msg):
            self.toolbar.setEnabled(True)
            self.setCursor(Qt.CursorShape.CrossCursor)
            from ui.modern_dialog import ModernMessageBox
            ModernMessageBox.warning(self, "OCR 错误", f"识别失败: {err_msg}")

        self.ocr_worker.finished.connect(on_finished)
        self.ocr_worker.error.connect(on_error)
        self.ocr_worker.start()
