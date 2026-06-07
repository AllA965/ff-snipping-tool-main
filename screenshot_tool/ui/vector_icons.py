"""
矢量图标模块 - 一比一复刻截图工具栏图标
"""
from PySide6.QtCore import Qt, QRect, QPoint, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPixmap, QIcon, QPainterPath, QPolygonF


def create_icon(name: str, size: int = 24, color: QColor = None) -> QIcon:
    """创建指定名称的图标"""
    if color is None:
        color = QColor(80, 80, 80)
    
    # 特殊处理 OCR 图标，使用外部图片
    if name == "ocr":
        import os
        # 尝试从几个可能的位置加载图标
        paths = [
            r"c:\Users\admin\Desktop\ff\截图贴图工具\文本识别.png",
            os.path.join(os.path.dirname(__file__), "..", "..", "文本识别.png"),
            "文本识别.png"
        ]
        for p in paths:
            if os.path.exists(p):
                pixmap = QPixmap(p)
                if not pixmap.isNull():
                    return QIcon(pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    draw_func = ICON_DRAWERS.get(name)
    if draw_func:
        draw_func(painter, size, color)
    
    painter.end()
    return QIcon(pixmap)


def draw_rect(p: QPainter, size: int, color: QColor):
    """矩形工具 - 带对角调整手柄的矩形"""
    p.setPen(QPen(color, 1.2))
    p.setBrush(Qt.BrushStyle.NoBrush)
    
    m = size * 0.2
    w = size - m * 2
    h = size - m * 2
    
    # 主矩形
    p.drawRect(int(m), int(m), int(w), int(h))
    
    # 四角的小方块手柄
    handle_size = 3
    corners = [
        (m - 1, m - 1),  # 左上
        (m + w - 2, m - 1),  # 右上
        (m - 1, m + h - 2),  # 左下
        (m + w - 2, m + h - 2),  # 右下
    ]
    p.setBrush(color)
    for x, y in corners:
        p.drawRect(int(x), int(y), handle_size, handle_size)


def draw_pen(p: QPainter, size: int, color: QColor):
    """画笔工具 - 波浪曲线"""
    p.setPen(QPen(color, 1.5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    
    # 绘制波浪曲线
    path = QPainterPath()
    m = size * 0.15
    
    path.moveTo(m, size * 0.65)
    path.cubicTo(
        size * 0.3, size * 0.3,
        size * 0.5, size * 0.7,
        size * 0.7, size * 0.35
    )
    path.lineTo(size - m, size * 0.25)
    
    p.drawPath(path)
    
    # 箭头头部
    end_x, end_y = size - m, size * 0.25
    p.drawLine(QPointF(end_x, end_y), QPointF(end_x - 4, end_y + 2))
    p.drawLine(QPointF(end_x, end_y), QPointF(end_x - 3, end_y + 4))


def draw_arrow(p: QPainter, size: int, color: QColor):
    """箭头工具 - 铅笔/画笔形状"""
    p.setPen(QPen(color, 1.2))
    
    # 铅笔主体 - 斜着的
    m = size * 0.15
    
    # 笔身矩形（斜的）
    path = QPainterPath()
    path.moveTo(size * 0.25, size * 0.75)
    path.lineTo(size * 0.35, size * 0.85)
    path.lineTo(size * 0.85, size * 0.35)
    path.lineTo(size * 0.75, size * 0.25)
    path.closeSubpath()
    
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(path)
    
    # 笔尖
    p.drawLine(QPointF(size * 0.25, size * 0.75), QPointF(size * 0.15, size * 0.85))
    p.drawLine(QPointF(size * 0.35, size * 0.85), QPointF(size * 0.15, size * 0.85))
    
    # 橡皮头部分的分隔线
    p.drawLine(QPointF(size * 0.65, size * 0.25), QPointF(size * 0.75, size * 0.35))


def draw_eraser(p: QPainter, size: int, color: QColor):
    """橡皮擦 - 菱形/钻石形状"""
    p.setPen(QPen(color, 1.2))
    p.setBrush(Qt.BrushStyle.NoBrush)
    
    # 菱形
    cx, cy = size / 2, size / 2
    rx, ry = size * 0.35, size * 0.35
    
    points = QPolygonF([
        QPointF(cx, cy - ry),      # 上
        QPointF(cx + rx, cy),      # 右
        QPointF(cx, cy + ry),      # 下
        QPointF(cx - rx, cy),      # 左
    ])
    p.drawPolygon(points)


def draw_mosaic(p: QPainter, size: int, color: QColor):
    """马赛克 - 3x3网格"""
    m = size * 0.2
    block = (size - m * 2) / 3
    
    p.setPen(QPen(color, 1))
    
    for i in range(3):
        for j in range(3):
            x = m + i * block
            y = m + j * block
            # 交替填充
            if (i + j) % 2 == 0:
                p.setBrush(color)
            else:
                p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRect(int(x), int(y), int(block), int(block)))


def draw_text(p: QPainter, size: int, color: QColor):
    """文字工具 - 大写T"""
    p.setPen(QPen(color, 2))
    p.setBrush(Qt.BrushStyle.NoBrush)
    
    font = p.font()
    font.setPixelSize(int(size * 0.7))
    font.setBold(True)
    font.setFamily("Arial")
    p.setFont(font)
    
    p.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, "T")


def draw_blur(p: QPainter, size: int, color: QColor):
    """模糊工具 - 水滴形状"""
    p.setPen(QPen(color, 1.2))
    p.setBrush(Qt.BrushStyle.NoBrush)
    
    # 水滴形状
    path = QPainterPath()
    cx = size / 2
    
    # 从顶部尖端开始
    path.moveTo(cx, size * 0.15)
    # 右侧曲线
    path.cubicTo(
        cx + size * 0.3, size * 0.4,
        cx + size * 0.3, size * 0.7,
        cx, size * 0.85
    )
    # 左侧曲线
    path.cubicTo(
        cx - size * 0.3, size * 0.7,
        cx - size * 0.3, size * 0.4,
        cx, size * 0.15
    )
    
    p.drawPath(path)


def draw_undo(p: QPainter, size: int, color: QColor):
    """撤销 - 左弯箭头"""
    p.setPen(QPen(color, 1.5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    
    # 弧线
    path = QPainterPath()
    m = size * 0.2
    
    path.moveTo(size * 0.75, size * 0.65)
    path.arcTo(m, m, size - m * 2, size - m * 2, -45, 225)
    p.drawPath(path)
    
    # 箭头
    arrow_x, arrow_y = size * 0.25, size * 0.45
    p.setBrush(color)
    arrow = QPolygonF([
        QPointF(arrow_x - 4, arrow_y),
        QPointF(arrow_x + 2, arrow_y - 5),
        QPointF(arrow_x + 2, arrow_y + 5),
    ])
    p.drawPolygon(arrow)


def draw_cancel(p: QPainter, size: int, color: QColor):
    """取消 - X"""
    p.setPen(QPen(color, 1.8))
    m = size * 0.28
    p.drawLine(QPointF(m, m), QPointF(size - m, size - m))
    p.drawLine(QPointF(size - m, m), QPointF(m, size - m))


def draw_pin(p: QPainter, size: int, color: QColor):
    """固定 - 图钉形状"""
    p.setPen(QPen(color, 1.2))
    p.setBrush(Qt.BrushStyle.NoBrush)
    
    cx = size / 2
    
    # 图钉头部（斜的矩形）
    path = QPainterPath()
    path.moveTo(cx - 5, size * 0.2)
    path.lineTo(cx + 5, size * 0.2)
    path.lineTo(cx + 3, size * 0.45)
    path.lineTo(cx - 3, size * 0.45)
    path.closeSubpath()
    p.drawPath(path)
    
    # 针
    p.drawLine(QPointF(cx, size * 0.45), QPointF(cx, size * 0.8))
    
    # 斜线表示固定
    p.drawLine(QPointF(cx - 4, size * 0.35), QPointF(cx + 4, size * 0.35))


def draw_save(p: QPainter, size: int, color: QColor):
    """保存 - 软盘图标"""
    p.setPen(QPen(color, 1.2))
    p.setBrush(Qt.BrushStyle.NoBrush)
    
    m = size * 0.18
    w = size - m * 2
    h = size - m * 2
    
    # 外框
    p.drawRect(int(m), int(m), int(w), int(h))
    
    # 顶部标签槽
    label_w = w * 0.5
    label_x = m + (w - label_w) / 2
    p.drawRect(int(label_x), int(m), int(label_w), int(h * 0.25))
    
    # 底部存储区
    store_m = w * 0.15
    store_y = m + h * 0.55
    store_h = h * 0.35
    p.setBrush(QColor(200, 200, 200))
    p.drawRect(int(m + store_m), int(store_y), int(w - store_m * 2), int(store_h))


def draw_copy(p: QPainter, size: int, color: QColor):
    """复制 - 两个重叠的矩形"""
    p.setPen(QPen(color, 1.2))
    
    m = size * 0.15
    w = size * 0.5
    h = size * 0.55
    offset = size * 0.2
    
    # 后面的矩形
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(int(m + offset), int(m), int(w), int(h))
    
    # 前面的矩形（白色填充）
    p.setBrush(QColor(245, 245, 245))
    p.drawRect(int(m), int(m + offset), int(w), int(h))


def draw_ellipse(p: QPainter, size: int, color: QColor):
    """椭圆工具"""
    p.setPen(QPen(color, 1.2))
    p.setBrush(Qt.BrushStyle.NoBrush)
    m = size * 0.2
    p.drawEllipse(int(m), int(m + 2), int(size - m * 2), int(size - m * 2 - 4))


def draw_line(p: QPainter, size: int, color: QColor):
    """直线工具"""
    p.setPen(QPen(color, 1.5))
    m = size * 0.2
    p.drawLine(QPointF(m, size - m), QPointF(size - m, m))


def draw_move(p: QPainter, size: int, color: QColor):
    """移动工具 - 四向箭头"""
    p.setPen(QPen(color, 1.5))
    p.setBrush(color)
    
    cx, cy = size / 2, size / 2
    arm = size * 0.3
    arrow_size = 4
    
    # 四个方向的线
    p.drawLine(QPointF(cx, cy - arm), QPointF(cx, cy + arm))  # 垂直
    p.drawLine(QPointF(cx - arm, cy), QPointF(cx + arm, cy))  # 水平
    
    # 上箭头
    p.drawPolygon(QPolygonF([
        QPointF(cx, cy - arm - 2),
        QPointF(cx - arrow_size, cy - arm + arrow_size),
        QPointF(cx + arrow_size, cy - arm + arrow_size),
    ]))
    # 下箭头
    p.drawPolygon(QPolygonF([
        QPointF(cx, cy + arm + 2),
        QPointF(cx - arrow_size, cy + arm - arrow_size),
        QPointF(cx + arrow_size, cy + arm - arrow_size),
    ]))
    # 左箭头
    p.drawPolygon(QPolygonF([
        QPointF(cx - arm - 2, cy),
        QPointF(cx - arm + arrow_size, cy - arrow_size),
        QPointF(cx - arm + arrow_size, cy + arrow_size),
    ]))
    # 右箭头
    p.drawPolygon(QPolygonF([
        QPointF(cx + arm + 2, cy),
        QPointF(cx + arm - arrow_size, cy - arrow_size),
        QPointF(cx + arm - arrow_size, cy + arrow_size),
    ]))


def draw_edit(p: QPainter, size: int, color: QColor):
    """编辑工具 - 铅笔图标"""
    p.setPen(QPen(color, 1.2))
    p.setBrush(Qt.BrushStyle.NoBrush)
    
    # 铅笔主体（斜向）
    path = QPainterPath()
    path.moveTo(size * 0.2, size * 0.8)
    path.lineTo(size * 0.3, size * 0.9)
    path.lineTo(size * 0.85, size * 0.35)
    path.lineTo(size * 0.75, size * 0.25)
    path.closeSubpath()
    p.drawPath(path)
    
    # 笔尖
    p.drawLine(QPointF(size * 0.2, size * 0.8), QPointF(size * 0.12, size * 0.88))
    
    # 橡皮头分隔线
    p.drawLine(QPointF(size * 0.68, size * 0.28), QPointF(size * 0.78, size * 0.38))


def draw_ocr(p: QPainter, size: int, color: QColor):
    """OCR 工具 - 带文字的矩形和扫描线"""
    p.setPen(QPen(color, 1.2))
    p.setBrush(Qt.BrushStyle.NoBrush)

    m = size * 0.18
    w = size - m * 2
    h = size - m * 2

    p.drawRect(int(m), int(m), int(w), int(h))

    scan_y = m + h * 0.55
    p.drawLine(QPointF(m + 2, scan_y), QPointF(m + w - 2, scan_y))

    font = p.font()
    font.setPixelSize(int(size * 0.38))
    p.setFont(font)
    p.drawText(QRect(int(m), int(m + 1), int(w), int(h * 0.6)), Qt.AlignmentFlag.AlignCenter, "T")


# 图标绘制函数映射
ICON_DRAWERS = {
    'move': draw_move,
    'rect': draw_rect,
    'pen': draw_pen,
    'arrow': draw_arrow,
    'eraser': draw_eraser,
    'mosaic': draw_mosaic,
    'text': draw_text,
    'blur': draw_blur,
    'undo': draw_undo,
    'cancel': draw_cancel,
    'pin': draw_pin,
    'save': draw_save,
    'copy': draw_copy,
    'ellipse': draw_ellipse,
    'line': draw_line,
    'edit': draw_edit,
    'ocr': draw_ocr,
}


def get_toolbar_icons(size: int = 20) -> dict:
    """获取工具栏所有图标"""
    color = QColor(80, 80, 80)
    return {name: create_icon(name, size, color) for name in ICON_DRAWERS}
