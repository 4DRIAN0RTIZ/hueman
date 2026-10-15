"""Smoke test: every target of a real user config must resolve to a packaged
template and render with a packaged palette. Config path via HUEMAN_REAL_CONFIG;
skipped when absent. template_dirs are ignored on purpose: only packaged
templates count."""

import logging
import os
from pathlib import Path

import pytest

from engine.config import HuemanConfig
from engine.palettes import PaletteLoader
from engine.render import make_jinja_env, render_template

ROOT = Path(__file__).resolve().parent.parent
REAL_CONFIG = Path(
    os.environ.get("HUEMAN_REAL_CONFIG", "~/MyDotFiles/theme/themectl.config.yaml")
).expanduser()
PALETTE = "synthwave"

if REAL_CONFIG.exists():
    _config = HuemanConfig(REAL_CONFIG)
    _targets = _config.targets
else:
    _targets = []


@pytest.mark.skipif(not REAL_CONFIG.exists(), reason="real config not found")
def test_real_config_has_targets():
    assert _targets


@pytest.mark.parametrize("target", _targets, ids=lambda t: t.name)
def test_real_target_template_exists_and_renders(target):
    packaged = ROOT / "templates"
    if target.template is None:
        assert target.patch and target.patch.strategy == "json_scheme_upsert"
        palette = PaletteLoader(ROOT / "palettes", [], logging.getLogger("t")).load(PALETTE)
        assert target.patch.palette_section in palette
        return
    assert (packaged / target.template).is_file(), f"missing template {target.template}"

    palette = PaletteLoader(ROOT / "palettes", [], logging.getLogger("t")).load(PALETTE)
    env = make_jinja_env([], packaged, target.jinja_delimiters)
    out = render_template(env, target, PALETTE, palette)

    markers = ["{{", "{%"]
    if target.jinja_delimiters:
        markers = [target.jinja_delimiters[0]]
    for m in markers:
        assert m not in out, f"unrendered {m!r} in {target.name}"
