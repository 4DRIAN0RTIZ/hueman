"""Orphan `hueman-state` branch: GitBranchSource against real temp git repos."""

import shutil
import subprocess

import pytest

from hueman.engine.config import ConfigError, HuemanConfig
from hueman.engine.statesource import GitBranchSource, State, StateSource
from test_reload_exit_codes import make_app

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")

BRANCH = "hueman-state"


def git(*args, cwd=None):
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True,
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": "/nonexistent",
             "GIT_CONFIG_NOSYSTEM": "1"},
    ).stdout.strip()


@pytest.fixture
def remote(tmp_path):
    bare = tmp_path / "remote.git"
    git("init", "--bare", "-q", str(bare))
    return bare


@pytest.fixture
def dotfiles(tmp_path, remote):
    repo = tmp_path / "dotfiles"
    git("init", "-q", str(repo))
    git("remote", "add", "origin", f"file://{remote}", cwd=repo)
    return repo


def make_source(tmp_path, dotfiles, name="ws", **kw):
    return GitBranchSource(repo=dotfiles, workdir=tmp_path / name, **kw)


def remote_state(remote):
    return git("--git-dir", str(remote), "show", f"{BRANCH}:hueman.state.yaml")


def test_is_a_state_source(tmp_path, dotfiles):
    assert isinstance(make_source(tmp_path, dotfiles), StateSource)


def test_read_returns_none_when_branch_missing(tmp_path, dotfiles):
    assert make_source(tmp_path, dotfiles).read() is None


def test_write_creates_orphan_single_commit(tmp_path, dotfiles, remote):
    assert make_source(tmp_path, dotfiles).write(State("nord", 1)) is True
    assert git("--git-dir", str(remote), "rev-list", "--count", BRANCH) == "1"
    assert git("--git-dir", str(remote), "cat-file", "-p", BRANCH).count("parent") == 0
    assert git("--git-dir", str(remote), "ls-tree", "--name-only", BRANCH) == "hueman.state.yaml"
    text = remote_state(remote)
    assert "palette: nord" in text and "revision: 1" in text


def test_second_write_amends_keeping_one_commit(tmp_path, dotfiles, remote):
    src = make_source(tmp_path, dotfiles)
    src.write(State("nord", 1))
    first = git("--git-dir", str(remote), "rev-parse", BRANCH)
    assert src.write(State("gruvbox", 2)) is True
    assert git("--git-dir", str(remote), "rev-list", "--count", BRANCH) == "1"
    assert git("--git-dir", str(remote), "rev-parse", BRANCH) != first
    assert "palette: gruvbox" in remote_state(remote)


def test_read_roundtrip(tmp_path, dotfiles):
    make_source(tmp_path, dotfiles).write(State("nord", 7))
    assert make_source(tmp_path, dotfiles, "other").read() == State("nord", 7)


def test_dotfiles_repo_is_never_touched(tmp_path, dotfiles):
    before = git("for-each-ref", cwd=dotfiles), git("status", "--porcelain", cwd=dotfiles)
    src = make_source(tmp_path, dotfiles)
    src.write(State("nord", 1))
    src.read()
    assert (git("for-each-ref", cwd=dotfiles), git("status", "--porcelain", cwd=dotfiles)) == before
    assert not (dotfiles / "hueman.state.yaml").exists()


def test_no_remote_configured_degrades(tmp_path):
    repo = tmp_path / "bare-dotfiles"
    git("init", "-q", str(repo))
    src = GitBranchSource(repo=repo, workdir=tmp_path / "ws")
    assert src.read() is None
    assert src.write(State("nord", 1)) is False


def test_missing_repo_degrades(tmp_path):
    src = GitBranchSource(repo=tmp_path / "nope", workdir=tmp_path / "ws")
    assert src.read() is None
    assert src.write(State("nord", 1)) is False


def test_unreachable_remote_degrades(tmp_path, dotfiles):
    git("remote", "set-url", "origin", f"file://{tmp_path}/gone.git", cwd=dotfiles)
    src = make_source(tmp_path, dotfiles)
    assert src.write(State("nord", 1)) is False
    assert src.read() is None


def test_git_missing_degrades(tmp_path, dotfiles, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda *_a, **_k: None)
    src = make_source(tmp_path, dotfiles)
    assert src.write(State("nord", 1)) is False
    assert src.read() is None


def test_higher_remote_revision_wins_without_push(tmp_path, dotfiles, remote):
    make_source(tmp_path, dotfiles, "a").write(State("nord", 5))
    assert make_source(tmp_path, dotfiles, "b").write(State("gruvbox", 3)) is False
    assert "palette: nord" in remote_state(remote)


def test_same_state_is_not_repushed(tmp_path, dotfiles, remote):
    src = make_source(tmp_path, dotfiles)
    src.write(State("nord", 2))
    sha = git("--git-dir", str(remote), "rev-parse", BRANCH)
    assert src.write(State("nord", 2)) is True
    assert git("--git-dir", str(remote), "rev-parse", BRANCH) == sha


def race(src, other, state, calls=None):
    """Make `other` write `state` right before src's first push (lost race)."""
    original = src._push
    done = []

    def push(*a, **k):
        if calls is not None:
            calls.append(1)
        if not done:
            done.append(1)
            other.write(state)
        return original(*a, **k)

    src._push = push


def test_rejected_push_remote_higher_wins(tmp_path, dotfiles, remote):
    a = make_source(tmp_path, dotfiles, "a")
    race(a, make_source(tmp_path, dotfiles, "b"), State("gruvbox", 5))
    assert a.write(State("nord", 3)) is False
    assert "palette: gruvbox" in remote_state(remote)


def test_rejected_push_tie_accepted_push_wins(tmp_path, dotfiles, remote):
    a = make_source(tmp_path, dotfiles, "a")
    race(a, make_source(tmp_path, dotfiles, "b"), State("gruvbox", 3))
    assert a.write(State("nord", 3)) is True
    assert "palette: nord" in remote_state(remote)
    assert git("--git-dir", str(remote), "rev-list", "--count", BRANCH) == "1"


def test_retries_are_bounded(tmp_path, dotfiles):
    a = make_source(tmp_path, dotfiles, "a", max_retries=2)
    calls = []
    a._push = lambda *args, **kw: calls.append(1) or False
    assert a.write(State("nord", 1)) is False
    assert len(calls) == 3


# --- config + Hueman integration -------------------------------------------

def sync_cfg(dotfiles, workdir):
    return (f"state_sync:\n  repo: {dotfiles}\n  remote: origin\n"
            f"  branch: {BRANCH}\n  workdir: {workdir}\n")


def app(tmp_path, dotfiles, **kw):
    return make_app(tmp_path, extra_top=sync_cfg(dotfiles, tmp_path / "ws"),
                    targets={"k": {}}, **kw)


def test_config_absent_means_disabled(tmp_path):
    assert make_app(tmp_path).config.state_sync is None


def test_config_defaults(tmp_path):
    a = make_app(tmp_path, extra_top="state_sync:\n  repo: /x\n")
    assert (a.config.state_sync.remote, a.config.state_sync.branch) == ("origin", BRANCH)


@pytest.mark.parametrize("bad", ["state_sync: 3\n", "state_sync: {}\n",
                                 "state_sync: {repo: /x, branch: 5}\n"])
def test_config_invalid(tmp_path, bad):
    with pytest.raises(ConfigError):
        make_app(tmp_path, extra_top=bad)


def test_set_writes_incrementing_revision(tmp_path, dotfiles, remote):
    a = app(tmp_path, dotfiles)
    assert a.set_theme("one") == []
    assert "revision: 1" in remote_state(remote)
    assert a.set_theme("one") == []
    assert "revision: 2" in remote_state(remote)
    assert "palette: one" in remote_state(remote)


def test_set_dry_run_and_only_never_write_state(tmp_path, dotfiles, remote):
    a = app(tmp_path, dotfiles)
    a.set_theme("one", dry_run=True)
    a.set_theme("one", only=["k"])
    assert git("--git-dir", str(remote), "branch", "--list") == ""


def test_set_without_network_still_applies_locally(tmp_path, dotfiles):
    git("remote", "set-url", "origin", f"file://{tmp_path}/gone.git", cwd=dotfiles)
    a = app(tmp_path, dotfiles)
    assert a.set_theme("one") == []
    assert (tmp_path / "state").read_text().strip() == "one"
    assert (tmp_path / "k.out").exists()


def test_set_without_state_sync_unchanged(tmp_path):
    a = make_app(tmp_path, targets={"k": {}})
    assert a.set_theme("one") == []
