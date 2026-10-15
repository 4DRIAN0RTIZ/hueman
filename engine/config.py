"""Carga hueman.config.yaml (paths, targets, reload) y monta un logger
propio — sin depender de ningún gestor de dotfiles externo."""

import logging
import os
from pathlib import Path

import yaml

from .targets import load_targets


class HuemanConfig:
    def __init__(self, path: Path):
        self.path = path
        raw = yaml.safe_load(path.read_text()) or {}
        self.state_file = Path(raw.get("state_file", "~/.config/hueman/current")).expanduser()
        self.palette_dirs = [Path(p).expanduser() for p in raw.get("palette_dirs", [])]
        self.template_dirs = [Path(p).expanduser() for p in raw.get("template_dirs", [])]
        self.targets = load_targets(raw.get("targets", {}))
        self.post_apply = raw.get("post_apply", [])
        self.logger = self._make_logger(raw.get("logging", {}))

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
