"""`hueman init`: write the packaged example config to the default path."""
import subprocess
import sys
from pathlib import Path

import pytest

import hueman.cli as cli
from hueman.resources import packaged_example_config

ROOT = Path(__file__).resolve().parent.parent


def run_main(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["hueman", *argv])
    try:
        cli.main()
    except SystemExit as exc:
        return exc.code or 0
    return 0


def test_example_config_is_packaged():
    path = packaged_example_config()
    assert path.is_file()
    assert path.resolve().parent == Path(cli.__file__).resolve().parent / "data"


def test_init_writes_default_path_without_config(isolated_home, monkeypatch, capsys):
    target = isolated_home / ".config" / "hueman" / "config.yaml"
    assert not target.exists()
    assert run_main(monkeypatch, "init") == 0
    assert target.read_text() == packaged_example_config().read_text()
    assert str(target) in capsys.readouterr().out


def test_init_honors_explicit_config_path(tmp_path, monkeypatch, capsys):
    target = tmp_path / "sub" / "mine.yaml"
    run_main(monkeypatch, "--config", str(target), "init")
    assert target.read_text() == packaged_example_config().read_text()
    assert str(target) in capsys.readouterr().out


def test_init_refuses_to_overwrite(tmp_path, monkeypatch, capsys):
    target = tmp_path / "c.yaml"
    target.write_text("mine: true\n")
    code = run_main(monkeypatch, "--config", str(target), "init")
    assert code == 1
    assert target.read_text() == "mine: true\n"
    assert "--force" in capsys.readouterr().err


def test_init_force_overwrites(tmp_path, monkeypatch):
    target = tmp_path / "c.yaml"
    target.write_text("mine: true\n")
    run_main(monkeypatch, "--config", str(target), "init", "--force")
    assert target.read_text() == packaged_example_config().read_text()


def test_written_config_is_loadable(tmp_path, monkeypatch):
    target = tmp_path / "c.yaml"
    run_main(monkeypatch, "--config", str(target), "init")
    from hueman.engine.config import HuemanConfig
    assert HuemanConfig(target).targets


def test_missing_config_error_hints_init_and_docs(tmp_path, monkeypatch, capsys):
    code = run_main(monkeypatch, "--config", str(tmp_path / "nope.yaml"), "set", "gruvbox")
    err = capsys.readouterr().err
    assert code == 1
    assert "Config no encontrada" in err
    assert "hueman init" in err
    assert "https://hueman.cuevaneander.tech" in err


def test_list_works_without_config(monkeypatch, capsys):
    code = run_main(monkeypatch, "list")
    assert code == 0
    assert "gruvbox" in capsys.readouterr().out.split()


def test_init_in_subprocess_with_no_config(isolated_home):
    env = {"HOME": str(isolated_home), "PATH": "/usr/bin:/bin"}
    r = subprocess.run([sys.executable, "-m", "hueman", "init"],
                       capture_output=True, text=True, env=env, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    assert (isolated_home / ".config" / "hueman" / "config.yaml").is_file()
