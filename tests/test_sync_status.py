"""`hueman sync` and drift-aware `status` against temp bare repos."""

import logging
import shutil
import sys

import pytest

import hueman.cli as hueman
from hueman.engine.statesource import GitBranchSource, ReadResult, State
from test_reload_exit_codes import make_app
from test_state_branch import BRANCH, app, dotfiles, git, make_source, remote, remote_state  # noqa: F401

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")


def peer(tmp_path, dotfiles):
    return make_source(tmp_path, dotfiles, "peer")


def rev_file(tmp_path):
    return tmp_path / "state.revision"


# --- StateSource.read_result ---------------------------------------------

def test_read_result_remote_flag(tmp_path, dotfiles):
    peer(tmp_path, dotfiles).write(State("nord", 3))
    res = make_source(tmp_path, dotfiles).read_result()
    assert res == ReadResult(State("nord", 3), True)


def test_read_result_empty_remote_is_reachable(tmp_path, dotfiles):
    assert make_source(tmp_path, dotfiles).read_result() == ReadResult(None, True)


def test_read_result_cache_when_unreachable(tmp_path, dotfiles):
    src = make_source(tmp_path, dotfiles)
    src.write(State("nord", 3))
    git("remote", "set-url", "origin", f"file://{tmp_path}/gone.git", cwd=dotfiles)
    res = make_source(tmp_path, dotfiles).read_result()
    assert res == ReadResult(State("nord", 3), False)
    assert make_source(tmp_path, dotfiles).read() == State("nord", 3)


def test_read_result_no_remote_configured(tmp_path):
    repo = tmp_path / "d"
    git("init", "-q", str(repo))
    res = GitBranchSource(repo=repo, workdir=tmp_path / "ws").read_result()
    assert res == ReadResult(None, False)


def test_git_calls_are_bounded_by_timeout(tmp_path, dotfiles):
    from hueman.engine import statesource
    assert 0 < statesource.GIT_TIMEOUT <= 30
    assert make_source(tmp_path, dotfiles, timeout=5).timeout == 5


def test_timeout_degrades_instead_of_hanging(tmp_path, dotfiles, monkeypatch):
    import subprocess
    def boom(*a, **k):
        raise subprocess.TimeoutExpired("git", 1)
    monkeypatch.setattr(subprocess, "run", boom)
    assert make_source(tmp_path, dotfiles).read_result() == ReadResult(None, False)


# --- local revision storage ----------------------------------------------

def test_local_revision_absent_is_none(tmp_path, dotfiles):
    assert app(tmp_path, dotfiles).local_revision() is None


def test_plain_state_file_stays_backward_compatible(tmp_path, dotfiles):
    a = app(tmp_path, dotfiles)
    a.set_theme("one")
    assert (tmp_path / "state").read_text() == "one\n"
    assert rev_file(tmp_path).read_text().strip() == "1"


@pytest.mark.parametrize("junk", ["", "abc", "-3", "1.5"])
def test_corrupt_revision_file_reads_as_none(tmp_path, dotfiles, junk):
    a = app(tmp_path, dotfiles)
    rev_file(tmp_path).write_text(junk)
    assert a.local_revision() is None


def test_set_persists_published_revision(tmp_path, dotfiles, remote):
    a = app(tmp_path, dotfiles)
    a.set_theme("one")
    a.set_theme("one")
    assert a.local_revision() == 2
    assert "revision: 2" in remote_state(remote)


def test_set_builds_on_local_revision_when_remote_empty(tmp_path, dotfiles):
    a = app(tmp_path, dotfiles)
    rev_file(tmp_path).write_text("9\n")
    a.set_theme("one")
    assert a.local_revision() == 10


def test_set_unpublished_keeps_local_revision(tmp_path, dotfiles):
    a = app(tmp_path, dotfiles)
    a.set_theme("one")
    git("remote", "set-url", "origin", f"file://{tmp_path}/gone.git", cwd=dotfiles)
    a.set_theme("one")
    assert a.local_revision() == 1


def test_set_without_state_sync_writes_no_revision(tmp_path):
    make_app(tmp_path, targets={"k": {}}).set_theme("one")
    assert not rev_file(tmp_path).exists()


# --- sync ------------------------------------------------------------------

def test_sync_applies_newer_remote_without_publishing(tmp_path, dotfiles, remote):
    peer(tmp_path, dotfiles).write(State("one", 4))
    sha = git("--git-dir", str(remote), "rev-parse", BRANCH)
    a = app(tmp_path, dotfiles)
    assert a.sync() == (0, "applied")
    assert (tmp_path / "state").read_text() == "one\n"
    assert (tmp_path / "k.out").exists()
    assert a.local_revision() == 4
    assert git("--git-dir", str(remote), "rev-parse", BRANCH) == sha


def test_sync_is_idempotent_no_writes_no_reload(tmp_path, dotfiles):
    peer(tmp_path, dotfiles).write(State("one", 4))
    marker = tmp_path / "reloaded"
    a = make_app(tmp_path, extra_top=__import__("test_state_branch").sync_cfg(dotfiles, tmp_path / "ws"),
                 targets={"k": {"reload": f"touch {marker}"}})
    assert a.sync()[1] == "applied"
    marker.unlink()
    (tmp_path / "k.out").unlink()
    assert a.sync() == (0, "in-sync")
    assert not marker.exists() and not (tmp_path / "k.out").exists()


def test_sync_noop_when_local_ahead(tmp_path, dotfiles):
    peer(tmp_path, dotfiles).write(State("one", 2))
    a = app(tmp_path, dotfiles)
    rev_file(tmp_path).write_text("5\n")
    assert a.sync() == (0, "ahead")
    assert not (tmp_path / "state").exists()


def test_sync_noop_on_empty_remote(tmp_path, dotfiles):
    a = app(tmp_path, dotfiles)
    assert a.sync() == (0, "no-remote-state")
    assert not (tmp_path / "state").exists()


def test_sync_treats_missing_local_revision_as_zero(tmp_path, dotfiles):
    peer(tmp_path, dotfiles).write(State("one", 1))
    (tmp_path / "state").write_text("other\n")
    assert app(tmp_path, dotfiles).sync()[1] == "applied"


def test_sync_unreachable_exits_zero_and_never_uses_cache(tmp_path, dotfiles):
    peer(tmp_path, dotfiles).write(State("one", 4))
    a = app(tmp_path, dotfiles)
    a.sync()
    (tmp_path / "state").unlink()
    rev_file(tmp_path).write_text("1\n")
    git("remote", "set-url", "origin", f"file://{tmp_path}/gone.git", cwd=dotfiles)
    b = app(tmp_path, dotfiles)
    assert b.sync() == (0, "unreachable")
    assert not (tmp_path / "state").exists()


def test_sync_without_state_sync_is_notice_exit_zero(tmp_path, capsys):
    a = make_app(tmp_path, targets={"k": {}})
    assert a.sync() == (0, "disabled")
    assert not (tmp_path / "k.out").exists()


def test_sync_failed_target_does_not_persist_revision(tmp_path, dotfiles):
    peer(tmp_path, dotfiles).write(State("one", 4))
    a = make_app(tmp_path, extra_top="reload_failure: error\n" +
                 __import__("test_state_branch").sync_cfg(dotfiles, tmp_path / "ws"),
                 targets={"k": {"reload": "exit 2"}})
    code, why = a.sync()
    assert code == 1 and why == "failed"
    assert a.local_revision() is None


def test_sync_unknown_palette_is_error(tmp_path, dotfiles):
    peer(tmp_path, dotfiles).write(State("nope", 4))
    with pytest.raises(SystemExit) as exc:
        app(tmp_path, dotfiles).sync()
    assert exc.value.code == 1


# --- status ------------------------------------------------------------------

def status_out(a, capsys):
    a.status()
    return capsys.readouterr().out


def test_status_without_state_sync_unchanged(tmp_path, capsys):
    out = status_out(make_app(tmp_path, targets={"k": {}}), capsys)
    assert "Tema activo" in out and "Drift" not in out


@pytest.mark.parametrize("local,remote_rev,label", [
    (3, 3, "in sync"), (1, 3, "behind"), (5, 3, "ahead"), (None, 3, "behind")])
def test_status_drift(tmp_path, dotfiles, capsys, local, remote_rev, label):
    peer(tmp_path, dotfiles).write(State("one", remote_rev))
    a = app(tmp_path, dotfiles)
    if local is not None:
        rev_file(tmp_path).write_text(f"{local}\n")
    out = status_out(a, capsys)
    assert f"Drift: {label}" in out
    assert f"r{remote_rev} (remote," in out


def test_status_unreachable_marks_cache(tmp_path, dotfiles, capsys):
    peer(tmp_path, dotfiles).write(State("one", 3))
    a = app(tmp_path, dotfiles)
    a.sync()
    git("remote", "set-url", "origin", f"file://{tmp_path}/gone.git", cwd=dotfiles)
    out = status_out(app(tmp_path, dotfiles), capsys)
    assert "Drift: remote unreachable" in out
    assert "r3 (local cache" in out


def test_status_empty_remote(tmp_path, dotfiles, capsys):
    out = status_out(app(tmp_path, dotfiles), capsys)
    assert "Drift: no remote state" in out


# --- CLI ---------------------------------------------------------------------

def run_cli(monkeypatch, tmp_path, *argv):
    monkeypatch.setattr(sys, "argv", ["hueman", "--config", str(tmp_path / "hueman.yaml"), *argv])
    with pytest.raises(SystemExit) as exc:
        hueman.main()
        sys.exit(0)
    return exc.value.code


def test_cli_sync_applies_and_exits_zero(tmp_path, dotfiles, monkeypatch):
    peer(tmp_path, dotfiles).write(State("one", 2))
    app(tmp_path, dotfiles)
    assert run_cli(monkeypatch, tmp_path, "sync") == 0
    assert (tmp_path / "state").read_text() == "one\n"


def test_cli_sync_quiet_on_no_change(tmp_path, dotfiles, monkeypatch, capsys):
    app(tmp_path, dotfiles)
    assert run_cli(monkeypatch, tmp_path, "sync") == 0
    cap = capsys.readouterr()
    assert cap.out == "" and cap.err == ""


def test_cli_sync_quiet_flag_silences_notices(tmp_path, dotfiles, monkeypatch, caplog):
    app(tmp_path, dotfiles)
    git("remote", "set-url", "origin", f"file://{tmp_path}/gone.git", cwd=dotfiles)
    assert run_cli(monkeypatch, tmp_path, "sync") == 0
    assert "inalcanzable" in caplog.text  # without --quiet the offline notice shows
    caplog.clear()
    assert run_cli(monkeypatch, tmp_path, "sync", "--quiet") == 0
    assert caplog.text == ""


def test_cli_sync_disabled_exit_zero_with_notice(tmp_path, monkeypatch, caplog):
    make_app(tmp_path, targets={"k": {}})
    assert run_cli(monkeypatch, tmp_path, "sync") == 0
    assert "state_sync" in caplog.text


def test_config_timeout(tmp_path):
    a = make_app(tmp_path, extra_top="state_sync:\n  repo: /x\n  timeout: 4\n")
    assert a.config.state_sync.timeout == 4
    from hueman.engine.config import ConfigError
    for bad in ("0", "-1", "abc", "true"):
        with pytest.raises(ConfigError):
            make_app(tmp_path, extra_top=f"state_sync:\n  repo: /x\n  timeout: {bad}\n")
