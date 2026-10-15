import logging

from engine.colors import contrast_text, is_dark
from hueman import Hueman
from engine.config import HuemanConfig


def test_color_filters_classify_light_and_dark_values():
    assert contrast_text("#000000") == "#f5f5f5"
    assert contrast_text("#ffffff") == "#1a1a1a"
    assert is_dark("#000000") is True
    assert is_dark("#ffffff") is False


def test_set_theme_persists_state_and_runs_post_apply_after_targets(tmp_path, monkeypatch):
    palette_file = tmp_path / "palette.yaml"
    palette_file.write_text("name: demo\n")
    config_file = tmp_path / "hueman.yaml"
    config_file.write_text(
        f"state_file: {tmp_path / 'state'}\n"
        f"palette_dirs: [{tmp_path}]\n"
        "targets: {}\n"
        "post_apply: ['echo done']\n"
    )
    config = HuemanConfig(config_file)
    app = Hueman(config)
    calls = []
    monkeypatch.setattr("hueman.run_post_apply", lambda commands, logger: calls.append(commands))

    app.set_theme("palette")

    assert config.state_file.read_text() == "palette\n"
    assert calls == [["echo done"]]


def test_set_theme_dry_run_does_not_persist_state(tmp_path):
    palette_file = tmp_path / "palette.yaml"
    palette_file.write_text("name: demo\n")
    config_file = tmp_path / "hueman.yaml"
    config_file.write_text(
        f"state_file: {tmp_path / 'state'}\n"
        f"palette_dirs: [{tmp_path}]\n"
        "targets: {}\n"
    )

    app = Hueman(HuemanConfig(config_file))
    app.set_theme("palette", dry_run=True)

    assert not (tmp_path / "state").exists()
