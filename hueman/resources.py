"""Ubicación de paletas, plantillas y config de ejemplo empaquetadas."""

from importlib.resources import files
from pathlib import Path


# setuptools instala los wheels descomprimidos (nunca como zip), así que
# Path(str(files(...))) es un Path real y válido para el loader de Jinja.
def packaged_palettes_dir() -> Path:
    return Path(str(files("hueman") / "palettes"))


def packaged_templates_dir() -> Path:
    return Path(str(files("hueman") / "templates"))


def packaged_example_config() -> Path:
    return Path(str(files("hueman") / "data" / "hueman.config.example.yaml"))
