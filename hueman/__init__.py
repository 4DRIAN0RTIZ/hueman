"""hueman: gestor centralizado de temas basado en paletas YAML y plantillas Jinja2."""

from importlib.metadata import PackageNotFoundError, version

try:
    # Nombre de la distribución en PyPI (único lugar a cambiar junto con pyproject.toml).
    __version__ = version("hueman-cli")
except PackageNotFoundError:  # checkout sin instalar
    __version__ = "0+unknown"

__all__ = ["__version__"]
