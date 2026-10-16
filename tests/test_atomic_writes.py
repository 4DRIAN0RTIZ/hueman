import json
import logging
import os
import stat

import pytest

import hueman
from engine.fsutil import atomic_write_text
from engine.render import TargetRenderError, make_jinja_env, render_target
from engine.targets import PatchSpec, Target

LOG = logging.getLogger("hueman-tests")


def boom(*args, **kwargs):
    raise OSError("simulated failure")


def leftovers(directory, expected):
    return sorted(p.name for p in directory.iterdir() if p.name not in expected)


def test_atomic_write_creates_file_with_content(tmp_path):
    out = tmp_path / "sub" / "f.txt"
    atomic_write_text(out, "hi\n")
    assert out.read_text() == "hi\n"
    assert leftovers(out.parent, {"f.txt"}) == []


def test_atomic_write_preserves_existing_mode(tmp_path):
    out = tmp_path / "f"
    out.write_text("old")
    out.chmod(0o640)
    atomic_write_text(out, "new")
    assert stat.S_IMODE(out.stat().st_mode) == 0o640


def test_atomic_write_make_executable_adds_exec_bits_keeping_mode(tmp_path):
    out = tmp_path / "f"
    out.write_text("old")
    out.chmod(0o640)
    atomic_write_text(out, "new", make_executable=True)
    assert stat.S_IMODE(out.stat().st_mode) == 0o751


def test_atomic_write_new_file_uses_umask_default(tmp_path):
    old = os.umask(0o022)
    try:
        out = tmp_path / "f"
        atomic_write_text(out, "x")
    finally:
        os.umask(old)
    assert stat.S_IMODE(out.stat().st_mode) == 0o644


def test_failed_replace_keeps_original_and_cleans_temp(tmp_path, monkeypatch):
    out = tmp_path / "f"
    out.write_text("original")
    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        atomic_write_text(out, "new")
    assert out.read_text() == "original"
    assert leftovers(tmp_path, {"f"}) == []


def test_failed_write_keeps_original_and_cleans_temp(tmp_path, monkeypatch):
    out = tmp_path / "f"
    out.write_text("original")
    monkeypatch.setattr(os, "fsync", boom)
    with pytest.raises(OSError):
        atomic_write_text(out, "new")
    assert out.read_text() == "original"
    assert leftovers(tmp_path, {"f"}) == []


def env_with(tmp_path, **templates):
    tdir = tmp_path / "templates"
    tdir.mkdir(exist_ok=True)
    for name, body in templates.items():
        (tdir / name).write_text(body)
    return make_jinja_env([], tdir)


def test_overwrite_failure_leaves_original(tmp_path, monkeypatch):
    env = env_with(tmp_path, **{"t.j2": "new\n"})
    out = tmp_path / "o" / "x.conf"
    out.parent.mkdir()
    out.write_text("old\n")
    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(TargetRenderError):
        render_target(env, Target(name="t", template="t.j2", outputs=[out]), "n", {}, False, LOG)
    assert out.read_text() == "old\n"
    assert leftovers(out.parent, {"x.conf"}) == []


def test_patch_failure_leaves_original(tmp_path, monkeypatch):
    env = env_with(tmp_path, **{"t.j2": "body\n"})
    out = tmp_path / "rc"
    out.write_text("keep\n")
    patch = PatchSpec(marker_begin="# B", marker_end="# E")
    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(TargetRenderError):
        render_target(env, Target(name="t", template="t.j2", mode="patch", patch=patch,
                                  outputs=[out]), "n", {}, False, LOG)
    assert out.read_text() == "keep\n"
    assert leftovers(tmp_path, {"rc", "templates"}) == []


def json_target(out):
    return Target(name="t", mode="patch", outputs=[out],
                  patch=PatchSpec(strategy="json_scheme_upsert", palette_section="kitty"))


KITTY = {"background": "#0", "foreground": "#f", "cursor": "#c", "selection_background": "#s",
         **{f"color{i}": f"#{i}" for i in range(16)}}


def test_json_upsert_failure_leaves_original(tmp_path, monkeypatch):
    out = tmp_path / "settings.json"
    out.write_text('{"schemes": []}\n')
    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(TargetRenderError):
        render_target(None, json_target(out), "n", {"kitty": KITTY}, False, LOG)
    assert out.read_text() == '{"schemes": []}\n'
    assert leftovers(tmp_path, {"settings.json"}) == []


def test_json_upsert_invalid_json_is_clean_error(tmp_path):
    out = tmp_path / "settings.json"
    out.write_text("{not json")
    with pytest.raises(TargetRenderError):
        render_target(None, json_target(out), "n", {"kitty": KITTY}, False, LOG)
    assert out.read_text() == "{not json"


def test_missing_template_is_clean_error(tmp_path):
    env = env_with(tmp_path)
    out = tmp_path / "o"
    with pytest.raises(TargetRenderError):
        render_target(env, Target(name="t", template="nope.j2", outputs=[out]), "n", {}, False, LOG)
    assert not out.exists()


def write_config(tmp_path, template):
    pdir = tmp_path / "palettes"
    pdir.mkdir()
    (pdir / "nord.yaml").write_text("name: nord\n")
    cfg = tmp_path / "hueman.config.yaml"
    cfg.write_text(
        f"state_file: {tmp_path / 'state'}\n"
        f"palette_dirs: [{pdir}]\n"
        "targets:\n"
        "  t:\n"
        f"    template: {template}\n"
        f"    outputs: [{tmp_path / 'out'}]\n"
    )
    return cfg


def test_state_write_failure_keeps_previous_state(tmp_path, monkeypatch):
    cfg = write_config(tmp_path, "nope.j2")
    state = tmp_path / "state"
    state.write_text("old\n")
    h = hueman.Hueman(hueman.HuemanConfig(cfg))
    h.config.targets = []
    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        h.set_theme("nord")
    assert state.read_text() == "old\n"
    assert leftovers(tmp_path, {"state", "palettes", "hueman.config.yaml"}) == []


def test_cli_missing_template_exits_nonzero(tmp_path, monkeypatch, capsys):
    cfg = write_config(tmp_path, "nope.j2")
    monkeypatch.setattr("sys.argv", ["hueman", "--config", str(cfg), "set", "nord"])
    with pytest.raises(SystemExit) as exc:
        hueman.main()
    assert exc.value.code == 1
