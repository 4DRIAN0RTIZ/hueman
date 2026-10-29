from pathlib import Path

import pytest

from hueman.engine.config import HuemanConfig
from hueman.engine.palettes import PaletteLoader


class NullLogger:
    def __getattr__(self, _name):
        return lambda *args, **kwargs: None


def test_resolve_path_precedence(tmp_path, monkeypatch, isolated_home):
    explicit = tmp_path / "explicit.yaml"
    env = tmp_path / "env.yaml"
    explicit.touch()
    env.touch()
    monkeypatch.setenv("HUEMAN_CONFIG", str(env))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "hueman.config.yaml").touch()

    assert HuemanConfig.resolve_path(explicit) == explicit
    assert HuemanConfig.resolve_path(None) == env

    monkeypatch.delenv("HUEMAN_CONFIG")
    # the current directory is never searched: falls to the user config path
    assert HuemanConfig.resolve_path(None) == isolated_home / ".config/hueman/config.yaml"


def test_cwd_config_is_ignored(tmp_path, monkeypatch, isolated_home, capsys):
    import sys

    import hueman.cli as hueman
    marker = tmp_path / "pwned"
    (tmp_path / "hueman.config.yaml").write_text(f"post_apply:\n  - touch {marker}\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["hueman", "set", "nord"])
    with pytest.raises(SystemExit) as exc:
        hueman.main()
    assert exc.value.code == 1
    assert "Config no encontrada" in capsys.readouterr().err
    assert not marker.exists()


def test_explicit_and_env_beat_cwd_and_user_config(tmp_path, monkeypatch, isolated_home):
    (tmp_path / "hueman.config.yaml").touch()
    user = isolated_home / ".config/hueman/config.yaml"
    user.parent.mkdir(parents=True)
    user.touch()
    monkeypatch.chdir(tmp_path)
    env = tmp_path / "env.yaml"
    monkeypatch.setenv("HUEMAN_CONFIG", str(env))
    assert HuemanConfig.resolve_path(None) == env
    assert HuemanConfig.resolve_path(str(tmp_path / "x.yaml")) == tmp_path / "x.yaml"
    monkeypatch.delenv("HUEMAN_CONFIG")
    assert HuemanConfig.resolve_path(None) == user


def test_palette_custom_precedes_packaged(tmp_path):
    packaged = tmp_path / "packaged"
    custom = tmp_path / "custom"
    packaged.mkdir()
    custom.mkdir()
    (packaged / "shared.yaml").write_text("name: packaged\n")
    (packaged / "only-packaged.yaml").write_text("name: packaged-only\n")
    (custom / "shared.yaml").write_text("name: custom\n")
    (custom / "only-custom.yaml").write_text("name: custom-only\n")

    loader = PaletteLoader(packaged, [custom], NullLogger())

    assert loader.list_palettes() == ["only-custom", "only-packaged", "shared"]
    assert loader.load("shared")["name"] == "custom"


def test_missing_palette_exits_with_available_names(tmp_path, caplog):
    packaged = tmp_path / "packaged"
    packaged.mkdir()
    (packaged / "solar.yaml").write_text("name: solar\n")
    loader = PaletteLoader(packaged, [], NullLogger())

    with pytest.raises(SystemExit) as error:
        loader.load("missing")

    assert error.value.code == 1
    assert "solar" in caplog.text or loader.list_palettes() == ["solar"]


def test_config_loads_paths_and_targets(tmp_path):
    config_path = tmp_path / "hueman.config.yaml"
    config_path.write_text(
        "state_file: state/current\n"
        "palette_dirs: [palettes]\n"
        "targets:\n"
        "  demo:\n"
        "    outputs: [out/demo.txt]\n"
    )

    config = HuemanConfig(config_path)

    assert config.state_file == Path("state/current")
    assert config.palette_dirs == [Path("palettes")]
    assert config.targets[0].name == "demo"
    assert config.targets[0].outputs == [Path("out/demo.txt")]
