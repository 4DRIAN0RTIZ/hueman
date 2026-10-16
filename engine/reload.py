"""Ejecuta comandos de recarga: uno por target (best-effort, tras escribir
con éxito) y los `post_apply` globales (una sola vez al final de `set`)."""

import re
import shlex
import subprocess

from .render import _dig

# `{name}`, `{palette}` o `{seccion.clave}`; el lookbehind deja intactos
# `${VAR}` del shell. Llaves simples sin punto (ej. `find -exec {} +`) no
# matchean salvo `name`/`palette`.
_PLACEHOLDER = re.compile(r"(?<!\$)\{([A-Za-z_]\w*(?:\.\w+)*)\}")


def expand_command(cmd: str, name: str, palette: dict) -> str:
    """Sustituye `{name}`/`{palette}` y `{a.b}` (lookup en la paleta activa)
    por su valor con shlex.quote. Un `{a.b}` que no resuelve es un error."""
    def repl(m):
        key = m.group(1)
        if key in ("name", "palette"):
            return shlex.quote(name)
        if "." not in key:
            return m.group(0)
        try:
            value = _dig(palette, key)
        except (KeyError, TypeError):
            raise ValueError(f"placeholder desconocido {{{key}}} en comando: {cmd}")
        return shlex.quote(str(value))

    return _PLACEHOLDER.sub(repl, cmd)


def _run(label: str, cmd: str, logger) -> int:
    """Run `cmd` through the shell and log its exit code."""
    rc = subprocess.run(["sh", "-c", cmd]).returncode
    logger.info(f"{label}: {cmd} (exit {rc})")
    return rc


def run_reload(cmd: str, logger) -> int:
    """Run a target reload command; return its exit code (0 if no command)."""
    if not cmd:
        return 0
    return _run("reload", cmd, logger)


def run_post_apply(commands: list, logger) -> list:
    """Run every command (a failure does not stop the rest); return the
    `(command, exit_code)` pairs of those that exited non-zero."""
    failed = []
    for cmd in commands:
        rc = _run("post_apply", cmd, logger)
        if rc:
            failed.append((cmd, rc))
    return failed
