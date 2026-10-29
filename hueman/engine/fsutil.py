"""Atomic file writes: temp file in the same directory + os.replace."""

import os
import stat
import tempfile
from pathlib import Path


def atomic_write_text(path: Path, content: str, make_executable: bool = False,
                      encoding: str = "utf-8") -> None:
    """Write `content` to `path` so readers never see a partial file.

    The data goes to a temp file next to the target and is moved into place
    with os.replace. An existing file's permission bits are preserved (new
    files get the umask default); `make_executable` adds the x bits. On any
    failure the original is untouched and the temp file is removed.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except FileNotFoundError:
        umask = os.umask(0)
        os.umask(umask)
        mode = 0o666 & ~umask
    if make_executable:
        mode |= 0o111
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding) as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise
