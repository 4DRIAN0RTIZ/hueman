import os
import sys

import pytest

import hueman.cli as hueman
from hueman.engine.config import ConfigError, HuemanConfig

TARGET = """
targets:
  t:
    template: x.j2
    outputs: ["{out}"]
"""


def write_cfg(tmp_path, body):
    cfg = tmp_path / "c.yaml"
    cfg.write_text(body)
    return cfg


def base(tmp_path):
    return TARGET.format(out=tmp_path / "out.txt")


def load_error(tmp_path, body):
    with pytest.raises(ConfigError) as exc:
        HuemanConfig(write_cfg(tmp_path, body))
    return str(exc.value)


def cli_fails_cleanly(tmp_path, monkeypatch, capsys, body):
    cfg = write_cfg(tmp_path, body)
    monkeypatch.setattr(sys, "argv", ["hueman", "--config", str(cfg), "set", "gruvbox", "--dry-run"])
    with pytest.raises(SystemExit) as exit_info:
        hueman.main()
    err = capsys.readouterr().err
    assert exit_info.value.code == 1
    assert err.startswith("Config invalida:")
    assert "Traceback" not in err
    assert len(err.strip().splitlines()) == 1


# --- logging.level ---------------------------------------------------------

def test_logging_level_unknown_is_config_error(tmp_path):
    msg = load_error(tmp_path, "logging: {level: LOUD}\n" + base(tmp_path))
    assert "logging.level" in msg and "LOUD" in msg


def test_logging_level_unknown_cli_exits_1(tmp_path, monkeypatch, capsys):
    cli_fails_cleanly(tmp_path, monkeypatch, capsys, "logging: {level: LOUD}\n" + base(tmp_path))


def test_logging_level_valid_is_case_insensitive(tmp_path):
    HuemanConfig(write_cfg(tmp_path, "logging: {level: debug}\n" + base(tmp_path)))


def test_logging_level_must_be_string(tmp_path):
    assert "logging.level" in load_error(tmp_path, "logging: {level: 5}\n" + base(tmp_path))


# --- logging (shape) and logging.file ---------------------------------------

def test_logging_must_be_mapping(tmp_path):
    assert "logging" in load_error(tmp_path, "logging: [a]\n" + base(tmp_path))


def test_logging_file_missing_parent_is_config_error(tmp_path):
    missing = tmp_path / "nope" / "h.log"
    msg = load_error(tmp_path, f"logging: {{file: {missing}}}\n" + base(tmp_path))
    assert "logging.file" in msg and str(missing.parent) in msg


def test_logging_file_missing_parent_cli_exits_1(tmp_path, monkeypatch, capsys):
    missing = tmp_path / "nope" / "h.log"
    cli_fails_cleanly(tmp_path, monkeypatch, capsys, f"logging: {{file: {missing}}}\n" + base(tmp_path))


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions")
def test_logging_file_unwritable_parent_is_config_error(tmp_path):
    ro = tmp_path / "ro"
    ro.mkdir()
    ro.chmod(0o500)
    try:
        msg = load_error(tmp_path, f"logging: {{file: {ro / 'h.log'}}}\n" + base(tmp_path))
    finally:
        ro.chmod(0o700)
    assert "logging.file" in msg


# --- mode / patch ----------------------------------------------------------

def test_mode_unknown_is_config_error(tmp_path):
    body = f"targets:\n  t:\n    mode: bogus\n    template: x.j2\n    outputs: ['{tmp_path}/o']\n"
    msg = load_error(tmp_path, body)
    assert "mode" in msg and "bogus" in msg


def test_mode_unknown_cli_exits_1(tmp_path, monkeypatch, capsys):
    body = f"targets:\n  t:\n    mode: bogus\n    template: x.j2\n    outputs: ['{tmp_path}/o']\n"
    cli_fails_cleanly(tmp_path, monkeypatch, capsys, body)


def test_patch_mode_without_patch_section_is_config_error(tmp_path):
    body = f"targets:\n  t:\n    mode: patch\n    template: x.j2\n    outputs: ['{tmp_path}/o']\n"
    msg = load_error(tmp_path, body)
    assert "patch" in msg


def test_patch_mode_without_patch_section_cli_exits_1(tmp_path, monkeypatch, capsys):
    body = f"targets:\n  t:\n    mode: patch\n    template: x.j2\n    outputs: ['{tmp_path}/o']\n"
    cli_fails_cleanly(tmp_path, monkeypatch, capsys, body)


def test_patch_must_be_mapping(tmp_path):
    body = f"targets:\n  t:\n    mode: patch\n    patch: oops\n    outputs: ['{tmp_path}/o']\n"
    assert "patch" in load_error(tmp_path, body)


# --- post_apply ------------------------------------------------------------

def test_post_apply_string_is_rejected(tmp_path):
    msg = load_error(tmp_path, "post_apply: 'echo hi'\n" + base(tmp_path))
    assert "post_apply" in msg and "lista" in msg


def test_post_apply_string_cli_exits_1(tmp_path, monkeypatch, capsys):
    cli_fails_cleanly(tmp_path, monkeypatch, capsys, "post_apply: 'echo hi'\n" + base(tmp_path))


def test_post_apply_items_must_be_strings(tmp_path):
    assert "post_apply" in load_error(tmp_path, "post_apply: [echo, 3]\n" + base(tmp_path))


def test_post_apply_null_means_empty(tmp_path):
    assert HuemanConfig(write_cfg(tmp_path, "post_apply:\n" + base(tmp_path))).post_apply == []


# --- outputs ---------------------------------------------------------------

def test_outputs_string_is_rejected(tmp_path):
    body = f"targets:\n  t:\n    template: x.j2\n    outputs: '{tmp_path}/o'\n"
    msg = load_error(tmp_path, body)
    assert "outputs" in msg and "lista" in msg


def test_outputs_string_cli_exits_1(tmp_path, monkeypatch, capsys):
    body = f"targets:\n  t:\n    template: x.j2\n    outputs: '{tmp_path}/o'\n"
    cli_fails_cleanly(tmp_path, monkeypatch, capsys, body)


def test_outputs_items_must_be_strings(tmp_path):
    body = "targets:\n  t:\n    template: x.j2\n    outputs: [1, [2]]\n"
    assert "outputs" in load_error(tmp_path, body)
