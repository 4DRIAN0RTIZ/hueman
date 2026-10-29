"""Backend-agnostic StateSource contract, run against every registered backend."""

import shutil
import subprocess
from pathlib import Path

import pytest

from hueman.engine.statesource import ReadResult, State, StateSource

from test_state_branch import git


@pytest.fixture(params=["git", "file"])
def backend(request, tmp_path):
    """Yields (make, break_it): `make(name)` builds a source over one shared
    store; `break_it()` makes the store unreachable for every source."""
    if request.param == "git":
        if shutil.which("git") is None:
            pytest.skip("git not installed")
        from hueman.engine.statesource import GitBranchSource
        bare = tmp_path / "remote.git"
        git("init", "--bare", "-q", str(bare))
        repo = tmp_path / "dotfiles"
        git("init", "-q", str(repo))
        git("remote", "add", "origin", f"file://{bare}", cwd=repo)

        def make(name="a"):
            return GitBranchSource(repo=repo, workdir=tmp_path / f"ws-{name}")

        def break_it():
            shutil.rmtree(bare)
        return make, break_it
    from hueman.engine.statesource import FileSource
    folder = tmp_path / "synced"
    folder.mkdir()

    def make(name="a"):
        return FileSource(folder / "hueman.state.yaml")

    def break_it():
        shutil.rmtree(folder)
    return make, break_it


def test_is_state_source(backend):
    make, _ = backend
    assert isinstance(make(), StateSource)


def test_empty_store_reads_none_but_reachable(backend):
    make, _ = backend
    assert make().read_result() == ReadResult(None, True)
    assert make().read() is None


def test_write_then_read_roundtrip_across_instances(backend):
    make, _ = backend
    assert make("a").write(State("nord", 3)) is True
    res = make("b").read_result()
    assert res == ReadResult(State("nord", 3), True)


def test_higher_revision_overwrites(backend):
    make, _ = backend
    src = make()
    src.write(State("nord", 1))
    assert src.write(State("gruvbox", 2)) is True
    assert src.read() == State("gruvbox", 2)


def test_lower_revision_is_refused(backend):
    make, _ = backend
    make("a").write(State("nord", 5))
    assert make("b").write(State("gruvbox", 4)) is False
    assert make("a").read() == State("nord", 5)


def test_identical_state_is_idempotent_true(backend):
    make, _ = backend
    src = make()
    assert src.write(State("nord", 1)) is True
    assert src.write(State("nord", 1)) is True
    assert src.read() == State("nord", 1)


def test_tie_with_different_palette_accepted_write_wins(backend):
    make, _ = backend
    make("a").write(State("nord", 2))
    assert make("b").write(State("gruvbox", 2)) is True
    assert make("a").read() == State("gruvbox", 2)


def test_unreachable_never_raises(backend):
    make, break_it = backend
    make().write(State("nord", 1))
    break_it()
    src = make("c")
    res = src.read_result()
    assert res.remote is False
    assert src.write(State("nord", 2)) is False
    assert src.read() in (None, State("nord", 1))  # cache allowed, never an exception
