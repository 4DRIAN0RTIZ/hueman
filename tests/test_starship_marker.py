"""The starship block header is a functional marker matched by marker_regex:
files carrying the OLD (theme_manager.py) or NEW (hueman) header must both be
replaced in place, never duplicated."""

import logging
from pathlib import Path

import yaml

from hueman.engine.palettes import PaletteLoader
from hueman.engine.render import make_jinja_env, render_target
from hueman.engine.targets import Target

ROOT = Path(__file__).resolve().parent.parent
LOG = logging.getLogger("t")


def _target(output):
    cfg = yaml.safe_load((ROOT / "hueman" / "data" / "hueman.config.example.yaml").read_text())
    data = dict(cfg["targets"]["starship"], outputs=[str(output)])
    return Target.from_dict("starship", data)


def _file(header):
    return (
        'add_newline = false\npalette = "dotfiles"\n\n[character]\nx = 1\n\n'
        f"{header}\n[palettes.dotfiles]\nbackground = \"#000000\"\nprimary = \"#111111\"\n\n"
        "[git_branch]\nstyle = \"bold green\"\n"
    )


def _run(tmp_path, header):
    out = tmp_path / "starship.toml"
    out.write_text(_file(header))
    palette = PaletteLoader(ROOT / "hueman" / "palettes", [], LOG).load("synthwave")
    env = make_jinja_env([], ROOT / "hueman" / "templates")
    target = _target(out)
    render_target(env, target, "synthwave", palette, False, LOG)
    first = out.read_text()
    render_target(env, target, "synthwave", palette, False, LOG)
    return first, out.read_text()


def test_old_header_is_replaced_in_place_without_duplicate(tmp_path):
    first, second = _run(tmp_path, "# --- Bloque gestionado por theme_manager.py: no editar a mano ---")
    assert first == second
    assert first.count("[palettes.dotfiles]") == 1
    assert "theme_manager.py" not in first
    assert "[git_branch]" in first and first.index("[character]") < first.index("[palettes.dotfiles]")


def test_new_header_is_replaced_in_place_without_duplicate(tmp_path):
    first, second = _run(tmp_path, "# --- Bloque gestionado por hueman: no editar a mano ---")
    assert first == second
    assert first.count("[palettes.dotfiles]") == 1
    assert first.count("Bloque gestionado por") == 1
    assert "[git_branch]" in first
