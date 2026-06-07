import os
import sys
import requests
import subprocess
from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtWidgets import QApplication
from ui.modern_dialog import ModernMessageBox
from core.i18n import tr

UPDATE_URL = "http://software.kunqiongai.com:8000/api/v1/updates/check/"
SOFTWARE_ID = "10013"


class CheckUpdateThread(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, current_version):
        super().__init__()
        self.current_version = current_version

    def run(self):
        try:
            params = {
                "software": SOFTWARE_ID,
                "version": self.current_version,
            }

            try:
                response = requests.get(UPDATE_URL, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data and isinstance(data, dict):
                        self.finished.emit(data)
                        return
                    self.error.emit(tr("服务器返回数据格式错误"))
                else:
                    self.error.emit(
                        tr("服务器响应错误: {status_code}").format(status_code=response.status_code)
                    )
            except requests.exceptions.RequestException as e:
                self.error.emit(tr("网络连接失败: {error}").format(error=str(e)))

        except Exception as e:
            self.error.emit(str(e))


class UpdateManager(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_version = "1.0.0"
        self.check_thread = None
        self.expected_hash = None
        self.is_manual = False

    def check_for_updates(self, manual=False):
        self.current_version = QApplication.applicationVersion()
        self.is_manual = manual
        self.check_thread = CheckUpdateThread(self.current_version)
        self.check_thread.finished.connect(self._on_check_finished)
        self.check_thread.error.connect(self._on_check_error)
        self.check_thread.start()

    def _on_check_finished(self, data):
        if not data.get("has_update"):
            if self.is_manual:
                ModernMessageBox.information(None, tr("检查更新"), tr("当前已是最新版本"))
            return

        remote_version = data.get("version")
        if not remote_version:
            if self.is_manual:
                ModernMessageBox.warning(None, tr("检查失败"), tr("获取版本信息失败"))
            return

        self.expected_hash = data.get("package_hash")
        download_url = data.get("download_url")
        is_mandatory = data.get("is_mandatory", False)

        msg = tr("发现新版本: {remote_version}\n\n{update_log}").format(
            remote_version=remote_version,
            update_log=data.get("update_log", tr("无更新日志")),
        )

        if is_mandatory:
            msg = tr("【强制更新】\n{msg}").format(msg=msg)
            ModernMessageBox.information(None, tr("必须更新"), msg, ok_text=tr("立即更新"))
            self._launch_updater(download_url)
        else:
            result = ModernMessageBox.question(
                None,
                tr("发现新版本"),
                msg,
                yes_text=tr("立即更新"),
                no_text=tr("稍后"),
                icon_type="success",
            )
            if result == 1:
                self._launch_updater(download_url)

    def _on_check_error(self, error_msg):
        if self.is_manual:
            ModernMessageBox.error(
                None,
                tr("检查失败"),
                tr("检查更新出错:\n{error_msg}").format(error_msg=error_msg),
            )

    def _launch_updater(self, url):
        """直接启动独立更新程序，由其负责下载和安装"""
        try:
            updater_args = []
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
                exe_name = os.path.basename(sys.executable)
                updater_name = "updater.exe" if sys.platform == "win32" else "updater"
                updater_exe = os.path.join(base_dir, updater_name)

                if os.path.exists(updater_exe):
                    updater_args = [
                        updater_exe,
                        "--url", url,
                        "--hash", self.expected_hash if self.expected_hash else "",
                        "--dir", base_dir,
                        "--exe", exe_name,
                        "--pid", str(os.getpid()),
                    ]
                else:
                    raise FileNotFoundError(
                        tr("未找到更新程序: {updater_exe}").format(updater_exe=updater_exe)
                    )
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                exe_name = "main.py"
                updater_script = os.path.join(base_dir, "updater.py")
                python_exe = sys.executable

                updater_args = [
                    python_exe,
                    updater_script,
                    "--url", url,
                    "--hash", self.expected_hash if self.expected_hash else "",
                    "--dir", base_dir,
                    "--exe", exe_name,
                    "--pid", str(os.getpid()),
                ]

            if updater_args:
                popen_kwargs = {"cwd": base_dir}
                if sys.platform == "win32":
                    popen_kwargs["creationflags"] = subprocess.DETACHED_PROCESS
                else:
                    popen_kwargs["start_new_session"] = True

                subprocess.Popen(updater_args, **popen_kwargs)
                QApplication.quit()
        except Exception as e:
            ModernMessageBox.error(
                None,
                tr("更新失败"),
                tr("无法启动更新程序:\n{error}").format(error=str(e)),
            )

    def _compare_versions(self, v1, v2):
        parts1 = [int(x) for x in v1.split('.')]
        parts2 = [int(x) for x in v2.split('.')]

        while len(parts1) < len(parts2):
            parts1.append(0)
        while len(parts2) < len(parts1):
            parts2.append(0)

        if parts1 > parts2:
            return 1
        if parts1 < parts2:
            return -1
        return 0
