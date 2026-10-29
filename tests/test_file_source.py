"""FileSource specifics (state file in a synced folder) and the source registry."""

import pytest

from hueman.engine.config import ConfigError
from hueman.engine.statesource import (FileSource, ReadResult, State, StateSource,
                                build_source)
from test_reload_exit_codes import make_app


def test_corrupt_file_reads_as_empty_but_reachable(tmp_path):
    f = tmp_path / "s.yaml"
    f.write_text("{{{ not yaml")
    assert FileSource(f).read_result() == ReadResult(None, True)


@pytest.mark.parametrize("junk", ["", "palette: x\n", "palette: x\nrevision: nope\n", "- 1\n"])
def test_junk_contents_never_raise(tmp_path, junk):
    f = tmp_path / "s.yaml"
    f.write_text(junk)
    assert FileSource(f).read() is None


def test_corrupt_file_is_replaced_by_write(tmp_path):
    f = tmp_path / "s.yaml"
    f.write_text("garbage")
    assert FileSource(f).write(State("nord", 1)) is True
    assert FileSource(f).read() == State("nord", 1)


def test_missing_parent_is_unreachable_and_not_created(tmp_path):
    f = tmp_path / "gone" / "s.yaml"
    src = FileSource(f)
    assert src.read_result() == ReadResult(None, False)
    assert src.write(State("nord", 1)) is False
    assert not f.parent.exists()


def test_write_is_atomic_via_fsutil(tmp_path, monkeypatch):
    from hueman.engine import statesource
    calls = []
    real = statesource.atomic_write_text
    monkeypatch.setattr(statesource, "atomic_write_text",
                        lambda p, c, **k: (calls.append(p), real(p, c, **k)))
    FileSource(tmp_path / "s.yaml").write(State("nord", 1))
    assert calls == [tmp_path / "s.yaml"]
    assert [p.name for p in tmp_path.iterdir()] == ["s.yaml"]


def test_write_error_degrades_to_false(tmp_path, monkeypatch):
    from hueman.engine import statesource
    def boom(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(statesource, "atomic_write_text", boom)
    assert FileSource(tmp_path / "s.yaml").write(State("nord", 1)) is False


def test_expands_user(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert FileSource("~/s.yaml").path == tmp_path / "s.yaml"


# -- abstract base ----------------------------------------------------------

def test_state_source_is_abstract():
    with pytest.raises(TypeError):
        StateSource()


def test_minimal_subclass_gets_read_for_free():
    class Mem(StateSource):
        def read_result(self):
            return ReadResult(State("x", 1), True)

        def write(self, state):
            return True
    assert Mem().read() == State("x", 1)


# -- registry + config ------------------------------------------------------

def test_default_type_is_git_backward_compatible(tmp_path):
    a = make_app(tmp_path, extra_top="state_sync:\n  repo: /x\n")
    assert a.config.state_sync.type == "git"


def test_file_type_config(tmp_path):
    a = make_app(tmp_path, extra_top=f"state_sync:\n  type: file\n  path: {tmp_path}/s.yaml\n")
    src = build_source(a.config.state_sync)
    assert isinstance(src, FileSource) and src.path == tmp_path / "s.yaml"


@pytest.mark.parametrize("bad", [
    "state_sync: {type: nope, path: /x}\n",
    "state_sync: {type: 3, path: /x}\n",
    "state_sync: {type: file}\n",
    "state_sync: {type: file, path: 5}\n",
    "state_sync: {type: file, path: ''}\n",
])
def test_invalid_file_or_unknown_type(tmp_path, bad):
    with pytest.raises(ConfigError):
        make_app(tmp_path, extra_top=bad)


def test_unknown_type_error_lists_valid_types(tmp_path):
    with pytest.raises(ConfigError, match="file") as exc:
        make_app(tmp_path, extra_top="state_sync: {type: ftp, path: /x}\n")
    assert "git" in str(exc.value) and "ftp" in str(exc.value)


def test_hueman_flow_over_file_backend(tmp_path):
    shared = tmp_path / "shared"
    shared.mkdir()
    cfg = f"state_sync:\n  type: file\n  path: {shared}/s.yaml\n"
    a = make_app(tmp_path, extra_top=cfg, targets={"k": {}})
    assert a.set_theme("one") == []
    assert FileSource(shared / "s.yaml").read().revision == 1
    assert a.sync() == (0, "in-sync")
    FileSource(shared / "s.yaml").write(State("one", 5))
    assert a.sync() == (0, "applied")
    assert a.local_revision() == 5


def test_orchestrator_depends_only_on_the_interface():
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent / "hueman" / "cli.py").read_text()
    assert "GitBranch" not in src and "FileSource" not in src
