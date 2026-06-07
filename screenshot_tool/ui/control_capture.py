"""
窗口控件截图模块 - 增强版
功能：
- 实时追踪鼠标位置，智能识别窗口或控件
- 支持UI Automation精准识别按钮、输入框、下拉菜单等控件
- 红色边框高亮显示当前目标
- 显示控件坐标、尺寸和类型信息
- 支持滚轮/方向键手动切换父子控件
- 支持滚动截取（Ctrl+点击）
"""
import ctypes
from ctypes import wintypes, POINTER, byref
from PySide6.QtWidgets import QWidget, QApplication, QLabel
from PySide6.QtCore import Qt, Signal, QTimer, QRect, QPoint
from PySide6.QtGui import (
    QPixmap, QPainter, QColor, QPen, QFont, QCursor,
    QGuiApplication, QScreen, QBrush, QImage
)
import time

# UI Automation 支持标志
UIA_AVAILABLE = False
IUIAutomation = None
UIA_WRAPPER = None


def _init_uia():
    """延迟初始化 UI Automation"""
    global UIA_AVAILABLE, IUIAutomation, UIA_WRAPPER
    try:
        # 使用 comtypes 正确初始化
        import comtypes
        import comtypes.client
        
        # 生成类型库
        comtypes.client.GetModule("UIAutomationCore.dll")
        
        # 动态导入生成的模块
        from comtypes.gen import UIAutomationClient
        
        # 创建 UI Automation 对象
        uia = comtypes.client.CreateObject(UIAutomationClient.CUIAutomation)
        uia_interface = uia.QueryInterface(UIAutomationClient.IUIAutomation)
        
        IUIAutomation = uia_interface
        UIA_AVAILABLE = True
        UIA_WRAPPER = UIAutomationWrapper(uia_interface)
        
    except Exception as e:
        # 回退方案：使用纯 ctypes
        try:
            UIA_WRAPPER = UIAutomationWrapperCtypes()
            UIA_AVAILABLE = True
        except Exception:
            UIA_AVAILABLE = False
            IUIAutomation = None
            UIA_WRAPPER = None


class UIAutomationWrapperCtypes:
    """使用纯 ctypes 的 UI Automation 包装类"""
    
    # Windows Accessibility API
    OBJID_WINDOW = 0
    CHILDID_SELF = 0
    
    def __init__(self):
        self.oleacc = ctypes.windll.oleacc
        self.user32 = ctypes.windll.user32
    
    def get_element_at_point(self, x, y):
        """获取指定点的可访问对象"""
        try:
            # 使用 AccessibleObjectFromPoint
            import comtypes
            from ctypes import POINTER, byref
            
            # 定义 IAccessible 接口
            class IAccessible(comtypes.IUnknown):
                _iid_ = comtypes.GUID("{618736e0-3c3d-11cf-810c-00aa00389b71}")
            
            pAcc = POINTER(IAccessible)()
            varChild = ctypes.c_long()
            
            pt = wintypes.POINT(x, y)
            result = self.oleacc.AccessibleObjectFromPoint(
                pt, byref(pAcc), byref(varChild)
            )
            
            if result == 0 and pAcc:
                return {'acc': pAcc, 'child': varChild.value, 'x': x, 'y': y}
        except Exception:
            pass
        
        # 回退：使用 WindowFromPoint
        pt = wintypes.POINT(x, y)
        hwnd = self.user32.WindowFromPoint(pt)
        if hwnd:
            return {'hwnd': hwnd, 'x': x, 'y': y}
        return None
    
    def get_element_info(self, element):
        """获取元素信息"""
        if not element:
            return None
        
        try:
            if 'hwnd' in element:
                hwnd = element['hwnd']
                rect = wintypes.RECT()
                self.user32.GetWindowRect(hwnd, byref(rect))
                
                # 获取类名
                class_buffer = ctypes.create_unicode_buffer(256)
                self.user32.GetClassNameW(hwnd, class_buffer, 256)
                
                # 获取窗口文本
                text_len = self.user32.GetWindowTextLengthW(hwnd)
                text_buffer = ctypes.create_unicode_buffer(text_len + 1)
                self.user32.GetWindowTextW(hwnd, text_buffer, text_len + 1)
                
                return {
                    'name': text_buffer.value,
                    'control_type': 50032,  # Window
                    'class_name': class_buffer.value,
                    'rect': (rect.left, rect.top, rect.right, rect.bottom)
                }
        except Exception:
            pass
        return None
    
    def get_parent(self, element):
        """获取父元素"""
        if not element:
            return None
        try:
            if 'hwnd' in element:
                parent_hwnd = self.user32.GetParent(element['hwnd'])
                if parent_hwnd:
                    return {'hwnd': parent_hwnd}
        except Exception:
            pass
        return None
    
    def get_control_type_name(self, control_type):
        """获取控件类型名称"""
        type_names = {
            50000: '按钮', 50002: '复选框', 50003: '下拉框',
            50004: '编辑框', 50008: '列表', 50020: '文本',
            50032: '窗口', 50033: '窗格',
        }
        return type_names.get(control_type, '控件')


class UIAutomationWrapper:
    """UI Automation 包装类，用于精准识别控件"""
    
    def __init__(self, uia):
        self.uia = uia
        self._tree_walker = None
    
    def get_element_at_point(self, x, y):
        """获取指定点的UI元素"""
        try:
            from comtypes.gen.UIAutomationClient import tagPOINT
            pt = tagPOINT()
            pt.x = x
            pt.y = y
            element = self.uia.ElementFromPoint(pt)
            return element
        except Exception:
            return None
    
    def get_element_info(self, element):
        """获取元素信息"""
        if not element:
            return None
        try:
            info = {
                'name': element.CurrentName or '',
                'control_type': element.CurrentControlType,
                'class_name': element.CurrentClassName or '',
                'automation_id': element.CurrentAutomationId or '',
            }
            # 获取边界矩形
            rect = element.CurrentBoundingRectangle
            info['rect'] = (rect.left, rect.top, rect.right, rect.bottom)
            return info
        except Exception:
            return None
    
    def get_parent(self, element):
        """获取父元素"""
        if not element:
            return None
        try:
            # 使用 TreeWalker 获取父元素
            if self._tree_walker is None:
                self._tree_walker = self.uia.ControlViewWalker
            return self._tree_walker.GetParentElement(element)
        except Exception:
            return None
    
    def get_children(self, element):
        """获取子元素列表"""
        if not element:
            return []
        try:
            if self._tree_walker is None:
                self._tree_walker = self.uia.ControlViewWalker
            
            children = []
            child = self._tree_walker.GetFirstChildElement(element)
            while child:
                children.append(child)
                child = self._tree_walker.GetNextSiblingElement(child)
            return children
        except Exception:
            return []
    
    def get_control_type_name(self, control_type):
        """获取控件类型名称"""
        type_names = {
            50000: '按钮',
            50001: '日历',
            50002: '复选框',
            50003: '下拉框',
            50004: '编辑框',
            50005: '超链接',
            50006: '图像',
            50007: '列表项',
            50008: '列表',
            50009: '菜单',
            50010: '菜单栏',
            50011: '菜单项',
            50012: '进度条',
            50013: '单选按钮',
            50014: '滚动条',
            50015: '滑块',
            50016: '微调框',
            50017: '状态栏',
            50018: '标签页',
            50019: '标签项',
            50020: '文本',
            50021: '工具栏',
            50022: '工具提示',
            50023: '树形视图',
            50024: '树形项',
            50025: '自定义',
            50026: '组',
            50027: '缩略图',
            50028: '数据网格',
            50029: '数据项',
            50030: '文档',
            50031: '分隔条',
            50032: '窗口',
            50033: '窗格',
            50034: '表头',
            50035: '表头项',
            50036: '表格',
            50037: '标题栏',
            50038: '语义缩放',
        }
        return type_names.get(control_type, f'控件({control_type})')


# Windows API 常量
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080
IDC_CROSS = 32515
GWL_STYLE = -16
GW_CHILD = 5
GA_ROOT = 2
GA_ROOTOWNER = 3
CWP_SKIPINVISIBLE = 0x0001
CWP_SKIPDISABLED = 0x0002
CWP_SKIPTRANSPARENT = 0x0004


class ControlHighlightOverlay(QWidget):
    """控件高亮覆盖层 - 智能双向识别"""
    
    capture_completed = Signal(object)  # 支持 QPixmap 或 QImage (用于超大长图)
    capture_cancelled = Signal()
    
    def __init__(self, screen_capture):
        super().__init__()
        self.screen_capture = screen_capture
        self.user32 = ctypes.windll.user32
        
        # 当前高亮的控件信息
        self.current_hwnd = None
        self.current_rect = None
        self.current_screen_rect = None
        self.control_info = ""
        self.control_type = ""
        self.control_class = ""
        
        # 目标类型：'window' 或 'control'
        self.target_type = "control"
        
        # 控件层级缓存
        self.window_hwnd = None  # 顶层窗口句柄
        self.control_hwnd = None  # 当前控件句柄
        self.control_hierarchy = []  # 控件层级列表 [窗口, 子控件1, 子控件2, ...]
        self.hierarchy_index = 0  # 当前选中的层级索引
        
        # 上一次鼠标位置（用于检测移动方向）
        self.last_mouse_pos = None
        self.last_control_area = 0
        
        # UI Automation 支持
        self.uia = None
        self.uia_element = None
        self._uia_initialized = False
        
        # 鼠标追踪定时器（60fps 更流畅）
        self.track_timer = QTimer(self)
        self.track_timer.timeout.connect(self._track_control)
        
        # 防抖定时器
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self._apply_pending_update)
        self.pending_hwnd = None
        self.pending_hierarchy = []
        
        # 忽略自身窗口句柄
        self.self_hwnd = None
        
        # UIA 元素缓存
        self._uia_element = None
        self._uia_element_info = None
        
        # 鼠标样式覆盖标志
        self._cursor_overridden = False
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置全屏透明覆盖层"""
        screens = QApplication.screens()
        total_rect = QRect()
        for screen in screens:
            total_rect = total_rect.united(screen.geometry())
        
        self.setGeometry(total_rect)
        self.screen_offset = QPoint(total_rect.x(), total_rect.y())
        
        # 使用 Tool 标志，避免在任务栏显示，同时保持窗口能接收事件
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # 截取背景图像（用于显示高亮区域）
        self.background = None
        
        # 提示标签
        self.hint_label = QLabel(self)
        self.hint_label.setStyleSheet("""
            QLabel {
                background: rgba(0, 0, 0, 200);
                color: white;
                padding: 8px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
        """)
        self._update_hint_text()
        self.hint_label.move(10, 10)
        
        # 目标类型标签
        self.type_label = QLabel(self)
        self.type_label.setStyleSheet("""
            QLabel {
                background: rgba(255, 0, 0, 220);
                color: white;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 11px;
                font-weight: bold;
            }
        """)
        self.type_label.setText("控件")
        self.type_label.adjustSize()
        self.type_label.move(10, 50)
    
    def _update_hint_text(self):
        """更新提示文本"""
        hints = [
            "移动鼠标选择目标",
            "点击截取",
            "Ctrl+点击滚动截取",
            "滚轮↑↓切换层级",
            "ESC取消"
        ]
        self.hint_label.setText(" | ".join(hints))
        self.hint_label.adjustSize()
    
    def showEvent(self, event):
        """显示时开始追踪"""
        super().showEvent(event)
        
        # 设置全局十字架鼠标，防止闪烁
        if not self._cursor_overridden:
            QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)
            self._cursor_overridden = True
        
        # 重新设置几何形状（showFullScreen 可能会覆盖）
        screens = QApplication.screens()
        total_rect = QRect()
        for screen in screens:
            total_rect = total_rect.united(screen.geometry())
        self.setGeometry(total_rect)
        self.screen_offset = QPoint(total_rect.x(), total_rect.y())
        
        # 截取背景图像（在获取窗口句柄之前）
        self.background = self.screen_capture.capture_all_screens()
        
        # 重置状态
        self.control_hierarchy = []
        self.hierarchy_index = 0
        self.current_hwnd = None
        self.current_rect = None
        self.current_screen_rect = None
        
        if not self._uia_initialized:
            self._uia_initialized = True
            _init_uia()
            if UIA_AVAILABLE:
                self.uia = IUIAutomation
        
        # 延迟获取窗口句柄和启动追踪，确保窗口完全显示
        QTimer.singleShot(150, self._init_and_start_tracking)
    
    def _init_and_start_tracking(self):
        """初始化并启动追踪"""
        # 获取自身窗口句柄（多种方式）
        self.self_hwnd = None
        
        # 方式1：通过 winId
        try:
            self.self_hwnd = int(self.winId())
        except Exception:
            pass
        
        # 方式2：通过前台窗口
        try:
            foreground = self.user32.GetForegroundWindow()
            if foreground:
                rect = wintypes.RECT()
                self.user32.GetWindowRect(foreground, ctypes.byref(rect))
                my_geo = self.geometry()
                if (abs(rect.left - my_geo.x()) < 10 and 
                    abs(rect.top - my_geo.y()) < 10 and
                    abs((rect.right - rect.left) - my_geo.width()) < 10 and
                    abs((rect.bottom - rect.top) - my_geo.height()) < 10):
                    self.self_hwnd = foreground
        except Exception:
            pass
        
        # 启动追踪
        self._start_tracking()
    
    def _start_tracking(self):
        """启动追踪"""
        # 30fps 追踪（更稳定）
        self.track_timer.start(33)
    
    def hideEvent(self, event):
        """隐藏时停止追踪"""
        self.track_timer.stop()
        self.debounce_timer.stop()
        
        # 恢复鼠标样式
        if self._cursor_overridden:
            QApplication.restoreOverrideCursor()
            self._cursor_overridden = False
            
        super().hideEvent(event)
    
    def closeEvent(self, event):
        """关闭时清理"""
        self.track_timer.stop()
        self.debounce_timer.stop()
        
        # 恢复鼠标样式
        if self._cursor_overridden:
            QApplication.restoreOverrideCursor()
            self._cursor_overridden = False
            
        super().closeEvent(event)

    
    def _track_control(self):
        """追踪鼠标下的控件 - 智能双向识别"""
        # 获取鼠标位置
        point = wintypes.POINT()
        self.user32.GetCursorPos(ctypes.byref(point))
        mouse_pos = (point.x, point.y)
        
        # 如果鼠标没有移动，跳过开销较大的识别
        if self.last_mouse_pos == mouse_pos:
            return
        
        # 使用枚举窗口方法获取鼠标下的窗口（排除自身）
        hwnd = self._get_window_under_point_enum(point.x, point.y)
        
        if not hwnd or hwnd == 0:
            # 如果没有找到窗口，清空当前状态
            if self.current_hwnd:
                self.current_hwnd = None
                self.current_rect = None
                self.control_info = "未找到窗口"
                self.update()
            return
        
        # 获取顶层窗口
        root_hwnd = self.user32.GetAncestor(hwnd, GA_ROOT)
        if not root_hwnd:
            root_hwnd = hwnd
        
        # 构建控件层级（从顶层窗口到最深层控件）
        hierarchy = self._build_control_hierarchy(root_hwnd, point.x, point.y)
        
        if not hierarchy:
            # 如果没有层级，至少使用窗口
            hierarchy = [root_hwnd]
        
        # 检查是否需要更新
        if hierarchy != self.control_hierarchy or root_hwnd != self.window_hwnd:
            self.pending_hwnd = root_hwnd
            self.pending_hierarchy = hierarchy
            
            # 使用防抖，避免快速移动时频繁更新
            if not self.debounce_timer.isActive():
                self.debounce_timer.start(10)  # 10ms 防抖
        
        # 检测鼠标移动方向，智能切换目标
        if self.last_mouse_pos and hierarchy:
            self._smart_switch_target(mouse_pos, hierarchy)
        
        self.last_mouse_pos = mouse_pos
    
    def _get_window_under_point_enum(self, x, y):
        """获取指定点下面的窗口（排除自身）"""
        # 获取所有可能的自身窗口句柄
        self_hwnds = set()
        if self.self_hwnd:
            self_hwnds.add(self.self_hwnd)
        
        # 也添加通过 winId 获取的句柄
        try:
            win_id = int(self.winId())
            if win_id:
                self_hwnds.add(win_id)
        except Exception:
            pass
        
        # 使用 WindowFromPoint 获取初始窗口
        point = wintypes.POINT(x, y)
        hwnd = self.user32.WindowFromPoint(point)
        
        if not hwnd:
            return None
        
        # 获取顶层窗口
        root_hwnd = self.user32.GetAncestor(hwnd, GA_ROOT)
        if not root_hwnd:
            root_hwnd = hwnd
        
        # 检查是否是自身窗口
        if root_hwnd in self_hwnds or hwnd in self_hwnds:
            # 遍历 Z 顺序找到下面的窗口
            GW_HWNDNEXT = 2
            top_hwnd = self.user32.GetTopWindow(None)
            
            while top_hwnd:
                # 跳过自身窗口
                if top_hwnd in self_hwnds:
                    top_hwnd = self.user32.GetWindow(top_hwnd, GW_HWNDNEXT)
                    continue
                
                # 检查窗口是否可见
                if not self.user32.IsWindowVisible(top_hwnd):
                    top_hwnd = self.user32.GetWindow(top_hwnd, GW_HWNDNEXT)
                    continue
                
                # 获取窗口矩形
                rect = wintypes.RECT()
                if self.user32.GetWindowRect(top_hwnd, ctypes.byref(rect)):
                    if rect.left <= x < rect.right and rect.top <= y < rect.bottom:
                        return top_hwnd
                
                top_hwnd = self.user32.GetWindow(top_hwnd, GW_HWNDNEXT)
            
            return None
        
        return root_hwnd
    
    def _build_control_hierarchy(self, root_hwnd, x, y) -> list:
        """构建从顶层窗口到最深层控件的层级列表 - 优先使用 UI Automation"""
        # 清空 UIA 缓存
        self._uia_elements = []
        self._uia_element_info = None
        self._uia_element = None
        self._current_uia_item = None
        
        # 优先使用 UI Automation 构建完整的控件层级
        if UIA_AVAILABLE and UIA_WRAPPER:
            uia_hierarchy = self._build_uia_hierarchy(x, y)
            if uia_hierarchy and len(uia_hierarchy) > 0:
                # UIA 层级有效，使用它
                self._uia_elements = uia_hierarchy
                # 返回窗口句柄 + UIA 元素索引作为层级
                # 索引 0 = 窗口, 索引 1+ = UIA 元素
                return [root_hwnd] + list(range(len(uia_hierarchy)))
        
        # 回退到传统 Win32 API
        hierarchy = [root_hwnd]
        current = root_hwnd
        while True:
            client_point = wintypes.POINT(x, y)
            self.user32.ScreenToClient(current, ctypes.byref(client_point))
            
            child = self.user32.ChildWindowFromPointEx(
                current, client_point,
                CWP_SKIPINVISIBLE | CWP_SKIPDISABLED
            )
            
            if child and child != current and self.user32.IsWindowVisible(child):
                hierarchy.append(child)
                current = child
            else:
                break
        
        return hierarchy
    
    def _build_uia_hierarchy(self, x, y) -> list:
        """使用 UI Automation 构建控件层级（从最深层到窗口）"""
        if not UIA_AVAILABLE or not UIA_WRAPPER:
            return []
        
        try:
            # 临时隐藏覆盖层以获取正确的元素
            # 使用 SetWindowLong 设置 WS_EX_TRANSPARENT 样式
            GWL_EXSTYLE = -20
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_LAYERED = 0x00080000
            
            old_style = 0
            if self.self_hwnd:
                # 保存原始样式
                old_style = self.user32.GetWindowLongW(self.self_hwnd, GWL_EXSTYLE)
                # 添加透明样式
                self.user32.SetWindowLongW(
                    self.self_hwnd, GWL_EXSTYLE, 
                    old_style | WS_EX_TRANSPARENT | WS_EX_LAYERED
                )
                # 强制设置十字架光标，防止在透明期间闪烁
                cross_cursor = self.user32.LoadCursorW(None, IDC_CROSS)
                if cross_cursor:
                    self.user32.SetCursor(cross_cursor)
            
            # 获取鼠标位置的元素
            element = UIA_WRAPPER.get_element_at_point(x, y)
            
            # 恢复原始样式
            if self.self_hwnd and old_style:
                self.user32.SetWindowLongW(self.self_hwnd, GWL_EXSTYLE, old_style)
            
            if not element:
                return []
            
            # 构建层级：从当前元素向上遍历
            hierarchy = []
            current = element
            visited_elements = set()
            max_depth = 30
            skip_count = 0
            
            while current and len(hierarchy) < max_depth and skip_count < 10:
                try:
                    # 检查是否已访问此元素（通过对象 ID）
                    elem_id = id(current)
                    if elem_id in visited_elements:
                        break
                    visited_elements.add(elem_id)
                    
                    info = UIA_WRAPPER.get_element_info(current)
                    if not info:
                        parent = UIA_WRAPPER.get_parent(current)
                        if parent:
                            current = parent
                            skip_count += 1
                            continue
                        break
                    
                    rect = info.get('rect')
                    
                    # 如果矩形无效，跳过但继续向上
                    if not rect or rect[2] <= rect[0] or rect[3] <= rect[1]:
                        parent = UIA_WRAPPER.get_parent(current)
                        if parent:
                            current = parent
                            skip_count += 1
                            continue
                        break
                    
                    # 有效元素，添加到层级
                    hierarchy.append({
                        'element': current,
                        'info': info,
                        'rect': rect
                    })
                    skip_count = 0
                    
                    # 窗口类型停止
                    if info.get('control_type', 0) == 50032:
                        break
                    
                    parent = UIA_WRAPPER.get_parent(current)
                    if parent:
                        current = parent
                    else:
                        break
                except Exception:
                    break
            
            # 反转：从窗口到最深层
            hierarchy.reverse()
            
            # 过滤：去除重复矩形
            if not hierarchy:
                return []
            
            filtered = []
            seen_rects = set()
            
            for item in hierarchy:
                rect = item['rect']
                rect_key = tuple(rect)
                
                # 跳过重复矩形
                if rect_key in seen_rects:
                    continue
                seen_rects.add(rect_key)
                
                # 跳过太小的元素
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                if w < 5 or h < 5:
                    continue
                
                filtered.append(item)
            
            return filtered
            
        except Exception:
            return []
            
        except Exception:
            return []
    
    def _smart_switch_target(self, mouse_pos, hierarchy):
        """智能切换目标（窗口/控件）- 自动选择最深层控件"""
        if len(hierarchy) <= 1:
            # 只有窗口，没有子控件
            if self.hierarchy_index != 0:
                self.hierarchy_index = 0
                self._update_from_hierarchy()
            return
        
        # 如果有 UIA 元素，自动切换到最深层控件
        if hasattr(self, '_uia_elements') and self._uia_elements and len(self._uia_elements) > 0:
            # 默认选择最深层的控件（最后一个 UIA 元素）
            if self.hierarchy_index == 0:
                # 从窗口切换到最深层控件
                self.hierarchy_index = len(hierarchy) - 1
                self._update_from_hierarchy()
            return
        
        # 回退到传统方式
        current_hwnd = hierarchy[min(self.hierarchy_index, len(hierarchy) - 1)]
        if isinstance(current_hwnd, int) and current_hwnd > 0:
            rect = wintypes.RECT()
            if self.user32.GetWindowRect(current_hwnd, ctypes.byref(rect)):
                current_area = (rect.right - rect.left) * (rect.bottom - rect.top)
                
                if self.hierarchy_index == 0 and len(hierarchy) > 1:
                    deepest_hwnd = hierarchy[-1]
                    if isinstance(deepest_hwnd, int) and deepest_hwnd > 0:
                        deep_rect = wintypes.RECT()
                        if self.user32.GetWindowRect(deepest_hwnd, ctypes.byref(deep_rect)):
                            deep_area = (deep_rect.right - deep_rect.left) * (deep_rect.bottom - deep_rect.top)
                            if deep_area < current_area * 0.5:
                                self.hierarchy_index = len(hierarchy) - 1
                                self._update_from_hierarchy()
                
                self.last_control_area = current_area
    
    def _apply_pending_update(self):
        """应用待处理的更新"""
        if self.pending_hwnd is None:
            return
        
        self.window_hwnd = self.pending_hwnd
        self.control_hierarchy = self.pending_hierarchy
        
        # 如果有 UIA 元素，默认选择最深层控件
        if hasattr(self, '_uia_elements') and self._uia_elements and len(self._uia_elements) > 0:
            # 自动选择最深层控件（最后一个）
            self.hierarchy_index = len(self.control_hierarchy) - 1
        elif not self.control_hierarchy:
            self.hierarchy_index = 0
        else:
            # 保持当前层级索引在有效范围内
            if self.hierarchy_index >= len(self.control_hierarchy):
                self.hierarchy_index = len(self.control_hierarchy) - 1
            if self.hierarchy_index < 0:
                self.hierarchy_index = 0
        
        self._update_from_hierarchy()
        
        self.pending_hwnd = None
        self.pending_hierarchy = []
    
    def _update_from_hierarchy(self):
        """根据当前层级更新高亮"""
        if not self.control_hierarchy:
            self.current_hwnd = None
            self.current_rect = None
            self.current_screen_rect = None
            self.control_info = "未识别到控件"
            self.target_type = "control"
            self._current_uia_item = None
            self._update_type_label()
            self.update()
            return
        
        # 确保索引有效
        if self.hierarchy_index < 0:
            self.hierarchy_index = 0
        if self.hierarchy_index >= len(self.control_hierarchy):
            self.hierarchy_index = len(self.control_hierarchy) - 1
        
        # 第一层始终是窗口句柄
        self.current_hwnd = self.control_hierarchy[0]
        
        # 判断目标类型和获取 UIA 元素
        if self.hierarchy_index == 0:
            self.target_type = "window"
            self._current_uia_item = None
        else:
            self.target_type = "control"
            # 其他层是 UIA 元素索引
            if hasattr(self, '_uia_elements') and self._uia_elements:
                uia_index = self.hierarchy_index - 1
                if 0 <= uia_index < len(self._uia_elements):
                    self._current_uia_item = self._uia_elements[uia_index]
                else:
                    self._current_uia_item = None
                    # 回退到传统方式
                    if self.hierarchy_index < len(self.control_hierarchy):
                        item = self.control_hierarchy[self.hierarchy_index]
                        if isinstance(item, int) and item > 0:
                            self.current_hwnd = item
            else:
                # 回退到传统方式
                self._current_uia_item = None
                if self.hierarchy_index < len(self.control_hierarchy):
                    item = self.control_hierarchy[self.hierarchy_index]
                    if isinstance(item, int) and item > 0:
                        self.current_hwnd = item
        
        self._update_highlight()
        self._update_type_label()
    
    def _update_type_label(self):
        """更新目标类型标签"""
        total = len(self.control_hierarchy) if self.control_hierarchy else 0
        
        # 获取控件类型名称
        type_name = ""
        if hasattr(self, 'control_type') and self.control_type:
            type_name = self.control_type
        
        if total == 0:
            self.type_label.setText("未识别")
            self.type_label.setStyleSheet("""
                QLabel {
                    background: rgba(128, 128, 128, 220);
                    color: white;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 11px;
                    font-weight: bold;
                }
            """)
        elif self.target_type == "window":
            self.type_label.setText(f"🪟 窗口 (层级 1/{total})")
            self.type_label.setStyleSheet("""
                QLabel {
                    background: rgba(33, 150, 243, 220);
                    color: white;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 11px;
                    font-weight: bold;
                }
            """)
        else:
            level = self.hierarchy_index + 1
            # 显示控件类型
            if type_name:
                self.type_label.setText(f"🎯 {type_name} (层级 {level}/{total})")
            else:
                self.type_label.setText(f"🎯 控件 (层级 {level}/{total})")
            self.type_label.setStyleSheet("""
                QLabel {
                    background: rgba(255, 0, 0, 220);
                    color: white;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 11px;
                    font-weight: bold;
                }
            """)
        self.type_label.adjustSize()
    
    def _update_highlight(self):
        """更新高亮显示"""
        rect_left = rect_top = rect_right = rect_bottom = 0
        width = height = 0
        control_type = ""
        control_name = ""
        class_name = ""
        
        # 检查是否使用 UIA 元素
        if hasattr(self, '_current_uia_item') and self._current_uia_item:
            # 使用 UIA 元素信息
            uia_item = self._current_uia_item
            uia_rect = uia_item.get('rect')
            uia_info = uia_item.get('info', {})
            
            if uia_rect and uia_rect[2] > uia_rect[0] and uia_rect[3] > uia_rect[1]:
                rect_left, rect_top, rect_right, rect_bottom = uia_rect
                width = rect_right - rect_left
                height = rect_bottom - rect_top
                
                control_type = UIA_WRAPPER.get_control_type_name(uia_info.get('control_type', 0))
                control_name = uia_info.get('name', '')
                class_name = uia_info.get('class_name', '')
        
        # 如果没有 UIA 信息，使用窗口句柄
        if width <= 0 or height <= 0:
            # 确保 current_hwnd 是有效的窗口句柄
            hwnd = self.current_hwnd
            if not hwnd or not isinstance(hwnd, int) or hwnd <= 0:
                self.current_rect = None
                self.current_screen_rect = None
                self.control_info = "未识别到控件"
                self.update()
                return
            
            # 检查窗口是否有效
            if not self.user32.IsWindow(hwnd):
                self.current_rect = None
                self.current_screen_rect = None
                self.control_info = "窗口无效"
                self.update()
                return
            
            rect = wintypes.RECT()
            if not self.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                self.current_rect = None
                self.current_screen_rect = None
                self.control_info = "无法获取位置"
                self.update()
                return
            
            rect_left, rect_top, rect_right, rect_bottom = rect.left, rect.top, rect.right, rect.bottom
            width = rect_right - rect_left
            height = rect_bottom - rect_top
            
            class_name = self._get_class_name(hwnd)
            control_type = self._identify_control_type(class_name)
            control_name = self._get_window_text(hwnd)
        
        if width <= 0 or height <= 0:
            self.current_rect = None
            self.current_screen_rect = None
            self.control_info = "尺寸无效"
            self.update()
            return
        
        # 转换为本地坐标
        self.current_rect = QRect(
            rect_left - self.screen_offset.x(),
            rect_top - self.screen_offset.y(),
            width,
            height
        )
        self.current_screen_rect = (rect_left, rect_top, rect_right, rect_bottom)
        
        self.control_info = f"X:{rect_left} Y:{rect_top} W:{width} H:{height}"
        self.control_type = control_type
        self.control_class = class_name
        
        # 更新提示
        if self.target_type == "window":
            title = control_name[:30] + "..." if len(control_name) > 30 else control_name
            if title:
                self.hint_label.setText(f"窗口: {title} | 滚轮↓进入子控件 | 点击截取 | Ctrl+点击滚动截取")
            else:
                self.hint_label.setText("窗口 | 滚轮↓进入子控件 | 点击截取 | Ctrl+点击滚动截取")
        else:
            type_info = f"{control_type}" if control_type else "控件"
            if control_name:
                type_info += f": {control_name[:20]}"
            self.hint_label.setText(f"{type_info} | 滚轮↑↓切换层级 | 点击截取 | Ctrl+点击滚动截取")
        self.hint_label.adjustSize()
        
        self.update()

    
    def _get_class_name(self, hwnd) -> str:
        """获取控件类名"""
        buffer = ctypes.create_unicode_buffer(256)
        self.user32.GetClassNameW(hwnd, buffer, 256)
        return buffer.value
    
    def _get_window_text(self, hwnd) -> str:
        """获取控件文本"""
        length = self.user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buffer = ctypes.create_unicode_buffer(length + 1)
            self.user32.GetWindowTextW(hwnd, buffer, length + 1)
            return buffer.value
        return ""
    
    def _identify_control_type(self, class_name: str) -> str:
        """识别控件类型"""
        if not class_name:
            return ""
        
        class_lower = class_name.lower()
        
        type_map = {
            'button': '按钮',
            'edit': '输入框',
            'richedit': '富文本框',
            'combobox': '下拉框',
            'listbox': '列表框',
            'listview': '列表视图',
            'syslistview': '列表视图',
            'treeview': '树形视图',
            'systreeview': '树形视图',
            'datagrid': '数据表格',
            'scrollbar': '滚动条',
            'static': '静态文本',
            'tabcontrol': '标签页',
            'systabcontrol': '标签页',
            'toolbar': '工具栏',
            'statusbar': '状态栏',
            'msctls_statusbar': '状态栏',
            'menu': '菜单',
            'tooltips': '提示框',
            'progress': '进度条',
            'msctls_progress': '进度条',
            'trackbar': '滑块',
            'msctls_trackbar': '滑块',
            'updown': '微调按钮',
            'msctls_updown': '微调按钮',
            'header': '表头',
            'sysheader': '表头',
            'rebar': '工具条',
            'rebarwindow': '工具条',
            'shelldll_defview': '文件视图',
            'directuihwnd': 'DirectUI',
            'chrome_widgetwin': '浏览器',
            'mozillawindowclass': '浏览器',
        }
        
        for key, value in type_map.items():
            if key in class_lower:
                return value
        
        # 返回简化的类名
        if len(class_name) > 15:
            return class_name[:12] + "..."
        return class_name
    
    def paintEvent(self, event):
        """绘制高亮框和信息"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 先绘制背景截图
        if self.background:
            painter.drawPixmap(0, 0, self.background)
        
        # 绘制半透明遮罩
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        
        if self.current_rect and self.current_rect.isValid():
            # 在高亮区域绘制原始背景（不带遮罩）
            if self.background:
                painter.drawPixmap(self.current_rect, self.background, self.current_rect)
            
            # 根据目标类型选择边框颜色
            if self.target_type == "window":
                border_color = QColor(33, 150, 243)  # 蓝色表示窗口
            else:
                border_color = QColor(255, 0, 0)  # 红色表示控件
            
            # 绘制高亮边框（3像素宽）
            pen = QPen(border_color, 3)
            painter.setPen(pen)
            painter.drawRect(self.current_rect.adjusted(1, 1, -1, -1))
            
            # 绘制信息标签
            info_text = self.control_info
            font = QFont("Microsoft YaHei", 9)
            painter.setFont(font)
            
            fm = painter.fontMetrics()
            text_width = fm.horizontalAdvance(info_text) + 16
            text_height = fm.height() + 8
            
            # 标签位置
            label_x = self.current_rect.left()
            if self.current_rect.top() > text_height + 5:
                label_y = self.current_rect.top() - text_height - 2
            else:
                label_y = self.current_rect.bottom() + 2
            
            # 确保标签不超出屏幕
            if label_x + text_width > self.width():
                label_x = self.width() - text_width - 5
            if label_x < 0:
                label_x = 5
            
            label_rect = QRect(label_x, label_y, text_width, text_height)
            painter.fillRect(label_rect, border_color)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, info_text)
    
    def mousePressEvent(self, event):
        """鼠标点击截取"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Ctrl+点击 = 滚动截取
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self._capture_with_scroll()
            else:
                self._capture_current()
        elif event.button() == Qt.MouseButton.RightButton:
            self._cancel()
    

    
    def wheelEvent(self, event):
        """滚轮切换层级"""
        event.accept()  # 接受事件
        
        if not self.control_hierarchy:
            return
        
        delta = event.angleDelta().y()
        
        if delta > 0:
            # 向上滚动：切换到父级（更大的区域）
            if self.hierarchy_index > 0:
                self.hierarchy_index -= 1
                self._update_from_hierarchy()
        else:
            # 向下滚动：切换到子级（更小的区域）
            if self.hierarchy_index < len(self.control_hierarchy) - 1:
                self.hierarchy_index += 1
                self._update_from_hierarchy()
    
    def keyPressEvent(self, event):
        """键盘事件"""
        key = event.key()
        
        if key == Qt.Key.Key_Escape:
            self._cancel()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self._capture_current()
        elif key == Qt.Key.Key_Up:
            if self.hierarchy_index > 0:
                self.hierarchy_index -= 1
                self._update_from_hierarchy()
        elif key == Qt.Key.Key_Down:
            if self.control_hierarchy and self.hierarchy_index < len(self.control_hierarchy) - 1:
                self.hierarchy_index += 1
                self._update_from_hierarchy()
        elif key == Qt.Key.Key_Home:
            self.hierarchy_index = 0
            self._update_from_hierarchy()
        elif key == Qt.Key.Key_End:
            if self.control_hierarchy:
                self.hierarchy_index = len(self.control_hierarchy) - 1
                self._update_from_hierarchy()
    
    def _capture_current(self):
        """截取当前高亮的目标"""
        if not self.current_screen_rect:
            return
        
        x, y, right, bottom = self.current_screen_rect
        width = right - x
        height = bottom - y
        
        if width <= 0 or height <= 0:
            return
        
        # 停止所有定时器
        self.track_timer.stop()
        self.debounce_timer.stop()
        
        # 保存截图参数
        self._capture_params = (x, y, width, height)
        
        # 隐藏覆盖层
        self.hide()
        
        # 延迟截图，确保窗口完全隐藏
        QTimer.singleShot(100, self._do_capture_delayed)
    
    def _do_capture_delayed(self):
        """延迟执行截图"""
        if hasattr(self, '_capture_params'):
            x, y, width, height = self._capture_params
            pixmap = self.screen_capture.capture_region(x, y, width, height)
            
            if pixmap and not pixmap.isNull():
                self.capture_completed.emit(pixmap)
            
            self.close()
    
    def _cancel(self):
        """取消截图"""
        self.track_timer.stop()
        self.debounce_timer.stop()
        self.capture_cancelled.emit()
        self.close()
    
    def _capture_with_scroll(self):
        """滚动截取控件内容"""
        if not self.current_hwnd or not self.current_screen_rect:
            return
        
        # 停止追踪
        self.track_timer.stop()
        self.debounce_timer.stop()
        
        # 保存参数
        self._scroll_hwnd = self.current_hwnd
        self._scroll_rect = self.current_screen_rect
        
        # 隐藏覆盖层
        self.hide()
        
        # 延迟执行滚动截取
        QTimer.singleShot(200, self._do_scroll_capture)
    
    def _do_scroll_capture(self):
        """执行滚动截取"""
        if not hasattr(self, '_scroll_hwnd') or not self._scroll_hwnd:
            self.close()
            return
        
        hwnd = self._scroll_hwnd
        x, y, right, bottom = self._scroll_rect
        width = right - x
        height = bottom - y
        
        if width <= 0 or height <= 0:
            self.close()
            return
        
        # 获取滚动信息
        scroll_info = self._get_scroll_info(hwnd)
        
        if not scroll_info or scroll_info['max_scroll'] <= 0:
            # 没有滚动条，直接截取
            pixmap = self.screen_capture.capture_region(x, y, width, height)
            if pixmap and not pixmap.isNull():
                self.capture_completed.emit(pixmap)
            self.close()
            return
        
        # 执行滚动截取
        self._perform_scroll_capture(hwnd, x, y, width, height, scroll_info)
    
    def _get_scroll_info(self, hwnd):
        """获取控件的滚动信息"""
        try:
            # 定义 SCROLLINFO 结构
            class SCROLLINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.UINT),
                    ("fMask", wintypes.UINT),
                    ("nMin", ctypes.c_int),
                    ("nMax", ctypes.c_int),
                    ("nPage", wintypes.UINT),
                    ("nPos", ctypes.c_int),
                    ("nTrackPos", ctypes.c_int),
                ]
            
            SIF_ALL = 0x17
            SB_VERT = 1
            
            si = SCROLLINFO()
            si.cbSize = ctypes.sizeof(SCROLLINFO)
            si.fMask = SIF_ALL
            
            if self.user32.GetScrollInfo(hwnd, SB_VERT, ctypes.byref(si)):
                max_scroll = si.nMax - si.nPage + 1 if si.nPage > 0 else si.nMax
                return {
                    'min': si.nMin,
                    'max': si.nMax,
                    'page': si.nPage,
                    'pos': si.nPos,
                    'max_scroll': max_scroll
                }
        except Exception:
            pass
        
        return None
    
    def _perform_scroll_capture(self, hwnd, x, y, width, height, scroll_info):
        """执行滚动截取并拼接"""
        try:
            # 滚动到顶部
            self._scroll_to_position(hwnd, 0)
            time.sleep(0.1)
            
            # 计算需要截取的次数
            page_height = scroll_info['page'] if scroll_info['page'] > 0 else height
            total_height = scroll_info['max'] + page_height
            
            # 限制最大高度 (20万像素，满足绝大多数长网页需求)
            max_total_height = 200000
            if total_height > max_total_height:
                total_height = max_total_height
            
            # 创建结果图像
            result_image = QImage(width, total_height, QImage.Format.Format_ARGB32)
            result_image.fill(QColor(255, 255, 255))
            
            painter = QPainter(result_image)
            current_y = 0
            current_scroll = 0
            overlap = 20  # 重叠像素，用于拼接
            
            while current_y < total_height:
                # 截取当前可见区域
                pixmap = self.screen_capture.capture_region(x, y, width, height)
                
                if pixmap and not pixmap.isNull():
                    # 计算实际绘制高度
                    draw_height = min(height, total_height - current_y)
                    
                    # 绘制到结果图像
                    if current_y == 0:
                        painter.drawPixmap(0, current_y, pixmap)
                        current_y += height - overlap
                    else:
                        # 跳过重叠部分
                        source_rect = QRect(0, overlap, width, draw_height)
                        painter.drawPixmap(0, current_y, pixmap, source_rect)
                        current_y += height - overlap
                
                # 滚动
                current_scroll += page_height - overlap
                if current_scroll >= scroll_info['max_scroll']:
                    break
                
                self._scroll_to_position(hwnd, current_scroll)
                time.sleep(0.05)
            
            painter.end()
            
            # 滚动回顶部
            self._scroll_to_position(hwnd, 0)
            
            # 直接发送 QImage，避免在大图时 QPixmap.fromImage 导致的 GPU 限制
            if not result_image.isNull():
                self.capture_completed.emit(result_image)
            
        except Exception as e:
            # 出错时截取当前可见区域
            pixmap = self.screen_capture.capture_region(x, y, width, height)
            if pixmap and not pixmap.isNull():
                self.capture_completed.emit(pixmap)
        
        self.close()
    
    def _scroll_to_position(self, hwnd, pos):
        """滚动到指定位置"""
        try:
            SB_VERT = 1
            SB_THUMBPOSITION = 4
            WM_VSCROLL = 0x0115
            
            # 设置滚动位置
            self.user32.SetScrollPos(hwnd, SB_VERT, pos, True)
            
            # 发送滚动消息
            wparam = (pos << 16) | SB_THUMBPOSITION
            self.user32.SendMessageW(hwnd, WM_VSCROLL, wparam, 0)
            
            # 也尝试发送 WM_VSCROLL 结束消息
            SB_ENDSCROLL = 8
            self.user32.SendMessageW(hwnd, WM_VSCROLL, SB_ENDSCROLL, 0)
        except Exception:
            pass


class ControlCaptureWindow(ControlHighlightOverlay):
    """控件截图窗口 - 兼容旧接口"""
    
    def __init__(self, screen_capture, config=None):
        super().__init__(screen_capture)
        self.config = config


class AdvancedControlCapture(QWidget):
    """高级控件捕获"""
    
    capture_completed = Signal(object)
    capture_cancelled = Signal()
    
    def __init__(self, screen_capture, config=None):
        super().__init__()
        self.screen_capture = screen_capture
        self.config = config
        
        self.simple_capture = ControlHighlightOverlay(screen_capture)
        self.simple_capture.capture_completed.connect(self.capture_completed.emit)
        self.simple_capture.capture_cancelled.connect(self.capture_cancelled.emit)
    
    def show(self):
        """显示控件捕获界面"""
        self.simple_capture.showFullScreen()
        self.simple_capture.raise_()
        self.simple_capture.activateWindow()
        self.simple_capture.setFocus()


# 保留兼容
class WindowSelectDialog:
    pass
