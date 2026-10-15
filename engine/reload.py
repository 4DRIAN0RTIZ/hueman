"""Ejecuta comandos de recarga: uno por target (best-effort, tras escribir
con éxito) y los `post_apply` globales (una sola vez al final de `set`)."""

import subprocess


def run_reload(cmd: str, logger) -> None:
    if not cmd:
        return
    subprocess.run(["sh", "-c", cmd])
    logger.info(f"reload: {cmd}")


def run_post_apply(commands: list, logger) -> None:
    for cmd in commands:
        subprocess.run(["sh", "-c", cmd])
        logger.info(f"post_apply: {cmd}")
