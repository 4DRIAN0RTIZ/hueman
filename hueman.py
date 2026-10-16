#!/usr/bin/env python3
"""Gestor centralizado de temas (standalone): una paleta por nombre en
palettes/*.yaml (empaquetadas o custom) alimenta templates Jinja2 que
generan la config real de cada herramienta declarada en un
hueman.config.yaml propio del usuario. No depende de ningún gestor de
dotfiles externo — todo el mapeo de rutas es explícito en ese config.
"""

import argparse
import fnmatch
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine.config import ConfigError, HuemanConfig  # noqa: E402
from engine.fsutil import atomic_write_text  # noqa: E402
from engine.palettes import PaletteLoader  # noqa: E402
from engine.reload import expand_command, run_post_apply, run_reload  # noqa: E402
from engine.statesource import GitBranchSource, ReadResult, State  # noqa: E402
from engine.render import TargetRenderError, make_jinja_env, render_target  # noqa: E402

HUEMAN_DIR = Path(__file__).resolve().parent
PACKAGED_PALETTES = HUEMAN_DIR / "palettes"
PACKAGED_TEMPLATES = HUEMAN_DIR / "templates"


class UnknownTargetError(ValueError):
    """Un patron de --only no coincide con ningun target."""


class Hueman:
    def __init__(self, config: HuemanConfig):
        self.config = config
        self.palettes = PaletteLoader(PACKAGED_PALETTES, config.palette_dirs, config.logger)
        self._jinja_envs = {}

    def _jinja_env(self, delimiters):
        key = delimiters or ()
        if key not in self._jinja_envs:
            self._jinja_envs[key] = make_jinja_env(
                self.config.template_dirs, PACKAGED_TEMPLATES, delimiters
            )
        return self._jinja_envs[key]

    def list_palettes(self) -> list:
        return self.palettes.list_palettes()

    def current_theme(self):
        return self.config.state_file.read_text().strip() if self.config.state_file.exists() else None

    def _select_targets(self, only):
        targets = self.config.targets
        if not only:
            return targets
        names = [t.name for t in targets]
        missing = [p for p in only if not fnmatch.filter(names, p)]
        if missing:
            raise UnknownTargetError(
                f"--only sin coincidencias: {', '.join(missing)}. "
                f"Targets validos: {', '.join(names)}"
            )
        return [t for t in targets if any(fnmatch.fnmatchcase(t.name, p) for p in only)]

    def set_theme(self, name: str, dry_run: bool = False, only=None, publish: bool = True) -> list:
        """Con `only` (patrones fnmatch) se renderizan solo los targets que
        coinciden y se dispara solo su reload; NO se escribe el state file ni
        corre post_apply (es una re-renderizacion parcial, no un cambio de tema).

        Un target cuyo render falla por una clave ausente en la paleta se
        omite con un warning y el resto continua; devuelve los nombres de los
        targets fallidos (el CLI sale con codigo 1 si hay alguno).

        `publish=False` (usado por `sync`) aplica sin publicar estado nuevo."""
        selected = self._select_targets(only)
        palette = self.palettes.load(name)
        failed = []
        for target in selected:
            env = self._jinja_env(target.jinja_delimiters)
            try:
                wrote = render_target(env, target, name, palette, dry_run, self.config.logger)
            except TargetRenderError as exc:
                self.config.logger.warning(f"{exc}; target omitido")
                failed.append(target.name)
                continue
            if not dry_run and wrote and target.reload:
                cmd = expand_command(target.reload, name, palette)
                rc = run_reload(cmd, self.config.logger)
                if rc:
                    policy = target.reload_failure or self.config.reload_failure
                    self.config.logger.log(
                        logging.ERROR if policy == "error" else logging.WARNING,
                        f"{target.name}: reload fallo (exit {rc}): {cmd}",
                    )
                    if policy == "error":
                        failed.append(target.name)

        if only:
            return failed

        post_apply = [expand_command(c, name, palette) for c in self.config.post_apply]
        if dry_run:
            for cmd in post_apply:
                print(f"[DRY RUN] post_apply: {cmd}")
            return failed

        self.config.state_file.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self.config.state_file, name + "\n")
        self.config.logger.info(f"Tema activo: {name}")
        post_failed = run_post_apply(post_apply, self.config.logger) or []
        for cmd, rc in post_failed:
            error = self.config.reload_failure == "error"
            self.config.logger.log(
                logging.ERROR if error else logging.WARNING,
                f"post_apply fallo (exit {rc}): {cmd}",
            )
        if post_failed and self.config.reload_failure == "error":
            failed.append("post_apply")
        if publish:
            self._publish_state(name)
        return failed

    @property
    def revision_file(self) -> Path:
        return self.config.state_file.with_name(self.config.state_file.name + ".revision")

    def local_revision(self):
        """Revision of the shared state this node last applied or published.

        Kept beside the plain state file (which only holds the palette name)
        so the legacy format is untouched. None when absent or unreadable."""
        try:
            value = int(self.revision_file.read_text().strip())
        except (OSError, ValueError):
            return None
        return value if value >= 0 else None

    def _save_revision(self, revision: int) -> None:
        atomic_write_text(self.revision_file, f"{revision}\n")

    def _publish_state(self, name: str) -> None:
        """Best-effort: share the active palette; never raises or fails `set`."""
        settings = self.config.state_sync
        if settings is None:
            return
        try:
            source = GitBranchSource.from_settings(settings, self.config.logger)
            current = source.read()
            base = max(current.revision if current else 0, self.local_revision() or 0)
            revision = base + 1
            if source.write(State(name, revision)):
                self._save_revision(revision)
            else:
                self.config.logger.warning("estado compartido no publicado; paleta aplicada solo en local")
        except Exception as exc:  # noqa: BLE001 - sync must never break `set`
            self.config.logger.warning(f"estado compartido no publicado: {exc}")

    def sync(self):
        """Pull the shared state and apply it only if its revision is newer.

        Returns (exit_code, outcome). Safe for shell startup: no change means
        no writes and no reload; an unreachable remote is not an error (exit 0)
        and cached data is never applied."""
        settings = self.config.state_sync
        if settings is None:
            self.config.logger.warning("sync: 'state_sync' no configurado; nada que hacer")
            return 0, "disabled"
        try:
            res = GitBranchSource.from_settings(settings, self.config.logger).read_result()
        except Exception as exc:  # noqa: BLE001 - sync must not crash shell startup
            self.config.logger.warning(f"sync: estado compartido ilegible: {exc}")
            return 0, "unreachable"
        if not res.remote:
            return 0, "unreachable"
        remote = res.state
        if remote is None:
            return 0, "no-remote-state"
        local = self.local_revision() or 0
        if remote.revision == local:
            return 0, "in-sync"
        if remote.revision < local:
            return 0, "ahead"
        self.config.logger.info(f"sync: r{local} -> r{remote.revision} ({remote.palette})")
        failed = self.set_theme(remote.palette, publish=False)
        if failed:
            print(f"Targets con errores: {', '.join(failed)}", file=sys.stderr)
            return 1, "failed"
        self._save_revision(remote.revision)
        return 0, "applied"

    def _drift_lines(self):
        settings = self.config.state_sync
        local = self.local_revision()
        lines = [f"Revision local: {'r%d' % local if local is not None else '(ninguna)'}"]
        try:
            res = GitBranchSource.from_settings(settings, self.config.logger).read_result()
        except Exception:  # noqa: BLE001
            res = ReadResult(None, False)
        remote = res.state
        if remote is None:
            lines.append("Revision remota: (desconocida)" if not res.remote else "Revision remota: (vacia)")
        else:
            origin = "remote" if res.remote else "local cache - remote unreachable"
            lines.append(f"Revision remota: r{remote.revision} ({origin}, paleta {remote.palette})")
        if not res.remote:
            drift = "remote unreachable"
        elif remote is None:
            drift = "no remote state"
        elif (local or 0) < remote.revision:
            drift = "behind"
        elif (local or 0) > remote.revision:
            drift = "ahead"
        else:
            drift = "in sync"
        lines.append(f"Drift: {drift}")
        return lines

    def status(self) -> None:
        print(f"Tema activo: {self.current_theme() or '(ninguno)'}")
        if self.config.state_sync is not None:
            print("\n".join(self._drift_lines()))
        print(f"Paletas disponibles: {', '.join(self.list_palettes())}")
        total = sum(len(t.outputs) for t in self.config.targets)
        existing = sum(1 for t in self.config.targets for o in t.outputs if o.exists())
        print(f"Targets configurados: {len(self.config.targets)} ({existing}/{total} outputs existentes en disco)")


def main():
    parser = argparse.ArgumentParser(description="Gestor centralizado de temas (standalone)")
    parser.add_argument("--config", help="Ruta a hueman.config.yaml")
    sub = parser.add_subparsers(dest="command")

    set_p = sub.add_parser("set", help="Aplicar un tema")
    set_p.add_argument("name")
    set_p.add_argument("--dry-run", action="store_true")
    set_p.add_argument(
        "--only", action="append", metavar="NAME[,NAME...]",
        help="Limitar a targets por nombre o glob (repetible). No actualiza "
        "el state file ni corre post_apply.",
    )

    sync_p = sub.add_parser(
        "sync", help="Aplicar el estado compartido si es mas nuevo (seguro en el arranque del shell)")
    sync_p.add_argument("-q", "--quiet", action="store_true",
                        help="Solo errores reales (sin avisos de red o config)")

    sub.add_parser("list", help="Listar paletas disponibles")
    sub.add_parser("status", help="Mostrar tema activo y estado de los targets")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    config_path = HuemanConfig.resolve_path(args.config)
    if not config_path.exists():
        print(f"Config no encontrada: {config_path}", file=sys.stderr)
        sys.exit(1)

    try:
        tc = Hueman(HuemanConfig(config_path))
    except ConfigError as e:
        print(f"Config invalida: {e}", file=sys.stderr)
        sys.exit(1)
    if args.command == "set":
        only = [p.strip() for v in args.only or [] for p in v.split(",") if p.strip()] or None
        try:
            failed = tc.set_theme(args.name, args.dry_run, only=only)
        except UnknownTargetError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
        if failed:
            print(f"Targets con errores: {', '.join(failed)}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "sync":
        if args.quiet:
            tc.config.logger.setLevel(logging.ERROR)
        sys.exit(tc.sync()[0])
    elif args.command == "list":
        print("\n".join(tc.list_palettes()))
    elif args.command == "status":
        tc.status()


if __name__ == "__main__":
    main()
