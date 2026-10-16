"""Carga hueman.config.yaml (paths, targets, reload) y monta un logger
propio — sin depender de ningún gestor de dotfiles externo."""

import logging
import os
from pathlib import Path

import yaml

from .statesource import DEFAULT_BRANCH, GIT_TIMEOUT, StateSyncSettings
from .targets import FAILURE_POLICIES, load_targets


class ConfigError(ValueError):
    """hueman.config.yaml is unreadable, malformed or has an invalid schema."""


class HuemanConfig:
    def __init__(self, path: Path):
        self.path = path
        try:
            raw = yaml.safe_load(path.read_text()) or {}
        except yaml.YAMLError as exc:
            raise ConfigError(f"{path}: YAML invalido: {exc}") from exc
        if not isinstance(raw, dict):
            raise ConfigError(f"{path}: se esperaba un mapeo YAML en la raiz")
        self.state_file = Path(raw.get("state_file", "~/.config/hueman/current")).expanduser()
        self.palette_dirs = [Path(p).expanduser() for p in raw.get("palette_dirs", [])]
        self.template_dirs = [Path(p).expanduser() for p in raw.get("template_dirs", [])]
        raw_targets = raw.get("targets") or {}
        if not isinstance(raw_targets, dict) or not all(
            isinstance(v, dict) for v in raw_targets.values()
        ):
            raise ConfigError(f"{path}: 'targets' debe ser un mapeo nombre -> definicion")
        try:
            self.targets = load_targets(raw_targets)
        except TypeError as exc:
            raise ConfigError(f"{path}: target invalido: {exc}") from exc
        self.reload_failure = raw.get("reload_failure", "warn")
        if self.reload_failure not in FAILURE_POLICIES:
            raise ConfigError(
                f"{path}: reload_failure debe ser 'warn' o 'error', no {self.reload_failure!r}"
            )
        self.post_apply = raw.get("post_apply", [])
        self.state_sync = self._load_state_sync(path, raw.get("state_sync"))
        self.logger = self._make_logger(raw.get("logging", {}))

    @staticmethod
    def _load_state_sync(path, raw):
        if raw is None:
            return None
        if not isinstance(raw, dict) or not isinstance(raw.get("repo"), str) or not raw["repo"]:
            raise ConfigError(f"{path}: 'state_sync' debe ser un mapeo con 'repo'")
        for key in ("remote", "branch", "workdir"):
            if key in raw and not isinstance(raw[key], str):
                raise ConfigError(f"{path}: state_sync.{key} debe ser texto")
        timeout = raw.get("timeout", GIT_TIMEOUT)
        if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
            raise ConfigError(f"{path}: state_sync.timeout debe ser un entero > 0 (segundos)")
        workdir = raw.get("workdir")
        return StateSyncSettings(
            repo=Path(raw["repo"]).expanduser(),
            remote=raw.get("remote", "origin"),
            branch=raw.get("branch", DEFAULT_BRANCH),
            workdir=Path(workdir).expanduser() if workdir else None,
            timeout=timeout,
        )

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
        cwd_candidate = Path.cwd() / "hueman.config.yaml"
        if cwd_candidate.exists():
            return cwd_candidate
        return Path("~/.config/hueman/config.yaml").expanduser()
