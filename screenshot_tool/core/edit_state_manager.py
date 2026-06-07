"""
编辑状态管理器 - 记录所有截图的编辑历史和状态
支持：撤销、状态恢复、编辑历史记录
"""
from PySide6.QtGui import QPixmap
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import os


class EditState:
    """单个编辑状态"""
    
    def __init__(self, tab_id: str, pixmap: QPixmap, operation: str = ""):
        self.tab_id = tab_id
        self.pixmap = pixmap.copy()
        self.operation = operation
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "tab_id": self.tab_id,
            "operation": self.operation,
            "timestamp": self.timestamp.isoformat(),
            "pixmap_size": (self.pixmap.width(), self.pixmap.height())
        }


class EditHistory:
    """单个截图的编辑历史"""
    
    def __init__(self, tab_id: str, max_history: int = 50):
        self.tab_id = tab_id
        self.max_history = max_history
        self.states: List[EditState] = []
        self.current_index = -1
    
    def add_state(self, pixmap: QPixmap, operation: str = ""):
        """添加编辑状态"""
        # 移除当前位置之后的所有状态
        self.states = self.states[:self.current_index + 1]
        
        # 添加新状态
        state = EditState(self.tab_id, pixmap, operation)
        self.states.append(state)
        self.current_index = len(self.states) - 1
        
        # 限制历史记录数量
        if len(self.states) > self.max_history:
            self.states.pop(0)
            self.current_index -= 1
    
    def undo(self) -> Optional[EditState]:
        """撤销"""
        if self.current_index > 0:
            self.current_index -= 1
            return self.states[self.current_index]
        return None
    
    def get_current_state(self) -> Optional[EditState]:
        """获取当前状态"""
        if 0 <= self.current_index < len(self.states):
            return self.states[self.current_index]
        return None
    
    def can_undo(self) -> bool:
        """是否可以撤销"""
        return self.current_index > 0
    
    def get_history_info(self) -> Dict[str, Any]:
        """获取历史信息"""
        return {
            "tab_id": self.tab_id,
            "total_states": len(self.states),
            "current_index": self.current_index,
            "can_undo": self.can_undo(),
            "operations": [s.operation for s in self.states]
        }


class EditStateManager:
    """编辑状态管理器 - 管理所有截图的编辑历史"""
    
    def __init__(self, config_dir: str, max_history_per_tab: int = 50):
        self.config_dir = config_dir
        self.max_history_per_tab = max_history_per_tab
        self.histories: Dict[str, EditHistory] = {}
        self.state_dir = os.path.join(config_dir, "edit_states")
        
        # 创建状态目录
        os.makedirs(self.state_dir, exist_ok=True)
    
    def create_history(self, tab_id: str) -> EditHistory:
        """为新标签页创建历史记录"""
        if tab_id not in self.histories:
            self.histories[tab_id] = EditHistory(tab_id, self.max_history_per_tab)
        return self.histories[tab_id]
    
    def add_state(self, tab_id: str, pixmap: QPixmap, operation: str = ""):
        """添加编辑状态"""
        history = self.create_history(tab_id)
        history.add_state(pixmap, operation)
    
    def undo(self, tab_id: str) -> Optional[QPixmap]:
        """撤销"""
        if tab_id in self.histories:
            state = self.histories[tab_id].undo()
            if state:
                return state.pixmap
        return None
    
    def can_undo(self, tab_id: str) -> bool:
        """是否可以撤销"""
        if tab_id in self.histories:
            return self.histories[tab_id].can_undo()
        return False
    
    def get_history_info(self, tab_id: str) -> Optional[Dict[str, Any]]:
        """获取历史信息"""
        if tab_id in self.histories:
            return self.histories[tab_id].get_history_info()
        return None
    
    def clear_history(self, tab_id: str):
        """清空指定标签页的历史"""
        if tab_id in self.histories:
            del self.histories[tab_id]
    
    def clear_all_histories(self):
        """清空所有历史"""
        self.histories.clear()
    
    def save_state_snapshot(self, tab_id: str, pixmap: QPixmap, metadata: Dict[str, Any] = None):
        """保存状态快照到磁盘"""
        if tab_id not in self.histories:
            return False
        
        try:
            history = self.histories[tab_id]
            state = history.get_current_state()
            
            if not state:
                return False
            
            # 保存图像
            image_path = os.path.join(self.state_dir, f"{tab_id}_snapshot.png")
            if not pixmap.save(image_path):
                return False
            
            # 保存元数据
            meta_path = os.path.join(self.state_dir, f"{tab_id}_metadata.json")
            meta = {
                "tab_id": tab_id,
                "timestamp": datetime.now().isoformat(),
                "operation": state.operation,
                "pixmap_size": (pixmap.width(), pixmap.height()),
                "custom_metadata": metadata or {}
            }
            
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta, f, indent=2)
            
            return True
        except Exception as e:
            print(f"保存状态快照失败: {e}")
            return False
    
    def load_state_snapshot(self, tab_id: str) -> Optional[Tuple[QPixmap, Dict[str, Any]]]:
        """从磁盘加载状态快照"""
        try:
            image_path = os.path.join(self.state_dir, f"{tab_id}_snapshot.png")
            meta_path = os.path.join(self.state_dir, f"{tab_id}_metadata.json")
            
            if not os.path.exists(image_path) or not os.path.exists(meta_path):
                return None
            
            # 加载图像
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                return None
            
            # 加载元数据
            with open(meta_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            return (pixmap, metadata)
        except Exception as e:
            print(f"加载状态快照失败: {e}")
            return None
    
    def get_all_histories_info(self) -> Dict[str, Dict[str, Any]]:
        """获取所有历史信息"""
        return {
            tab_id: history.get_history_info()
            for tab_id, history in self.histories.items()
        }
    
    def cleanup_old_snapshots(self, days: int = 7):
        """清理旧的快照文件"""
        import time
        current_time = time.time()
        cutoff_time = current_time - (days * 24 * 60 * 60)
        
        for filename in os.listdir(self.state_dir):
            filepath = os.path.join(self.state_dir, filename)
            if os.path.isfile(filepath):
                if os.path.getmtime(filepath) < cutoff_time:
                    try:
                        os.remove(filepath)
                    except Exception as e:
                        print(f"删除文件失败 {filepath}: {e}")


class BatchEditOperation:
    """批量编辑操作"""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.affected_tabs: List[str] = []
        self.timestamp = datetime.now()
    
    def add_affected_tab(self, tab_id: str):
        """添加受影响的标签页"""
        if tab_id not in self.affected_tabs:
            self.affected_tabs.append(tab_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "operation_name": self.operation_name,
            "affected_tabs": self.affected_tabs,
            "timestamp": self.timestamp.isoformat(),
            "tab_count": len(self.affected_tabs)
        }


class BatchEditHistory:
    """批量编辑历史"""
    
    def __init__(self, max_operations: int = 100):
        self.max_operations = max_operations
        self.operations: List[BatchEditOperation] = []
    
    def record_operation(self, operation: BatchEditOperation):
        """记录批量操作"""
        self.operations.append(operation)
        
        # 限制历史记录数量
        if len(self.operations) > self.max_operations:
            self.operations.pop(0)
    
    def get_recent_operations(self, count: int = 10) -> List[Dict[str, Any]]:
        """获取最近的操作"""
        return [
            op.to_dict()
            for op in self.operations[-count:]
        ]
    
    def get_all_operations(self) -> List[Dict[str, Any]]:
        """获取所有操作"""
        return [op.to_dict() for op in self.operations]
    
    def clear(self):
        """清空历史"""
        self.operations.clear()


# 全局编辑状态管理器实例
_edit_state_manager = None


def get_edit_state_manager(config_dir: str = None) -> EditStateManager:
    """获取全局编辑状态管理器"""
    global _edit_state_manager
    if _edit_state_manager is None:
        if config_dir is None:
            config_dir = os.path.expanduser("~/.pyscreenshot")
        _edit_state_manager = EditStateManager(config_dir)
    return _edit_state_manager
