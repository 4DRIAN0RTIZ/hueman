"""Real-network timeout of the git backend: a local TCP server that accepts
connections and never replies stands in for a hung remote (no mocks)."""

import shutil
import socket
import threading
import time

import pytest

from hueman.engine.statesource import ReadResult
from test_reload_exit_codes import make_app
from test_state_branch import BRANCH, dotfiles, git, make_source, remote, sync_cfg  # noqa: F401

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")

TIMEOUT = 1
MAX_ELAPSED = 8  # generous slack over TIMEOUT so slow CI is not flaky


@pytest.fixture
def blackhole():
    """Port of a 127.0.0.1 server that accepts connections and never answers."""
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(8)
    held = []

    def accept_loop():
        while True:
            try:
                held.append(srv.accept()[0])
            except OSError:  # listening socket closed
                return

    threading.Thread(target=accept_loop, daemon=True).start()
    try:
        yield srv.getsockname()[1]
    finally:
        srv.close()
        for c in held:
            c.close()


@pytest.fixture
def hung(tmp_path, dotfiles, blackhole):  # noqa: F811
    git("remote", "set-url", "origin", f"git://127.0.0.1:{blackhole}/repo.git", cwd=dotfiles)
    return dotfiles


def hung_app(tmp_path, hung):
    cfg = sync_cfg(hung, tmp_path / "ws") + f"  timeout: {TIMEOUT}\n"
    return make_app(tmp_path, extra_top=cfg, targets={"k": {}})


def test_read_result_degrades_when_remote_hangs(tmp_path, hung):
    start = time.monotonic()
    res = make_source(tmp_path, hung, timeout=TIMEOUT).read_result()
    assert res == ReadResult(None, False)
    assert time.monotonic() - start < MAX_ELAPSED


def test_sync_unreachable_when_remote_hangs(tmp_path, hung):
    a = hung_app(tmp_path, hung)
    start = time.monotonic()
    assert a.sync() == (0, "unreachable")
    assert time.monotonic() - start < MAX_ELAPSED


def test_status_reports_unreachable_when_remote_hangs(tmp_path, hung, capsys):
    a = hung_app(tmp_path, hung)
    start = time.monotonic()
    a.status()
    elapsed = time.monotonic() - start
    assert "Drift: remote unreachable" in capsys.readouterr().out
    assert elapsed < MAX_ELAPSED
