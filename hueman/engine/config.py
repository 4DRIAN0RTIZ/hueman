"""Carga hueman.config.yaml (paths, targets, reload) y monta un logger
propio — sin depender de ningún gestor de dotfiles externo."""

import logging
import os
import re
from pathlib import Path

import yaml

from .statesource import StateSyncConfigError, parse_settings
from .targets import FAILURE_POLICIES, load_targets


class ConfigError(ValueError):
    """hueman.config.yaml is unreadable, malformed or has an invalid schema."""


VAR_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_VAR_REF_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def substitute_vars(text: str, variables: dict, where: str) -> str:
    """Replace every exact ``${name}`` in ``text`` with ``variables[name]``.

    A ``$`` not followed by ``{name}`` is left alone. Replacement values are
    inserted verbatim (no recursion). An unknown name raises ConfigError
    naming the variable and ``where`` it was used."""

    def repl(match):
        name = match.group(1)
        if name not in variables:
            raise ConfigError(f"variable '${{{name}}}' no definida (usada en {where})")
        return variables[name]

    return _VAR_REF_RE.sub(repl, text)


def _subst_paths(value, variables, where):
    """Substitute in a str or in each str of a list; other shapes pass through."""
    if isinstance(value, str):
        return substitute_vars(value, variables, where)
    if isinstance(value, list):
        return [substitute_vars(v, variables, where) if isinstance(v, str) else v for v in value]
    return value


def _validate_vars(path, raw_vars) -> dict:
    if raw_vars is None:
        return {}
    if not isinstance(raw_vars, dict):
        raise ConfigError(f"{path}: 'vars' debe ser un mapeo nombre -> valor")
    for name, value in raw_vars.items():
        if not isinstance(name, str) or not VAR_NAME_RE.fullmatch(name):
            raise ConfigError(f"{path}: nombre de variable invalido en 'vars': {name!r}")
        if not isinstance(value, str):
            raise ConfigError(f"{path}: vars.{name} debe ser un string, no {value!r}")
        if _VAR_REF_RE.search(value):
            raise ConfigError(
                f"{path}: vars.{name} no puede contener ${{...}} (las variables no se anidan)"
            )
    return dict(raw_vars)


class HuemanConfig:
    def __init__(self, path: Path, var_overrides: dict = None):
        self.path = path
        try:
            raw = yaml.safe_load(path.read_text()) or {}
        except yaml.YAMLError as exc:
            raise ConfigError(f"{path}: YAML invalido: {exc}") from exc
        if not isinstance(raw, dict):
            raise ConfigError(f"{path}: se esperaba un mapeo YAML en la raiz")
        variables = _validate_vars(path, raw.get("vars"))
        variables.update(_validate_vars(path, var_overrides))
        try:
            self.state_file = Path(
                _subst_paths(raw.get("state_file", "~/.config/hueman/current"), variables, "state_file")
            ).expanduser()
            self.palette_dirs = [
                Path(p).expanduser() for p in _subst_paths(raw.get("palette_dirs", []), variables, "palette_dirs")
            ]
            self.template_dirs = [
                Path(p).expanduser() for p in _subst_paths(raw.get("template_dirs", []), variables, "template_dirs")
            ]
            raw_targets = raw.get("targets") or {}
            if not isinstance(raw_targets, dict) or not all(
                isinstance(v, dict) for v in raw_targets.values()
            ):
                raise ConfigError(f"{path}: 'targets' debe ser un mapeo nombre -> definicion")
            raw_targets = {
                name: self._substitute_target(name, cfg, variables) for name, cfg in raw_targets.items()
            }
        except ConfigError as exc:
            if str(exc).startswith(str(path)):
                raise
            raise ConfigError(f"{path}: {exc}") from exc
        try:
            self.targets = load_targets(raw_targets)
        except TypeError as exc:
            raise ConfigError(f"{path}: target invalido: {exc}") from exc
        self.reload_failure = raw.get("reload_failure", "warn")
        if self.reload_failure not in FAILURE_POLICIES:
            raise ConfigError(
                f"{path}: reload_failure debe ser 'warn' o 'error', no {self.reload_failure!r}"
            )
        self.post_apply = self._validate_post_apply(path, raw.get("post_apply"))
        self.state_sync = self._load_state_sync(path, raw.get("state_sync"))
        self.logger = self._make_logger(self._validate_logging(path, raw.get("logging")))

    @staticmethod
    def _substitute_target(name, cfg, variables):
        out = dict(cfg)
        for key in ("outputs", "skip_unless_path_exists"):
            if key in out:
                out[key] = _subst_paths(out[key], variables, f"targets.{name}.{key}")
        return out

    @staticmethod
    def _validate_post_apply(path, raw):
        if raw is None:
            return []
        if not isinstance(raw, list) or not all(isinstance(c, str) for c in raw):
            raise ConfigError(f"{path}: 'post_apply' debe ser una lista de comandos (strings)")
        return raw

    @staticmethod
    def _validate_logging(path, raw) -> dict:
        """Return a checked copy of the ``logging`` section."""
        if raw is None:
            return {}
        if not isinstance(raw, dict):
            raise ConfigError(f"{path}: 'logging' debe ser un mapeo (level, file)")
        level = raw.get("level", "INFO")
        if not isinstance(level, str) or not isinstance(
            logging.getLevelName(level.upper()), int
        ):
            raise ConfigError(
                f"{path}: logging.level desconocido: {level!r} "
                "(usa DEBUG, INFO, WARNING, ERROR o CRITICAL)"
            )
        log_file = raw.get("file")
        if log_file is not None:
            if not isinstance(log_file, str) or not log_file:
                raise ConfigError(f"{path}: logging.file debe ser una ruta (string)")
            parent = Path(log_file).expanduser().parent
            if not parent.is_dir():
                raise ConfigError(f"{path}: logging.file: el directorio {parent} no existe")
            if not os.access(parent, os.W_OK | os.X_OK):
                raise ConfigError(f"{path}: logging.file: no se puede escribir en {parent}")
        return {**raw, "level": level.upper()}

    @staticmethod
    def _load_state_sync(path, raw):
        if raw is None:
            return None
        try:
            return parse_settings(raw)
        except StateSyncConfigError as exc:
            raise ConfigError(f"{path}: {exc}") from exc

    @staticmethod
    def _make_logger(logging_cfg: dict) -> logging.Logger:
        logger = logging.getLogger("hueman")
        logger.setLevel(logging_cfg.get("level", "INFO"))
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
            logger.addHandler(handler)
            log_file = logging_cfg.get("file")
            if log_file:
                file_handler = logging.FileHandler(Path(log_file).expanduser())
                file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
                logger.addHandler(file_handler)
        return logger

    @staticmethod
    def resolve_path(explicit) -> Path:
        if explicit:
            return Path(explicit).expanduser()
        env_path = os.environ.get("HUEMAN_CONFIG")
        if env_path:
            return Path(env_path).expanduser()
        # el directorio actual NO se busca a proposito: un config puede ejecutar
        # comandos (post_apply/reload) y no debe cargarse desde un repo ajeno
        return Path("~/.config/hueman/config.yaml").expanduser()
