import argparse
import hashlib
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import zipfile

import requests
from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QProgressBar, QVBoxLayout, QWidget

from core.i18n import init_i18n, tr
from core.single_instance import SingleInstanceLock

_updater_lock = SingleInstanceLock("KunQiong_Updater")


def is_already_running() -> bool:
    return not _updater_lock.acquire()


def log(msg: str):
    try:
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "updater_log.txt")
        with open(log_file, "a", encoding="utf-8") as file:
            file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
    except Exception:
        pass


class UpdateSignals(QObject):
    progress = Signal(int)
    status = Signal(str)
    finished = Signal(bool)


class UpdateWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(450, 180)

        self.container = QWidget()
        self.container.setObjectName("container")
        self.container.setStyleSheet(
            """
            QWidget#container {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffffff, stop:1 #f8f9fa);
                border: 1px solid #dcdfe6;
                border-radius: 12px;
            }
            QLabel#titleLabel {
                color: #2c3e50;
                font-size: 18px;
                font-weight: bold;
                font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC";
            }
            QLabel#statusLabel {
                color: #5e6d82;
                font-size: 13px;
                font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC";
            }
            QLabel#percentageLabel {
                color: #409eff;
                font-size: 13px;
                font-weight: bold;
                font-family: "Consolas", "Monaco";
            }
            QProgressBar {
                border: none;
                background-color: #ebeef5;
                height: 8px;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #409eff, stop:1 #66b1ff);
                border-radius: 4px;
            }
            """
        )
        self.setCentralWidget(self.container)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(12)

        self.title_label = QLabel(tr("正在升级系统"))
        self.title_label.setObjectName("titleLabel")
        layout.addWidget(self.title_label)

        self.status_label = QLabel(tr("准备就绪..."))
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        self.percentage_label = QLabel("0%")
        self.percentage_label.setObjectName("percentageLabel")
        self.percentage_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.percentage_label)

        try:
            from PySide6.QtWidgets import QGraphicsDropShadowEffect

            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(30)
            shadow.setColor(QColor(0, 0, 0, 60))
            shadow.setOffset(0, 8)
            self.container.setGraphicsEffect(shadow)
        except Exception:
            pass

    def update_status(self, text: str):
        self.status_label.setText(text)

    def update_progress(self, value: int):
        self.progress_bar.setValue(value)
        self.percentage_label.setText(f"{value}%")


def is_process_running(pid: int) -> bool:
    if pid <= 0:
        return False

    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def kill_process(pid: int) -> bool:
    log(f"Attempting to kill process {pid}")

    if pid <= 0:
        return False

    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=False, capture_output=True)
        else:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.5)
            if is_process_running(pid):
                os.kill(pid, signal.SIGKILL)
        return not is_process_running(pid)
    except Exception as exc:
        log(f"Failed to kill process: {exc}")
        return False


def _launch_target(exe_path: str, cwd: str):
    if sys.platform == "win32":
        subprocess.Popen(
            [exe_path],
            cwd=cwd,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
        )
    else:
        if os.path.exists(exe_path):
            os.chmod(exe_path, os.stat(exe_path).st_mode | 0o111)
        subprocess.Popen([exe_path], cwd=cwd, start_new_session=True)


def _download_zip(args, signals) -> str | None:
    zip_path = args.zip

    if not args.url:
        return zip_path

    signals.status.emit(tr("正在下载更新包..."))

    try:
        temp_dir = os.path.dirname(args.zip) if args.zip else tempfile.gettempdir()
        if not zip_path:
            zip_path = os.path.join(temp_dir, "update_package.zip")

        response = requests.get(args.url, stream=True, timeout=30)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0
        sha256 = hashlib.sha256()

        with open(zip_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                file.write(chunk)
                sha256.update(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    progress = 10 + int(downloaded / total_size * 40)
                    signals.progress.emit(progress)

        if args.hash:
            actual_hash = sha256.hexdigest()
            if actual_hash.lower() != args.hash.lower():
                log(f"Hash mismatch. expected={args.hash}, actual={actual_hash}")
                signals.status.emit(tr("校验失败：下载文件损坏"))
                signals.finished.emit(False)
                return None

        return zip_path

    except Exception as exc:
        log(f"Download failed: {exc}")
        signals.status.emit(tr("下载失败: {error}").format(error=str(exc)))
        signals.finished.emit(False)
        return None


def _extract_package(zip_path: str, target_dir: str, signals) -> bool:
    signals.status.emit(tr("正在安装更新..."))
    signals.progress.emit(50)

    max_retries = 5

    for retry in range(max_retries):
        try:
            with zipfile.ZipFile(zip_path, "r") as archive:
                files = archive.namelist()
                total_files = len(files) if files else 1

                for index, member in enumerate(files):
                    lower = member.lower()
                    if lower.endswith("updater.exe") or lower.endswith("/updater") or lower.endswith("\\updater"):
                        continue

                    archive.extract(member, target_dir)
                    progress = 50 + int((index + 1) / total_files * 40)
                    signals.progress.emit(progress)

            return True
        except PermissionError as exc:
            log(f"Permission error ({retry + 1}/{max_retries}): {exc}")
            signals.status.emit(tr("正在重试 ({current}/{total})...").format(current=retry + 1, total=max_retries))
            time.sleep(2)
        except Exception as exc:
            log(f"Extraction error ({retry + 1}/{max_retries}): {exc}")
            time.sleep(1)

    signals.status.emit(tr("安装失败：文件被占用"))
    return False


def update_worker(args, signals):
    try:
        if args.pid:
            signals.status.emit(tr("正在关闭主程序..."))
            signals.progress.emit(5)

            start_time = time.time()
            timeout = 10
            while is_process_running(args.pid):
                if time.time() - start_time > timeout:
                    kill_process(args.pid)
                    time.sleep(1)
                    break
                time.sleep(0.5)

        signals.progress.emit(10)

        zip_path = _download_zip(args, signals)
        if not zip_path:
            return

        if not _extract_package(zip_path, args.dir, signals):
            signals.finished.emit(False)
            return

        signals.progress.emit(95)
        signals.status.emit(tr("清理并重启..."))

        try:
            if zip_path and os.path.exists(zip_path):
                os.remove(zip_path)
        except Exception as exc:
            log(f"Failed to remove zip: {exc}")

        exe_path = os.path.join(args.dir, args.exe)
        if not os.path.exists(exe_path):
            log(f"Executable not found: {exe_path}")
            signals.status.emit(tr("未找到主程序"))
            signals.finished.emit(False)
            return

        try:
            _launch_target(exe_path, args.dir)
            signals.progress.emit(100)
            signals.finished.emit(True)
        except Exception as exc:
            log(f"Failed to restart application: {exc}")
            signals.status.emit(tr("启动失败，请手动打开程序"))
            signals.finished.emit(False)

    except Exception:
        log(f"Critical error in worker: {traceback.format_exc()}")
        signals.status.emit(tr("更新出错，请联系支持"))
        signals.finished.emit(False)


def main():
    if is_already_running():
        sys.exit(0)

    parser = argparse.ArgumentParser(description="Independent Updater")
    parser.add_argument("--zip", help="Path to local update zip file")
    parser.add_argument("--url", help="URL to download update package")
    parser.add_argument("--hash", help="Expected SHA256 hash of the package")
    parser.add_argument("--dir", required=True, help="Installation directory")
    parser.add_argument("--exe", required=True, help="Main executable name to restart")
    parser.add_argument("--pid", type=int, help="PID of the main process to wait for")
    args = parser.parse_args()

    init_i18n("auto")
    app = QApplication(sys.argv)

    window = UpdateWindow()
    window.show()

    screen_geometry = app.primaryScreen().geometry()
    window.move(
        (screen_geometry.width() - window.width()) // 2,
        (screen_geometry.height() - window.height()) // 2,
    )

    signals = UpdateSignals()
    signals.status.connect(window.update_status)
    signals.progress.connect(window.update_progress)

    def on_finished(success):
        if success:
            QTimer.singleShot(1000, app.quit)
        else:
            QTimer.singleShot(5000, app.quit)

    signals.finished.connect(on_finished)

    worker_thread = threading.Thread(target=update_worker, args=(args, signals), daemon=True)
    worker_thread.start()

    exit_code = app.exec()
    _updater_lock.release()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
