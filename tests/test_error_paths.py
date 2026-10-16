import logging
import sys

import pytest

import hueman
from engine.config import ConfigError, HuemanConfig
from engine.palettes import PaletteLoader

LOG = logging.getLogger("hueman-tests")


@pytest.mark.parametrize("body", ["a: [\n", "- just\n- a list\n", "", "plain scalar\n"])
def test_invalid_palette_exits_one_with_error_and_no_state(tmp_path, caplog, body):
    (tmp_path / "bad.yaml").write_text(body)
    loader = PaletteLoader(tmp_path, [], LOG)
    with pytest.raises(SystemExit) as exc:
        loader.load("bad")
    assert exc.value.code == 1
    assert "bad" in caplog.text


@pytest.mark.parametrize("body", ["a: [\n", "- x\n", "plain\n", "targets: [1]\n"])
def test_invalid_config_raises_config_error(tmp_path, body):
    cfg = tmp_path / "c.yaml"
    cfg.write_text(body)
    with pytest.raises(ConfigError):
        HuemanConfig(cfg)


def test_empty_config_is_valid(tmp_path, isolated_home):
    cfg = tmp_path / "c.yaml"
    cfg.write_text("")
    assert HuemanConfig(cfg).targets == []


def test_invalid_patch_spec_raises_config_error(tmp_path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text("targets:\n  t:\n    mode: patch\n    patch: {bogus_key: 1}\n")
    with pytest.raises(ConfigError):
        HuemanConfig(cfg)


def test_cli_invalid_config_exits_one_without_traceback(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / "c.yaml"
    cfg.write_text("a: [\n")
    monkeypatch.setattr(sys, "argv", ["hueman", "--config", str(cfg), "list"])
    with pytest.raises(SystemExit) as exc:
        hueman.main()
    assert exc.value.code == 1
    assert str(cfg) in capsys.readouterr().err


def test_cli_set_with_broken_palette_keeps_previous_state(tmp_path, monkeypatch):
    (tmp_path / "ok.yaml").write_text("n: 1\n")
    (tmp_path / "broken.yaml").write_text("a: [\n")
    state = tmp_path / "state"
    cfg = tmp_path / "c.yaml"
    cfg.write_text(f"state_file: {state}\npalette_dirs: [{tmp_path}]\ntargets: {{}}\n")
    for name, code in (("ok", None), ("broken", 1)):
        monkeypatch.setattr(sys, "argv", ["hueman", "--config", str(cfg), "set", name])
        if code:
            with pytest.raises(SystemExit) as exc:
                hueman.main()
            assert exc.value.code == code
        else:
            hueman.main()
    assert state.read_text() == "ok\n"
