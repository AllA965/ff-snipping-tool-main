import os
import sys
from pathlib import Path


class SingleInstanceLock:
    """Cross-platform non-blocking single-instance lock."""

    def __init__(self, name: str, lock_dir: Path | None = None):
        safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in name)
        base_dir = lock_dir or (Path.home() / ".pyscreenshot" / "locks")
        self.lock_path = Path(base_dir) / f"{safe_name}.lock"
        self._file = None
        self._acquired = False

    def acquire(self) -> bool:
        if self._acquired:
            return True

        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.lock_path, "a+b")

        try:
            if sys.platform == "win32":
                import msvcrt

                self._file.seek(0)
                self._file.write(b"0")
                self._file.flush()
                msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            self._acquired = True
            return True
        except OSError:
            self.release()
            return False

    def release(self) -> None:
        if self._file is None:
            return

        try:
            if self._acquired:
                if sys.platform == "win32":
                    import msvcrt

                    self._file.seek(0)
                    msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        finally:
            try:
                self._file.close()
            except OSError:
                pass
            self._file = None
            self._acquired = False

    def __del__(self):
        self.release()
