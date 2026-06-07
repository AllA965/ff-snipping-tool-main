# -*- coding: utf-8 -*-
"""
屏幕录制器
"""
import os
import threading
import time
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QFileDialog,
    QGroupBox, QFormLayout, QCheckBox, QFrame
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QGuiApplication
from ui.icons import set_window_icon

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


class RecorderThread(QThread):
    """录制线程"""
    
    frame_recorded = Signal(int)
    
    def __init__(self, output_path, fps, region=None, start_time=None):
        super().__init__()
        self.output_path = output_path
        self.fps = fps
        self.region = region
        self.running = False
        self.paused = False
        self.frame_count = 0
        self.start_time = start_time
        self.last_pause_time = 0
        self.total_paused_duration = 0
    
    def run(self):
        """运行录制"""
        if not HAS_CV2:
            return
        
        import mss
        
        self.running = True
        if self.start_time is None:
            self.start_time = time.time()
        
        # 获取屏幕区域
        with mss.mss() as sct:
            if self.region:
                monitor = {
                    "left": self.region[0],
                    "top": self.region[1],
                    "width": self.region[2],
                    "height": self.region[3]
                }
            else:
                monitor = sct.monitors[1]  # 主屏幕
            
            # 创建视频写入器
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(
                self.output_path, fourcc, self.fps,
                (monitor["width"], monitor["height"])
            )
            
            frame_interval = 1.0 / self.fps
            
            while self.running:
                if not self.paused:
                    loop_start = time.time()
                    
                    # 截取屏幕
                    img = sct.grab(monitor)
                    frame = np.array(img)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    
                    # 计算应该有的帧数
                    elapsed_time = time.time() - self.start_time - self.total_paused_duration
                    target_frame_count = int(elapsed_time * self.fps)
                    
                    # 补帧逻辑：如果当前帧数落后于目标帧数，则重复写入当前帧
                    # 最少写入一帧
                    num_frames_to_write = max(1, target_frame_count - self.frame_count)
                    
                    for _ in range(num_frames_to_write):
                        out.write(frame)
                        self.frame_count += 1
                    
                    self.frame_recorded.emit(self.frame_count)
                    
                    # 控制循环速度，避免占用过多CPU
                    elapsed = time.time() - loop_start
                    if elapsed < frame_interval:
                        time.sleep(frame_interval - elapsed)
                else:
                    time.sleep(0.1)
            
            out.release()
    
    def stop(self):
        """停止录制"""
        self.running = False
        self.wait()
    
    def pause(self):
        """暂停录制"""
        if not self.paused:
            self.paused = True
            self.last_pause_time = time.time()
    
    def resume(self):
        """恢复录制"""
        if self.paused:
            if self.last_pause_time > 0:
                self.total_paused_duration += time.time() - self.last_pause_time
            self.paused = False


class ScreenRecorderWindow(QWidget):
    """屏幕录制器窗口"""
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.recorder_thread = None
        self.recording = False
        self.paused = False
        self.start_time = None
        
        self.setup_ui()
        self.setup_timer()
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("屏幕录制器")
        set_window_icon(self)
        self.setFixedSize(400, 340)
        self.setStyleSheet("""
            QWidget { 
                background: #121212; 
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            }
            QLabel { 
                color: #e0e0e0; 
                font-size: 13px;
                border: none;
                background: transparent;
            }
            QPushButton {
                background: #2a2a2a;
                color: #ffffff;
                border: 1px solid #333333;
                border-radius: 10px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover { 
                background: #353535;
                border-color: #444444;
            }
            QPushButton#record_btn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0078d4, stop:1 #005a9e);
                border: none;
                font-weight: bold;
            }
            QPushButton#record_btn:hover { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1085da, stop:1 #0067b8);
            }
            QPushButton#record_btn[recording="true"] { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e81123, stop:1 #b40e1b); 
            }
            QPushButton#record_btn[recording="true"]:hover { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f13545, stop:1 #cf1122); 
            }
            QPushButton:disabled { 
                background: #1a1a1a; 
                color: #444444;
                border-color: #222222;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(25)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # 顶部标题栏
        header_layout = QHBoxLayout()
        title_label = QLabel("屏幕录制")
        title_label.setStyleSheet("font-size: 18px; font-weight: 600; color: #ffffff;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # 录制指示灯
        self.indicator = QLabel("●")
        self.indicator.setStyleSheet("color: transparent; font-size: 20px;")
        header_layout.addWidget(self.indicator)
        
        main_layout.addLayout(header_layout)
        
        # 居中计时器面板
        status_panel = QFrame()
        status_panel.setObjectName("status_panel")
        status_panel.setStyleSheet("""
            QFrame#status_panel {
                background: #1e1e1e;
                border-radius: 20px;
                border: 1px solid #2d2d2d;
            }
        """)
        status_layout = QVBoxLayout(status_panel)
        status_layout.setContentsMargins(20, 30, 20, 30)
        status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        time_title = QLabel("已录制时间")
        time_title.setStyleSheet("color: #777; font-size: 12px; font-weight: 500; letter-spacing: 1px;")
        time_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.time_label = QLabel("00:00:00")
        self.time_label.setStyleSheet("""
            font-size: 48px; 
            font-weight: 700; 
            color: #ffffff; 
            font-family: 'Consolas', 'Segoe UI Semibold';
            margin-top: 5px;
        """)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        status_layout.addWidget(time_title)
        status_layout.addWidget(self.time_label)
        main_layout.addWidget(status_panel)
        
        # 隐藏配置
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 60)
        self.fps_spin.setValue(30)
        self.fps_spin.hide()
        self.quality_combo = QComboBox()
        self.quality_combo.hide()
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.record_btn = QPushButton("开始录制")
        self.record_btn.setObjectName("record_btn")
        self.record_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.record_btn.setFixedHeight(45)
        self.record_btn.clicked.connect(self.toggle_recording)
        self.record_btn.setEnabled(HAS_CV2)
        
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pause_btn.setFixedHeight(45)
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setEnabled(False)
        
        btn_layout.addWidget(self.record_btn, 2)
        btn_layout.addWidget(self.pause_btn, 1)
        main_layout.addLayout(btn_layout)
        
        # 底部路径
        path_layout = QHBoxLayout()
        path_layout.setContentsMargins(5, 0, 5, 0)
        
        self.path_label = QLabel(self.config.get("save_path", ""))
        self.path_label.setStyleSheet("color: #555; font-size: 11px;")
        self.path_label.setToolTip(self.path_label.text())
        
        browse_btn = QPushButton("更改路径")
        browse_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #0078d4;
                font-size: 11px;
                font-weight: bold;
                padding: 0;
            }
            QPushButton:hover { color: #1085da; text-decoration: underline; }
        """)
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.clicked.connect(self.browse_path)
        
        path_layout.addWidget(self.path_label, 1)
        path_layout.addWidget(browse_btn)
        main_layout.addLayout(path_layout)
        
        # 呼吸灯定时器
        self.pulse_timer = QTimer()
        self.pulse_timer.timeout.connect(self.update_pulse)
        self.pulse_count = 0
    
    def setup_timer(self):
        """设置定时器"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.setInterval(100)  # 进一步提高更新频率到 100ms
    
    def toggle_recording(self):
        """切换录制状态"""
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        """开始录制"""
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = self.config.get("save_path", "")
        output_path = os.path.join(save_path, f"recording_{timestamp}.mp4")
        
        # 记录开始时间（统一使用一个时间点）
        current_time = time.time()
        self.start_time = current_time
        
        # 创建录制线程，并传入开始时间进行同步
        self.recorder_thread = RecorderThread(output_path, self.fps_spin.value(), start_time=current_time)
        self.recorder_thread.frame_recorded.connect(self.on_frame_recorded)
        self.recorder_thread.start()
        
        self.recording = True
        self.timer.start()
        self.update_time()  # 立即更新显示
        self.pulse_timer.start(50)  # 50ms 更新一次呼吸灯
        
        self.record_btn.setText("⏹ 停止录制")
        self.record_btn.setProperty("recording", True)
        self.record_btn.style().unpolish(self.record_btn)
        self.record_btn.style().polish(self.record_btn)
        self.pause_btn.setEnabled(True)
        self.fps_spin.setEnabled(False)
        self.quality_combo.setEnabled(False)
    
    def stop_recording(self):
        """停止录制"""
        if self.recorder_thread:
            self.recorder_thread.stop()
            self.recorder_thread = None
        
        self.recording = False
        self.paused = False
        self.timer.stop()
        self.pulse_timer.stop()
        self.indicator.setStyleSheet("color: transparent;")
        
        self.record_btn.setText("⏺ 开始录制")
        self.record_btn.setProperty("recording", False)
        self.record_btn.style().unpolish(self.record_btn)
        self.record_btn.style().polish(self.record_btn)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("⏸ 暂停")
        self.fps_spin.setEnabled(True)
        self.quality_combo.setEnabled(True)
    
    def toggle_pause(self):
        """切换暂停状态"""
        if not self.paused:
            self.recorder_thread.pause()
            self.paused = True
            self.pause_btn.setText("▶ 继续")
            self.indicator.setStyleSheet("color: #ffb74d;")  # 暂停时变为橙色
            self.pulse_timer.stop()
        else:
            self.recorder_thread.resume()
            self.paused = False
            self.pause_btn.setText("⏸ 暂停")
            self.pulse_timer.start(50)
    
    def update_pulse(self):
        """更新呼吸灯效果"""
        import math
        self.pulse_count += 0.1
        opacity = int((math.sin(self.pulse_count) + 1) * 127) + 50
        self.indicator.setStyleSheet(f"color: rgba(211, 47, 47, {opacity}); font-size: 18px;")

    def update_time(self):
        """更新时间显示"""
        if self.recording and not self.paused and self.recorder_thread:
            # 使用录制线程中的时间统计，确保 UI 显示与视频时长一致
            # 统一从 recorder_thread 获取时间基准
            now = time.time()
            elapsed_time = now - self.recorder_thread.start_time - self.recorder_thread.total_paused_duration
            
            # 确保时间不为负数
            elapsed = max(0, int(elapsed_time))
            hours = elapsed // 3600
            minutes = (elapsed % 3600) // 60
            seconds = elapsed % 60
            self.time_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
    
    def on_frame_recorded(self, count):
        """帧录制回调"""
        pass
    
    def browse_path(self):
        """浏览保存路径"""
        path = QFileDialog.getExistingDirectory(self, "选择保存目录")
        if path:
            self.path_label.setText(path)
            self.config.set("save_path", path)
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.recording:
            self.stop_recording()
        super().closeEvent(event)
