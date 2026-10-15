"""Definición declarativa de targets: qué template/paleta renderiza a qué
archivo(s), con qué modo (overwrite/patch) y qué comando de reload dispara."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PatchSpec:
    strategy: str = "regex_splice"  # "regex_splice" | "json_scheme_upsert"

    # regex_splice, variante "bloque delimitado por un único regex" (ej. una
    # sección TOML entera como [theme.custom] o [palettes.dotfiles]):
    marker_regex: str = None
    insert_after_section_regex: str = None  # fallback si el bloque no existe aún

    # regex_splice, variante "marcadores begin/end literales" (ej. comentarios
    # -- BEGIN ... / -- END ... envolviendo un bloque de código):
    marker_begin: str = None
    marker_end: str = None
    marker_end_regex: str = None  # alternativa a marker_end cuando el cierre no es literal

    # post-procesamiento aplicado sobre el contenido ya parcheado, ANTES de
    # escribir — son datos (contenido específico del usuario), no lógica:
    replacements: list = field(default_factory=list)  # [[viejo, nuevo], ...]
    ensure_after: list = field(default_factory=list)   # [{if_missing_regex, anchor, insert}, ...]

    # solo para strategy == "json_scheme_upsert":
    scheme_name: str = None
    palette_section: str = "kitty"


@dataclass
class Target:
    name: str
    mode: str = "overwrite"  # "overwrite" | "patch"
    template: str = None
    palette_key: str = None
    outputs: list = field(default_factory=list)
    reload: str = None
    make_executable: bool = False
    skip_if_missing_parent: bool = False
    # Rutas (archivo o directorio) que deben existir todas para que el target
    # corra; si falta alguna se omite sin escribir ni disparar reload.
    skip_unless_path_exists: list = field(default_factory=list)
    jinja_delimiters: tuple = None
    extra_vars: dict = field(default_factory=dict)
    patch: PatchSpec = None

    @classmethod
    def from_dict(cls, name: str, data: dict) -> "Target":
        patch_data = data.get("patch")
        patch = PatchSpec(**patch_data) if patch_data else None
        delimiters = data.get("jinja_delimiters")
        required = data.get("skip_unless_path_exists") or []
        if isinstance(required, str):
            required = [required]
        return cls(
            name=name,
            mode=data.get("mode", "overwrite"),
            template=data.get("template"),
            palette_key=data.get("palette_key"),
            outputs=[Path(o).expanduser() for o in data.get("outputs", [])],
            reload=data.get("reload"),
            make_executable=data.get("make_executable", False),
            skip_if_missing_parent=data.get("skip_if_missing_parent", False),
            skip_unless_path_exists=[Path(p).expanduser() for p in required],
            jinja_delimiters=tuple(delimiters) if delimiters else None,
            extra_vars=data.get("extra_vars", {}),
            patch=patch,
        )


def load_targets(raw: dict) -> list:
    return [Target.from_dict(name, cfg) for name, cfg in raw.items()]
