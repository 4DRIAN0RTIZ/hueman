"""Palette names are validated before any filesystem access (CLI and sync)."""

import logging
import shutil
import sys

import pytest

import hueman.cli as hueman
from hueman.engine.palettes import PaletteLoader, is_valid_palette_name
from hueman.engine.statesource import FileSource, State, parse_state
from hueman.resources import packaged_palettes_dir
from test_reload_exit_codes import make_app

LOG = logging.getLogger("hueman-tests")

BAD = ["/abs/evil", "../x", "a/../b", "a..b", "a/b", "bad name", "bad\nname", "name\n", "",
       ".hidden", "-dash", "tab\tname", "a\x00b", "ñandu"]


def packaged_names():
    return PaletteLoader(packaged_palettes_dir(), [], LOG).list_palettes()


@pytest.mark.parametrize("name", packaged_names())
def test_every_packaged_palette_name_is_valid_and_loads(name):
    assert is_valid_palette_name(name)
    assert isinstance(PaletteLoader(packaged_palettes_dir(), [], LOG).load(name), dict)


@pytest.mark.parametrize("name", ["nord", "a", "A1", "rose-pine.dawn", "x_y", "v1.2"])
def test_valid_names(name):
    assert is_valid_palette_name(name)


@pytest.mark.parametrize("name", BAD)
def test_invalid_names(name):
    assert not is_valid_palette_name(name)


@pytest.mark.parametrize("name", BAD)
def test_load_rejects_invalid_name_before_touching_disk(tmp_path, caplog, name):
    outside = tmp_path / "evil.yaml"
    outside.write_text("kitty: {c: red}\n")
    pal = tmp_path / "pal"
    pal.mkdir()
    loader = PaletteLoader(tmp_path / "packaged", [pal], LOG)
    if name == "/abs/evil":
        name = str(tmp_path / "evil")
    with pytest.raises(SystemExit) as exc:
        loader.load(name)
    assert exc.value.code == 1
    assert "Nombre de paleta invalido" in caplog.text


def test_cli_set_bad_name_exits_one_cleanly_and_writes_nothing(tmp_path, monkeypatch, capsys):
    app = make_app(tmp_path, targets={"k": {}})
    evil = tmp_path / "evil.yaml"
    evil.write_text("kitty: {c: red}\n")
    cfg = tmp_path / "hueman.yaml"
    monkeypatch.setattr(sys, "argv", ["hueman", "--config", str(cfg), "set", str(tmp_path / "evil")])
    with pytest.raises(SystemExit) as exc:
        hueman.main()
    assert exc.value.code == 1
    assert not (tmp_path / "k.out").exists()
    assert not (tmp_path / "state").exists()
    assert "Traceback" not in capsys.readouterr().err


@pytest.mark.parametrize("name", ["/abs/evil", "../x", "a/b", "a b", "a\nb", ""])
def test_parse_state_rejects_invalid_palette(name):
    from hueman.engine.statesource import dump_state
    assert parse_state(dump_state(State(name, 3))) is None


def test_parse_state_accepts_valid_palette():
    assert parse_state("palette: nord\nrevision: 2\n") == State("nord", 2)


def test_file_source_ignores_state_with_bad_palette(tmp_path):
    f = tmp_path / "s.yaml"
    f.write_text("palette: ../x\nrevision: 9\n")
    assert FileSource(f).read() is None


def file_app(tmp_path, palette_in_state, revision=4):
    state = tmp_path / "shared.yaml"
    state.write_text(f"palette: {palette_in_state}\nrevision: {revision}\n")
    return make_app(tmp_path, extra_top=f"state_sync:\n  type: file\n  path: {state}\n",
                    targets={"k": {}})


def test_sync_remote_palette_missing_locally_is_soft(tmp_path, caplog):
    a = file_app(tmp_path, "not-here")
    assert a.sync() == (0, "unknown-palette")
    assert a.local_revision() is None
    assert not (tmp_path / "k.out").exists()
    assert not (tmp_path / "state").exists()
    assert "not-here" in caplog.text


def test_sync_remote_palette_invalid_name_is_ignored(tmp_path):
    a = file_app(tmp_path, "../x")
    assert a.sync() == (0, "no-remote-state")
    assert a.local_revision() is None
    assert not (tmp_path / "k.out").exists()


def test_sync_valid_remote_palette_still_applies(tmp_path):
    a = file_app(tmp_path, "one")
    assert a.sync() == (0, "applied")
    assert a.local_revision() == 4
