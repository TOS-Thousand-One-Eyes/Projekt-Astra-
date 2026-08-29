import hashlib
import json
import os
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


_PROCESS_FILE_LOCK = threading.RLock()
_WINDOWS_LOCK_RETRY_SECONDS = 30.0


def lock_path_for(path):
    """Return a per-user lock-file path without dirtying the data directory."""
    resolved = os.path.normcase(str(Path(path).resolve(strict=False)))
    digest = hashlib.sha256(resolved.encode("utf-8", errors="surrogatepass")).hexdigest()
    return Path(tempfile.gettempdir()) / "astra-file-locks" / f"{digest}.lock"


@contextmanager
def interprocess_file_lock(path):
    """Serialize a file transaction across threads, instances, and processes."""
    lock_path = lock_path_for(path)
    with _PROCESS_FILE_LOCK:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_path, "a+b") as handle:
            _lock_handle(handle)
            try:
                yield
            finally:
                _unlock_handle(handle)


def atomic_json_write(
    path,
    payload,
    *,
    replace_func=os.replace,
    errors=None,
    trailing_newline=False,
):
    """Write JSON through a unique sibling temporary file and clean up on failure."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target.with_suffix(
        f"{target.suffix}.{os.getpid()}.{threading.get_ident()}."
        f"{uuid.uuid4().hex[:8]}.tmp"
    )
    open_kwargs = {"encoding": "utf-8"}
    if errors is not None:
        open_kwargs["errors"] = errors
    try:
        with open(tmp_path, "w", **open_kwargs) as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            if trailing_newline:
                handle.write("\n")
        replace_func(tmp_path, target)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


def _lock_handle(handle):
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"\0")
        handle.flush()
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        deadline = time.monotonic() + _WINDOWS_LOCK_RETRY_SECONDS
        while True:
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.05)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)


def _unlock_handle(handle):
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
