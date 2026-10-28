import logging
from pathlib import Path

import yaml

from engine.render import make_jinja_env, render_target
from engine.targets import Target

ROOT = Path(__file__).resolve().parent.parent
KEYS = ["foreground", "background", "cursor"] + [f"color{i}" for i in range(16)]
logger = logging.getLogger("hueman-tests")


def _render(tmp_path, palette_name="catppuccin-mocha"):
    palette = yaml.safe_load((ROOT / "palettes" / f"{palette_name}.yaml").read_text())
    env = make_jinja_env([], ROOT / "templates")
    out = tmp_path / ".termux" / "colors.properties"
    target = Target(
        name="termux", template="termux_colors.properties.j2",
        palette_key="kitty", outputs=[out],
    )
    assert render_target(env, target, palette_name, palette, False, logger) is True
    return out.read_text(), palette["kitty"]


def _parse(text):
    return dict(
        line.split("=", 1) for line in text.splitlines()
        if line and not line.startswith("#")
    )


def test_termux_template_has_all_19_keys_with_palette_values(tmp_path):
    text, kitty = _render(tmp_path)
    props = _parse(text)

    assert sorted(props) == sorted(KEYS)
    assert len(props) == 19
    assert all(props[k] == kitty[k] for k in KEYS)


def test_termux_template_exact_lines_and_format(tmp_path):
    text, _ = _render(tmp_path)
    lines = text.splitlines()

    assert lines[0].startswith("#")
    assert "foreground=#cdd6f4" in lines
    assert "background=#1e1e2e" in lines
    assert "cursor=#f5e0dc" in lines
    assert "color1=#f38ba8" in lines
    assert "color15=#a6adc8" in lines
    assert '"' not in text and " = " not in text and text.endswith("\n")


def test_termux_template_is_deterministic(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    a, _ = _render(tmp_path / "a")
    b, _ = _render(tmp_path / "b")

    assert a == b
