"""
配置管理模块 - 增强版
"""
import os
import json
from pathlib import Path
from datetime import datetime


class Config:
    """应用配置管理"""
    
    SOFT_NUMBER = "10013"
    
    DEFAULT_CONFIG = {
        # 保存设置
        "save_path": str(Path.home() / "Pictures" / "Screenshots"),
        "default_format": "png",
        "auto_save": False,
        "copy_to_clipboard": True,
        "show_notification": True,
        
        # 文件命名规则
        "naming_template": "${YYYYMMDD}_${MODE}_${SEQ}",
        "naming_prefix": "Screenshot",
        "naming_templates": [
            "${YYYYMMDD}_${MODE}_${SEQ}",
            "Screenshot_${HHMMSS}",
            "${PREFIX}_${YYYYMMDD}",
            "${PREFIX}_${YYYY}-${MM}-${DD}_${HH}-${MM}-${SS}"
        ],
        
        # 快捷键
        "hotkeys": {
            "fullscreen": "Ctrl+Shift+F",
            "region": "Ctrl+Shift+A",
            "window": "Ctrl+Shift+W",
            "color_picker": "Ctrl+Shift+C",
            "repeat_capture": "F8",
            "whiteboard": "Win+Shift+W",
            "smart_paste": "Ctrl+Shift+V"
        },
        
        # 截图设置
        "scroll_delay": 0.5,  # 滚动延迟（秒）
        "scroll_speed": "medium",  # slow/medium/fast
        
        # 编辑器设置
        "editor_fullscreen": True,  # 编辑器默认全屏
        "editor_remember_size": True,
        "editor_last_size": None,
        
        # 界面设置
        "theme": "auto",  # light/dark/auto
        "accent_color": "#0078D7",
        "icon_size": 24,  # 16/24/32
        "toolbar_collapsed": False,
        "language": "auto",
        
        # 重复截取
        "last_capture": None,  # 存储最后一次截图参数
        
        # 取色器
        "color_history": [],
        "color_format": "hex",  # hex/rgb/hsl/hsv
        
        # 量角器
        "protractor_lock_angle": 15,  # 角度锁定间隔
        
        # 白板
        "whiteboard_background": "white",  # white/black/grid/custom
        "whiteboard_custom_bg": None,
        
        # 新手引导
        "show_tutorial": True,
        "first_run": True,
        "tips_shown": []
    }
    
    # 序号计数器
    _sequence = 0
    
    def __init__(self):
        self.config_dir = Path.home() / ".pyscreenshot"
        self.config_file = self.config_dir / "config.json"
        self.config = self.load_config()
        
        # 确保截图保存目录存在
        os.makedirs(self.config["save_path"], exist_ok=True)
    
    def load_config(self) -> dict:
        """加载配置文件"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # 深度合并默认配置
                    config = self._deep_merge(self.DEFAULT_CONFIG.copy(), loaded)
                    return config
            except Exception:
                return self.DEFAULT_CONFIG.copy()
        return self.DEFAULT_CONFIG.copy()
    
    def _deep_merge(self, base: dict, override: dict) -> dict:
        """深度合并字典"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def save_config(self):
        """保存配置文件"""
        os.makedirs(self.config_dir, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)
    
    def get(self, key: str, default=None):
        """获取配置项"""
        return self.config.get(key, default)
    
    def set(self, key: str, value):
        """设置配置项"""
        self.config[key] = value
        self.save_config()
    
    def generate_filename(self, mode: str = "screenshot") -> str:
        """根据模板生成文件名"""
        template = self.config.get("naming_template", "${YYYYMMDD}_${MODE}_${SEQ}")
        prefix = self.config.get("naming_prefix", "Screenshot")
        fmt = self.config.get("default_format", "png")
        
        now = datetime.now()
        Config._sequence += 1
        
        # 替换变量
        replacements = {
            "${YYYY}": now.strftime("%Y"),
            "${MM}": now.strftime("%m"),
            "${DD}": now.strftime("%d"),
            "${HH}": now.strftime("%H"),
            "${YYYYMMDD}": now.strftime("%Y%m%d"),
            "${HHMMSS}": now.strftime("%H%M%S"),
            "${MODE}": mode,
            "${PREFIX}": prefix,
            "${SEQ}": f"{Config._sequence:03d}",
            "${YYYY}-${MM}-${DD}": now.strftime("%Y-%m-%d"),
            "${HH}-${MM}-${SS}": now.strftime("%H-%M-%S"),
        }
        
        filename = template
        for var, val in replacements.items():
            filename = filename.replace(var, val)
        
        return f"{filename}.{fmt}"
    
    def save_last_capture(self, mode: str, rect: tuple = None, size: tuple = None):
        """保存最后一次截图参数"""
        self.config["last_capture"] = {
            "mode": mode,
            "rect": rect,
            "size": size,
            "timestamp": datetime.now().isoformat()
        }
        self.save_config()
    
    def get_last_capture(self) -> dict:
        """获取最后一次截图参数"""
        return self.config.get("last_capture")
    
    def add_color_history(self, color: str):
        """添加颜色到历史"""
        history = self.config.get("color_history", [])
        if color in history:
            history.remove(color)
        history.insert(0, color)
        self.config["color_history"] = history[:10]  # 最多10个
        self.save_config()
    
    def get_color_history(self) -> list:
        """获取颜色历史"""
        return self.config.get("color_history", [])
