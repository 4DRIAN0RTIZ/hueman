"""Packaging: resource lookup, `python -m hueman` entry point and version."""
import subprocess
import sys
from pathlib import Path

import hueman.cli as hueman
from hueman.resources import packaged_palettes_dir, packaged_templates_dir

ROOT = Path(__file__).resolve().parent.parent


def test_packaged_dirs_exist_and_are_not_empty():
    palettes = packaged_palettes_dir()
    templates = packaged_templates_dir()
    assert palettes.is_dir() and any(palettes.glob("*.yaml"))
    assert templates.is_dir() and any(templates.glob("*.j2"))


def test_packaged_dirs_live_inside_the_package():
    pkg = Path(hueman.__file__).resolve().parent
    assert packaged_palettes_dir().resolve() == pkg / "palettes"
    assert packaged_templates_dir().resolve() == pkg / "templates"


def test_list_palettes_includes_known_palette(tmp_path):
    from hueman.engine.config import HuemanConfig
    from hueman.cli import Hueman

    cfg = tmp_path / "hueman.yaml"
    cfg.write_text("targets: {}\n")
    assert "gruvbox" in Hueman(HuemanConfig(cfg)).list_palettes()


def test_version_is_a_non_empty_string():
    assert isinstance(hueman.__version__, str) and hueman.__version__


def _run(*args):
    return subprocess.run(
        [sys.executable, "-m", "hueman", *args],
        capture_output=True, text=True, cwd=ROOT,
    )


def test_python_m_hueman_help():
    r = _run("--help")
    assert r.returncode == 0, r.stderr
    assert "usage" in r.stdout.lower()


def test_python_m_hueman_version():
    r = _run("--version")
    assert r.returncode == 0, r.stderr
    assert hueman.__version__ in r.stdout


def test_python_m_hueman_list():
    r = _run("--config", str(ROOT / "hueman" / "data" / "hueman.config.example.yaml"), "list")
    assert r.returncode == 0, r.stderr
    assert "gruvbox" in r.stdout.split()
