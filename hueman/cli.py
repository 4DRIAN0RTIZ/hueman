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

from . import __version__
from .engine.config import VAR_NAME_RE, ConfigError, HuemanConfig
from .engine.fsutil import atomic_write_text
from .engine.palettes import PaletteLoader
from .engine.reload import PlaceholderError, expand_command, run_post_apply, run_reload
from .engine.statesource import ReadResult, State, build_source
from .engine.render import TargetRenderError, make_jinja_env, render_target
from .resources import packaged_example_config, packaged_palettes_dir, packaged_templates_dir


class UnknownTargetError(ValueError):
    """Un patron de --only no coincide con ningun target."""


class Hueman:
    def __init__(self, config: HuemanConfig):
        self.config = config
        self.palettes = PaletteLoader(packaged_palettes_dir(), config.palette_dirs, config.logger)
        self._jinja_envs = {}

    def _jinja_env(self, delimiters):
        key = delimiters or ()
        if key not in self._jinja_envs:
            self._jinja_envs[key] = make_jinja_env(
                self.config.template_dirs, packaged_templates_dir(), delimiters
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
        # Validar placeholders de reload/post_apply antes de escribir nada.
        for target in selected:
            if target.reload:
                expand_command(target.reload, name, palette)
        post_apply = None
        if not only:
            post_apply = [expand_command(c, name, palette) for c in self.config.post_apply]
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
            source = build_source(settings, self.config.logger)
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
            res = build_source(settings, self.config.logger).read_result()
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
        try:
            failed = self.set_theme(remote.palette, publish=False)
        except PlaceholderError as e:
            # set_theme valida antes de escribir: no hay nada aplicado ni revision que guardar
            print(f"Config invalida: {e}", file=sys.stderr)
            return 1, "failed"
        except SystemExit:
            # load() ya logueo el motivo; la paleta remota no existe aqui (o es invalida).
            # Sync no debe matar el arranque del shell ni avanzar la revision.
            self.config.logger.warning(
                f"sync: la paleta remota '{remote.palette}' no esta disponible localmente; "
                "se omite")
            return 0, "unknown-palette"
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
            res = build_source(settings, self.config.logger).read_result()
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


DOCS_URL = "https://hueman.cuevaneander.tech"


def init_config(path: Path, force: bool) -> int:
    """Copy the packaged example config to `path`; returns the exit code."""
    if path.exists() and not force:
        print(f"Ya existe: {path} (usa --force para sobrescribir)", file=sys.stderr)
        return 1
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, packaged_example_config().read_text())
    except OSError as exc:
        print(f"No se pudo escribir {path}: {exc}", file=sys.stderr)
        return 1
    print(f"Config de ejemplo escrito en {path}")
    return 0


def _var_arg(text: str):
    """argparse type for --var NAME=VALUE; returns (name, value)."""
    name, sep, value = text.partition("=")
    if not sep or not VAR_NAME_RE.fullmatch(name):
        raise argparse.ArgumentTypeError(
            f"invalid form {text!r}: expected NAME=VALUE with NAME matching [A-Za-z_][A-Za-z0-9_]*"
        )
    return name, value


def main():
    parser = argparse.ArgumentParser(description="Gestor centralizado de temas (standalone)")
    parser.add_argument("--version", action="version", version=f"hueman {__version__}")
    parser.add_argument("--config", help="Ruta al config (por defecto: $HUEMAN_CONFIG o ~/.config/hueman/config.yaml)")
    parser.add_argument(
        "--var", action="append", type=_var_arg, default=[], metavar="NAME=VALUE",
        help="Define o sobreescribe una variable de 'vars:' para ${NAME} en las rutas "
        "del config (repetible).",
    )
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

    init_p = sub.add_parser(
        "init", help="Escribir un config de ejemplo en la ruta de config por defecto")
    init_p.add_argument("--force", action="store_true",
                        help="Sobrescribir el config si ya existe")

    sub.add_parser("list", help="Listar paletas disponibles")
    sub.add_parser("status", help="Mostrar tema activo y estado de los targets")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    config_path = HuemanConfig.resolve_path(args.config)
    if args.command == "init":
        sys.exit(init_config(config_path, args.force))
    if not config_path.exists():
        if args.command == "list":
            # Las paletas empaquetadas no dependen del config del usuario.
            loader = PaletteLoader(packaged_palettes_dir(), [], logging.getLogger("hueman"))
            print("\n".join(loader.list_palettes()))
            return
        print(
            f"Config no encontrada: {config_path}\n"
            f"Crea uno con `hueman init`, o usa --config / HUEMAN_CONFIG (docs: {DOCS_URL})",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        tc = Hueman(HuemanConfig(config_path, dict(args.var)))
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
        except PlaceholderError as e:
            print(f"Config invalida: {e}", file=sys.stderr)
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
