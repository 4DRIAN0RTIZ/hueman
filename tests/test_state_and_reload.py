import logging
import subprocess
import sys
from pathlib import Path

import pytest

from engine.config import HuemanConfig
from engine.reload import run_post_apply, run_reload
from hueman import Hueman

ROOT = Path(__file__).resolve().parent.parent


def make_app(tmp_path, extra="", palettes=("one", "two")):
    pal = tmp_path / "pal"
    pal.mkdir(exist_ok=True)
    for p in palettes:
        (pal / f"{p}.yaml").write_text(f"name: {p}\n")
    cfg = tmp_path / "hueman.yaml"
    cfg.write_text(
        f"state_file: {tmp_path / 'deep' / 'nested' / 'current'}\n"
        f"palette_dirs: [{pal}]\n" + (extra or "targets: {}\n")
    )
    return Hueman(HuemanConfig(cfg))


def test_state_file_parent_dirs_are_created(tmp_path):
    app = make_app(tmp_path)
    app.set_theme("one")
    assert app.config.state_file.read_text() == "one\n"


def test_current_theme_none_without_state_and_roundtrips(tmp_path):
    app = make_app(tmp_path)
    assert app.current_theme() is None
    app.set_theme("one")
    assert app.current_theme() == "one"
    app.set_theme("two")
    assert app.current_theme() == "two"


def test_unknown_palette_does_not_touch_state(tmp_path):
    app = make_app(tmp_path)
    app.set_theme("one")
    with pytest.raises(SystemExit) as exc:
        app.set_theme("nope")
    assert exc.value.code == 1
    assert app.current_theme() == "one"


def test_status_reports_active_theme_palettes_and_target_counts(tmp_path, capsys):
    present = tmp_path / "present.out"
    present.write_text("x")
    app = make_app(
        tmp_path,
        f"targets:\n  t:\n    template: missing.j2\n    outputs: ['{present}', '{tmp_path}/absent.out']\n",
    )
    app.status()
    out = capsys.readouterr().out
    assert "Tema activo: (ninguno)" in out
    assert "one" in out and "two" in out
    assert "1/2 outputs" in out


def test_dry_run_never_writes_state(tmp_path):
    app = make_app(tmp_path)
    app.set_theme("one", dry_run=True)
    assert not app.config.state_file.exists()


def test_run_reload_failure_is_best_effort(tmp_path, caplog):
    marker = tmp_path / "ran"
    # A failing command must not raise, and later commands must still run.
    run_reload("exit 3", logging.getLogger("hueman-tests"))
    run_post_apply(["exit 5", f"touch {marker}"], logging.getLogger("hueman-tests"))
    assert marker.exists()


def test_run_reload_empty_command_is_noop(monkeypatch):
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: calls.append(a))
    run_reload("", logging.getLogger("hueman-tests"))
    run_reload(None, logging.getLogger("hueman-tests"))
    assert calls == []


def test_failing_reload_does_not_abort_state_or_post_apply(tmp_path):
    marker = tmp_path / "post"
    out = tmp_path / "a.out"
    (tmp_path / "tpl").mkdir()
    (tmp_path / "tpl" / "a.j2").write_text("hi {{ theme_name }}\n")
    app = make_app(
        tmp_path,
        f"template_dirs: ['{tmp_path / 'tpl'}']\n"
        f"post_apply: ['touch {marker}']\n"
        f"targets:\n  a:\n    template: a.j2\n    outputs: ['{out}']\n    reload: 'exit 9'\n",
    )
    assert app.set_theme("one") == []
    assert out.read_text() == "hi one\n"
    assert marker.exists()
    assert app.current_theme() == "one"


def test_cli_end_to_end_in_subprocess_uses_only_temp_paths(tmp_path, isolated_home):
    app = make_app(tmp_path)
    env = {"HOME": str(isolated_home), "PATH": "/usr/bin:/bin"}
    cfg = str(app.config.path)
    for args, rc in ((["set", "one"], 0), (["set", "nope"], 1), (["status"], 0), (["list"], 0)):
        r = subprocess.run(
            [sys.executable, str(ROOT / "hueman.py"), "--config", cfg, *args],
            capture_output=True, text=True, env=env,
        )
        assert r.returncode == rc, r.stderr
    assert app.current_theme() == "one"
    assert list(isolated_home.iterdir()) == []


def test_cli_missing_config_exits_one(tmp_path, monkeypatch, capsys):
    import hueman
    monkeypatch.setattr(sys, "argv", ["hueman", "--config", str(tmp_path / "nope.yaml"), "list"])
    with pytest.raises(SystemExit) as exc:
        hueman.main()
    assert exc.value.code == 1
    assert "Config no encontrada" in capsys.readouterr().err
