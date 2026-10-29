"""Carga de paletas YAML: empaquetadas dentro del tool + directorios custom
del usuario, con precedencia de los custom sobre los empaquetados."""

from pathlib import Path

import yaml


class PaletteLoader:
    def __init__(self, packaged_dir: Path, custom_dirs: list, logger):
        self.packaged_dir = packaged_dir
        self.custom_dirs = custom_dirs
        self.logger = logger

    def _search_dirs(self):
        # los custom_dirs (en orden declarado) tienen precedencia sobre lo empaquetado
        return list(self.custom_dirs) + [self.packaged_dir]

    def list_palettes(self) -> list:
        found = {}
        for d in self._search_dirs():
            if not d.exists():
                continue
            for p in d.glob("*.yaml"):
                if p.stem in found and found[p.stem] != p:
                    self.logger.warning(
                        f"Paleta '{p.stem}' definida en más de un directorio, "
                        f"gana la de mayor precedencia: {found[p.stem]}"
                    )
                    continue
                found.setdefault(p.stem, p)
        return sorted(found)

    def load(self, name: str) -> dict:
        for d in self._search_dirs():
            path = d / f"{name}.yaml"
            if path.exists():
                try:
                    data = yaml.safe_load(path.read_text())
                except yaml.YAMLError as exc:
                    self.logger.error(f"Paleta invalida {path}: {exc}")
                    raise SystemExit(1)
                if not isinstance(data, dict):
                    self.logger.error(f"Paleta invalida {path}: se esperaba un mapeo YAML")
                    raise SystemExit(1)
                return data
        available = ", ".join(self.list_palettes())
        self.logger.error(f"Paleta no encontrada: {name}. Disponibles: {available}")
        raise SystemExit(1)
