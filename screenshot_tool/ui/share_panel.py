"""
分享面板UI模块
参考PicPick风格的分享界面
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QDialog, QLineEdit,
    QSpinBox, QComboBox, QCheckBox, QProgressBar,
    QListWidget, QListWidgetItem, QStackedWidget, QGroupBox,
    QFormLayout, QTabWidget, QTextEdit
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from ui.modern_dialog import ModernMessageBox
from PySide6.QtGui import QPixmap, QColor, QPainter, QIcon, QFont

from core.share_manager import get_share_manager, ShareType
from core.credential_manager import get_credential_manager
from core.ftp_manager import FTPServerConfig, FTPProtocol
from core.social_share import SocialShareManager
from core.office_export import OfficeExporter


class ShareItemButton(QPushButton):
    """分享项按钮"""
    
    def __init__(self, icon_color: str, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.icon_color = icon_color
        self.title = title
        self.subtitle = subtitle
        self.setFixedHeight(50 if subtitle else 40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_style()

    def _setup_style(self):
        self.setStyleSheet("""
            QPushButton {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                text-align: left;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background: #f0f7ff;
                border-color: #0078D7;
            }
            QPushButton:pressed {
                background: #e0efff;
            }
        """)
    
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制图标背景
        icon_size = 28
        icon_x = 10
        icon_y = (self.height() - icon_size) // 2
        
        painter.setBrush(QColor(self.icon_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(icon_x, icon_y, icon_size, icon_size, 6, 6)
        
        # 绘制标题
        painter.setPen(QColor(51, 51, 51))
        font = painter.font()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        
        text_x = 48
        if self.subtitle:
            painter.drawText(text_x, 20, self.title)
            font.setBold(False)
            font.setPointSize(8)
            painter.setFont(font)
            painter.setPen(QColor(128, 128, 128))
            painter.drawText(text_x, 35, self.subtitle)
        else:
            painter.drawText(text_x, (self.height() + 8) // 2, self.title)


class ShareCategoryHeader(QLabel):
    """分享类别标题"""
    
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: bold;
                color: #2B579A;
                padding: 8px 0;
                border-bottom: 2px solid #2B579A;
                margin-bottom: 8px;
            }
        """)


class FTPServerDialog(QDialog):
    """FTP服务器配置对话框"""
    
    def __init__(self, parent=None, server_data: dict = None):
        super().__init__(parent)
        self.server_data = server_data
        self.setWindowTitle("FTP服务器配置" if not server_data else "编辑FTP服务器")
        self.setFixedSize(400, 350)
        self._setup_ui()
        
        if server_data:
            self._load_data(server_data)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # 表单
        form = QFormLayout()
        form.setSpacing(10)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如: 我的服务器")
        form.addRow("名称:", self.name_edit)
        
        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("例如: ftp.example.com")
        form.addRow("主机:", self.host_edit)
        
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(21)
        form.addRow("端口:", self.port_spin)
        
        self.username_edit = QLineEdit()
        form.addRow("用户名:", self.username_edit)
        
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("密码:", self.password_edit)
        
        self.path_edit = QLineEdit()
        self.path_edit.setText("/")
        self.path_edit.setPlaceholderText("远程目录路径")
        form.addRow("路径:", self.path_edit)
        
        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["FTP", "FTPS (SSL/TLS)"])
        form.addRow("协议:", self.protocol_combo)
        
        layout.addLayout(form)
        
        # 测试连接按钮
        test_btn = QPushButton("测试连接")
        test_btn.clicked.connect(self._test_connection)
        layout.addWidget(test_btn)
        
        layout.addStretch()
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("secondary", True)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
        
        self.setStyleSheet("""
            QDialog { background: #f5f5f5; }
            QLineEdit, QSpinBox, QComboBox {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 6px;
                background: white;
            }
            QPushButton {
                background: #0078D7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover { background: #005A9E; }
            QPushButton[secondary="true"] {
                background: #e0e0e0;
                color: #333;
            }
        """)

    def _load_data(self, data: dict):
        self.name_edit.setText(data.get('name', ''))
        self.host_edit.setText(data.get('host', ''))
        self.port_spin.setValue(data.get('port', 21))
        self.username_edit.setText(data.get('username', ''))
        self.password_edit.setText(data.get('password', ''))
        self.path_edit.setText(data.get('path', '/'))
    
    def _test_connection(self):
        from core.ftp_manager import get_ftp_manager, FTPServerConfig
        
        config = FTPServerConfig(
            name=self.name_edit.text(),
            host=self.host_edit.text(),
            port=self.port_spin.value(),
            username=self.username_edit.text(),
            password=self.password_edit.text(),
            protocol=FTPProtocol.FTPS if self.protocol_combo.currentIndex() == 1 else FTPProtocol.FTP
        )
        
        success, message = get_ftp_manager().test_connection(config)
        
        if success:
            ModernMessageBox.information(self, "成功", "连接测试成功！")
        else:
            ModernMessageBox.warning(self, "失败", f"连接失败: {message}")
    
    def _save(self):
        if not self.name_edit.text() or not self.host_edit.text():
            ModernMessageBox.warning(self, "错误", "请填写名称和主机地址")
            return
        
        self.accept()
    
    def get_data(self) -> dict:
        return {
            'name': self.name_edit.text(),
            'host': self.host_edit.text(),
            'port': self.port_spin.value(),
            'username': self.username_edit.text(),
            'password': self.password_edit.text(),
            'path': self.path_edit.text()
        }


class CloudAccountDialog(QDialog):
    """云存储账号管理对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("云存储账号管理")
        self.setFixedSize(400, 300)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # 标题
        title = QLabel("百度网盘")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #2B579A;")
        layout.addWidget(title)
        
        # 状态显示
        self.baidu_status = QLabel("未授权")
        self.baidu_status.setStyleSheet("""
            QLabel {
                padding: 12px;
                background: #fff3cd;
                border: 1px solid #ffc107;
                border-radius: 4px;
                color: #856404;
            }
        """)
        layout.addWidget(self.baidu_status)
        
        # 说明文字
        info_label = QLabel("授权后可将截图直接上传到百度网盘，方便跨设备访问和分享。")
        info_label.setStyleSheet("color: #666; font-size: 11px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 授权按钮
        baidu_auth_btn = QPushButton("🔐 授权百度网盘")
        baidu_auth_btn.clicked.connect(self._auth_baidu)
        baidu_auth_btn.setStyleSheet("""
            QPushButton {
                background: #06A7FF;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 12px 24px;
                font-size: 12px;
            }
            QPushButton:hover { background: #0590E0; }
        """)
        layout.addWidget(baidu_auth_btn)
        
        layout.addStretch()
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setProperty("secondary", True)
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #e0e0e0;
                color: #333;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover { background: #d0d0d0; }
        """)
        layout.addWidget(close_btn)
        
        self.setStyleSheet("QDialog { background: #f5f5f5; }")
    
    def _auth_baidu(self):
        try:
            from core.cloud_storage import get_cloud_manager, CloudProvider
            provider = get_cloud_manager().get_provider(CloudProvider.BAIDU)
            if provider:
                provider.auth_completed.connect(self._on_auth_completed)
                provider.start_oauth()
            else:
                ModernMessageBox.warning(self, "提示", "百度网盘功能暂不可用")
        except Exception as e:
            ModernMessageBox.warning(self, "错误", f"授权失败: {str(e)}")
    
    def _on_auth_completed(self, success: bool, message: str):
        if success:
            self.baidu_status.setText("✓ 已授权")
            self.baidu_status.setStyleSheet("""
                QLabel {
                    padding: 12px;
                    background: #d4edda;
                    border: 1px solid #28a745;
                    border-radius: 4px;
                    color: #155724;
                }
            """)
            ModernMessageBox.success(self, "成功", message)
        else:
            ModernMessageBox.warning(self, "失败", message)


class ShareProgressDialog(QDialog):
    """分享进度对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("分享进度")
        self.setFixedSize(350, 150)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.status_label = QLabel("准备中...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self.cancel_btn)
        
        self.setStyleSheet("""
            QDialog { background: #f5f5f5; }
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: #0078D7;
                border-radius: 3px;
            }
            QPushButton {
                background: #e0e0e0;
                color: #333;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
        """)
    
    def update_progress(self, progress: int, message: str = None):
        self.progress_bar.setValue(progress)
        if message:
            self.status_label.setText(message)
    
    def set_completed(self, success: bool, message: str):
        self.progress_bar.setValue(100 if success else 0)
        self.status_label.setText(message)
        self.cancel_btn.setText("关闭")


class SharePanel(QWidget):
    """分享面板 - 主界面"""
    
    share_requested = Signal(str)  # 分享类型
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.share_manager = get_share_manager()
        self.credential_manager = get_credential_manager()
        self.current_pixmap = None
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 标题区域（包含预览）
        header = QFrame()
        header.setStyleSheet("background: #2B579A; padding: 16px;")
        header_layout = QHBoxLayout(header)
        
        # 左侧标题
        title_section = QVBoxLayout()
        title = QLabel("分享")
        title.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
        title_section.addWidget(title)
        
        self.preview_info = QLabel("选择分享方式")
        self.preview_info.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 11px;")
        title_section.addWidget(self.preview_info)
        header_layout.addLayout(title_section)
        
        header_layout.addStretch()
        
        # 右侧预览缩略图
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(80, 60)
        self.preview_label.setStyleSheet("""
            QLabel {
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.3);
                border-radius: 4px;
            }
        """)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.preview_label)
        
        layout.addWidget(header)
        
        # 内容区域
        content = QFrame()
        content.setStyleSheet("background: #f8f9fa;")
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(16, 12, 16, 12)
        content_layout.setSpacing(20)
        
        # 左侧 - 分享选项
        left_panel = self._create_share_options()
        content_layout.addWidget(left_panel, 1)
        
        # 右侧 - 发送选项
        right_panel = self._create_send_options()
        content_layout.addWidget(right_panel, 1)
        
        layout.addWidget(content, 1)
    
    def _create_share_options(self) -> QWidget:
        """创建分享选项面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # ========== 社交分享 ==========
        social_header = ShareCategoryHeader("社交分享")
        layout.addWidget(social_header)
        
        # 检测已安装的应用
        apps = SocialShareManager.detect_installed_apps()
        
        # 微信
        wechat_btn = ShareItemButton("#07C160", "微信", 
            "已安装 - 分享到微信" if apps.get('wechat') else "未检测到微信客户端")
        wechat_btn.setEnabled(apps.get('wechat', False))
        wechat_btn.clicked.connect(lambda: self._on_share_clicked(ShareType.WECHAT))
        layout.addWidget(wechat_btn)
        
        # QQ（放在微信下方）
        qq_btn = ShareItemButton("#12B7F5", "QQ", 
            "已安装 - 分享到QQ" if apps.get('qq') else "未检测到QQ客户端")
        qq_btn.setEnabled(apps.get('qq', False))
        qq_btn.clicked.connect(lambda: self._on_share_clicked(ShareType.QQ))
        layout.addWidget(qq_btn)
        
        # 钉钉
        dingtalk_btn = ShareItemButton("#0089FF", "钉钉", 
            "已安装 - 分享到钉钉" if apps.get('dingtalk') else "未检测到钉钉客户端")
        dingtalk_btn.setEnabled(apps.get('dingtalk', False))
        dingtalk_btn.clicked.connect(lambda: self._on_share_clicked(ShareType.DINGTALK))
        layout.addWidget(dingtalk_btn)
        
        # 企业微信
        wecom_btn = ShareItemButton("#2BAD13", "企业微信", 
            "已安装 - 分享到企业微信" if apps.get('wecom') else "未检测到企业微信客户端")
        wecom_btn.setEnabled(apps.get('wecom', False))
        wecom_btn.clicked.connect(lambda: self._on_share_clicked(ShareType.WECOM))
        layout.addWidget(wecom_btn)
        
        layout.addSpacing(8)
        
        # ========== 云存储 ==========
        cloud_header = ShareCategoryHeader("云存储")
        layout.addWidget(cloud_header)
        
        # 百度网盘
        baidu_btn = ShareItemButton("#06A7FF", "百度网盘", "上传并分享图像到百度网盘")
        baidu_btn.clicked.connect(lambda: self._on_share_clicked(ShareType.BAIDU_PAN))
        layout.addWidget(baidu_btn)
        
        layout.addSpacing(8)
        
        # ========== 邮件 ==========
        email_header = ShareCategoryHeader("邮件")
        layout.addWidget(email_header)
        
        email_btn = ShareItemButton("#EA4335", "电子邮件", "添加图像的副本到电子邮件")
        email_btn.clicked.connect(lambda: self._on_share_clicked(ShareType.EMAIL))
        layout.addWidget(email_btn)
        
        layout.addSpacing(8)
        
        # ========== Office应用 ==========
        office_header = ShareCategoryHeader("Office 应用")
        layout.addWidget(office_header)
        
        word_btn = ShareItemButton("#2B579A", "Microsoft Word", "插入图像的副本到 Word")
        word_btn.clicked.connect(lambda: self._on_share_clicked(ShareType.OFFICE_WORD))
        layout.addWidget(word_btn)
        
        excel_btn = ShareItemButton("#217346", "Microsoft Excel", "插入图像的副本到 Excel")
        excel_btn.clicked.connect(lambda: self._on_share_clicked(ShareType.OFFICE_EXCEL))
        layout.addWidget(excel_btn)
        
        ppt_btn = ShareItemButton("#D24726", "Microsoft PowerPoint", "插入图像的副本到 PowerPoint")
        ppt_btn.clicked.connect(lambda: self._on_share_clicked(ShareType.OFFICE_POWERPOINT))
        layout.addWidget(ppt_btn)
        
        paint_btn = ShareItemButton("#0078D7", "Microsoft 画图", "发送图像的副本到 Paint")
        paint_btn.clicked.connect(lambda: self._on_share_clicked(ShareType.PAINT))
        layout.addWidget(paint_btn)
        
        layout.addStretch()
        return panel

    def _create_send_options(self) -> QWidget:
        """创建发送选项面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # ========== 发送到外部程序 ==========
        header = ShareCategoryHeader("发送到外部程序")
        layout.addWidget(header)
        
        # 外部程序按钮
        ext_btn = ShareItemButton("#5C6BC0", "外部程序", "发送图像到 Photoshop、GIMP 等外部程序")
        ext_btn.clicked.connect(self._show_external_programs)
        layout.addWidget(ext_btn)
        
        # FTP服务器按钮
        ftp_btn = ShareItemButton("#26A69A", "FTP", "直接发送图像到 FTP 服务器")
        ftp_btn.clicked.connect(self._show_ftp_options)
        layout.addWidget(ftp_btn)
        
        layout.addSpacing(8)
        
        # ========== 快捷操作 ==========
        quick_header = ShareCategoryHeader("快捷操作")
        layout.addWidget(quick_header)
        
        # 复制到剪贴板
        clipboard_btn = ShareItemButton("#607D8B", "复制到剪贴板", "Ctrl+C 快速复制")
        clipboard_btn.clicked.connect(lambda: self._on_share_clicked(ShareType.CLIPBOARD))
        layout.addWidget(clipboard_btn)
        
        layout.addSpacing(8)
        
        # ========== 应用检测状态 ==========
        status_header = ShareCategoryHeader("应用检测状态")
        layout.addWidget(status_header)
        
        apps = SocialShareManager.detect_installed_apps()
        
        # 使用紧凑的网格布局显示状态
        status_frame = QFrame()
        status_frame.setStyleSheet("""
            QFrame {
                background: #f5f5f5;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        status_grid = QGridLayout(status_frame)
        status_grid.setContentsMargins(8, 6, 8, 6)
        status_grid.setSpacing(4)
        
        app_names = [
            ('wechat', '微信'), ('qq', 'QQ'), 
            ('dingtalk', '钉钉'), ('wecom', '企业微信'),
            ('outlook', 'Outlook')
        ]
        
        for i, (key, name) in enumerate(app_names):
            status = "✓" if apps.get(key) else "✗"
            color = "#28a745" if apps.get(key) else "#dc3545"
            label = QLabel(f"<span style='color:{color}'>{status}</span> {name}")
            label.setStyleSheet("font-size: 11px; background: transparent;")
            status_grid.addWidget(label, i // 2, i % 2)
        
        layout.addWidget(status_frame)
        
        # 刷新检测按钮
        refresh_btn = QPushButton("🔄 重新检测")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #f0f0f0;
                color: #333;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover { 
                background: #e5f3ff;
                border-color: #0078D7;
            }
        """)
        refresh_btn.clicked.connect(self._refresh_app_detection)
        layout.addWidget(refresh_btn)
        
        layout.addStretch()
        return panel
    
    def _refresh_app_detection(self):
        """刷新应用检测"""
        # 重新创建面板
        ModernMessageBox.information(self, "提示", "请重新打开分享面板以刷新检测结果")
    
    def _connect_signals(self):
        """连接信号"""
        self.share_manager.task_started.connect(self._on_task_started)
        self.share_manager.task_progress.connect(self._on_task_progress)
        self.share_manager.task_completed.connect(self._on_task_completed)
    
    def set_pixmap(self, pixmap: QPixmap):
        """设置要分享的图像"""
        self.current_pixmap = pixmap
        
        # 更新预览
        if pixmap and not pixmap.isNull():
            # 创建缩略图
            thumbnail = pixmap.scaled(
                76, 56, 
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.preview_label.setPixmap(thumbnail)
            
            # 更新信息
            w, h = pixmap.width(), pixmap.height()
            self.preview_info.setText(f"图像尺寸: {w} × {h} 像素")
        else:
            self.preview_label.clear()
            self.preview_info.setText("没有可分享的图像")
    
    def _on_share_clicked(self, share_type: ShareType):
        """分享按钮点击"""
        if not self.current_pixmap:
            ModernMessageBox.warning(self, "提示", "请先截取或打开一张图像")
            return
        
        # 显示进度对话框
        self.progress_dialog = ShareProgressDialog(self)
        
        # 执行分享
        if share_type == ShareType.OFFICE_WORD:
            self.share_manager.export_to_word(self.current_pixmap)
        elif share_type == ShareType.OFFICE_EXCEL:
            self.share_manager.export_to_excel(self.current_pixmap)
        elif share_type == ShareType.OFFICE_POWERPOINT:
            self.share_manager.export_to_powerpoint(self.current_pixmap)
        elif share_type == ShareType.PAINT:
            self.share_manager.send_to_paint(self.current_pixmap)
        elif share_type == ShareType.EMAIL:
            self.share_manager.share_via_email(self.current_pixmap)
        elif share_type == ShareType.WECHAT:
            self.share_manager.share_to_wechat(self.current_pixmap)
        elif share_type == ShareType.QQ:
            self.share_manager.share_to_qq(self.current_pixmap)
        elif share_type == ShareType.DINGTALK:
            self.share_manager.share_to_dingtalk(self.current_pixmap)
        elif share_type == ShareType.WECOM:
            self.share_manager.share_to_wecom(self.current_pixmap)
        elif share_type == ShareType.ONEDRIVE:
            self.share_manager.upload_to_onedrive(self.current_pixmap)
        elif share_type == ShareType.BAIDU_PAN:
            self.share_manager.upload_to_baidu(self.current_pixmap)
        elif share_type == ShareType.CLIPBOARD:
            self.share_manager.copy_to_clipboard(self.current_pixmap)
        else:
            ModernMessageBox.information(self, "提示", f"功能开发中: {share_type.value}")
            return
        
        self.progress_dialog.show()

    def _on_task_started(self, task_id: str):
        """任务开始"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.update_progress(0, "正在处理...")
    
    def _on_task_progress(self, task_id: str, progress: int):
        """任务进度更新"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.update_progress(progress)
    
    def _on_task_completed(self, task_id: str, success: bool, message: str):
        """任务完成"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.set_completed(success, message)
            
            # 3秒后自动关闭
            if success:
                QTimer.singleShot(2000, self.progress_dialog.accept)
    
    def _show_external_programs(self):
        """显示外部程序选择"""
        menu_dialog = QDialog(self)
        menu_dialog.setWindowTitle("选择外部程序")
        menu_dialog.setFixedSize(300, 250)
        
        layout = QVBoxLayout(menu_dialog)
        
        # Photoshop
        ps_btn = ShareItemButton("#31A8FF", "Adobe Photoshop", "发送到Photoshop")
        ps_btn.clicked.connect(lambda: self._send_to_external("photoshop", menu_dialog))
        layout.addWidget(ps_btn)
        
        # GIMP
        gimp_btn = ShareItemButton("#5C5543", "GIMP", "发送到GIMP")
        gimp_btn.clicked.connect(lambda: self._send_to_external("gimp", menu_dialog))
        layout.addWidget(gimp_btn)
        
        # 画图
        paint_btn = ShareItemButton("#0078D7", "Microsoft 画图", "发送到画图")
        paint_btn.clicked.connect(lambda: self._send_to_external("paint", menu_dialog))
        layout.addWidget(paint_btn)
        
        layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(menu_dialog.accept)
        layout.addWidget(close_btn)
        
        menu_dialog.setStyleSheet("""
            QDialog { background: #f5f5f5; }
            QPushButton {
                background: #e0e0e0;
                color: #333;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        
        menu_dialog.exec()
    
    def _send_to_external(self, program: str, dialog: QDialog):
        """发送到外部程序"""
        dialog.accept()
        
        if not self.current_pixmap:
            ModernMessageBox.warning(self, "提示", "请先截取或打开一张图像")
            return
        
        if program == "photoshop":
            self.share_manager.send_to_photoshop(self.current_pixmap)
        elif program == "gimp":
            self.share_manager.send_to_gimp(self.current_pixmap)
        elif program == "paint":
            self.share_manager.send_to_paint(self.current_pixmap)
    
    def _show_ftp_options(self):
        """显示FTP选项"""
        ftp_dialog = QDialog(self)
        ftp_dialog.setWindowTitle("FTP服务器")
        ftp_dialog.setFixedSize(400, 350)
        
        layout = QVBoxLayout(ftp_dialog)
        
        # 服务器列表
        list_label = QLabel("已配置的服务器:")
        layout.addWidget(list_label)
        
        self.ftp_list = QListWidget()
        self._refresh_ftp_list()
        layout.addWidget(self.ftp_list)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(lambda: self._add_ftp_server(ftp_dialog))
        btn_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("编辑")
        edit_btn.clicked.connect(lambda: self._edit_ftp_server(ftp_dialog))
        btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("删除")
        delete_btn.clicked.connect(self._delete_ftp_server)
        btn_layout.addWidget(delete_btn)
        
        layout.addLayout(btn_layout)
        
        # 上传按钮
        upload_btn = QPushButton("上传到选中的服务器")
        upload_btn.clicked.connect(lambda: self._upload_to_ftp(ftp_dialog))
        layout.addWidget(upload_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.setProperty("secondary", True)
        close_btn.clicked.connect(ftp_dialog.accept)
        layout.addWidget(close_btn)
        
        ftp_dialog.setStyleSheet("""
            QDialog { background: #f5f5f5; }
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
            }
            QPushButton {
                background: #0078D7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
            }
            QPushButton:hover { background: #005A9E; }
            QPushButton[secondary="true"] {
                background: #e0e0e0;
                color: #333;
            }
        """)
        
        ftp_dialog.exec()
    
    def _refresh_ftp_list(self):
        """刷新FTP服务器列表"""
        self.ftp_list.clear()
        servers = self.credential_manager.get_all_ftp_servers()
        for name, config in servers.items():
            item = QListWidgetItem(f"{name} ({config['host']}:{config['port']})")
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.ftp_list.addItem(item)
    
    def _add_ftp_server(self, parent_dialog):
        """添加FTP服务器"""
        dialog = FTPServerDialog(parent_dialog)
        if dialog.exec():
            data = dialog.get_data()
            self.credential_manager.save_ftp_server(
                data['name'], data['host'], data['port'],
                data['username'], data['password'], data['path']
            )
            self._refresh_ftp_list()
    
    def _edit_ftp_server(self, parent_dialog):
        """编辑FTP服务器"""
        item = self.ftp_list.currentItem()
        if not item:
            ModernMessageBox.warning(self, "提示", "请先选择一个服务器")
            return
        
        name = item.data(Qt.ItemDataRole.UserRole)
        server_data = self.credential_manager.get_ftp_server(name)
        server_data['name'] = name
        
        dialog = FTPServerDialog(parent_dialog, server_data)
        if dialog.exec():
            # 删除旧的，保存新的
            self.credential_manager.delete_ftp_server(name)
            data = dialog.get_data()
            self.credential_manager.save_ftp_server(
                data['name'], data['host'], data['port'],
                data['username'], data['password'], data['path']
            )
            self._refresh_ftp_list()
    
    def _delete_ftp_server(self):
        """删除FTP服务器"""
        item = self.ftp_list.currentItem()
        if not item:
            ModernMessageBox.warning(self, "提示", "请先选择一个服务器")
            return
        
        name = item.data(Qt.ItemDataRole.UserRole)
        
        reply = ModernMessageBox.question(
            self, "确认删除",
            f"确定要删除服务器 '{name}' 吗？",
            yes_text="确定", no_text="取消"
        )
        
        if reply == QDialog.DialogCode.Accepted:
            self.credential_manager.delete_ftp_server(name)
            self._refresh_ftp_list()
    
    def _upload_to_ftp(self, dialog):
        """上传到FTP"""
        item = self.ftp_list.currentItem()
        if not item:
            ModernMessageBox.warning(self, "提示", "请先选择一个服务器")
            return
        
        if not self.current_pixmap:
            ModernMessageBox.warning(self, "提示", "请先截取或打开一张图像")
            return
        
        name = item.data(Qt.ItemDataRole.UserRole)
        dialog.accept()
        
        self.progress_dialog = ShareProgressDialog(self)
        self.share_manager.upload_to_ftp(self.current_pixmap, name)
        self.progress_dialog.show()
    
    def _show_cloud_accounts(self):
        """显示云存储账号管理"""
        dialog = CloudAccountDialog(self)
        dialog.exec()
