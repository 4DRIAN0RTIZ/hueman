# Instalación

## Requisitos

- Python 3.9 o superior
- Las dependencias (Jinja2 y PyYAML) se instalan solas con el paquete

## Instalar

El paquete se llama `hueman-cli`; instala el comando `hueman`. Para una
herramienta de línea de comandos lo recomendado es `pipx`, que la aísla en su
propio entorno:

```sh
pipx install hueman-cli
```

O con pip:

```sh
python3 -m pip install hueman-cli
```

Verifica:

```sh
hueman --version
hueman --help
```

También funciona `python3 -m hueman` si el comando no está en tu `PATH`.

## Desde el código fuente

Para contribuir, o si todavía no hay paquete publicado en tu índice:

```sh
git clone https://github.com/NeanderTeam/hueman.git
cd hueman
pip install -e .
hueman --version
```

La versión sale de los tags de git. En un checkout de desarrollo, `./init.sh`
corre smoke tests y la suite.

## Config del usuario

hueman **no** trae tu mapeo de máquinas. Necesitas un config propio:
`hueman init` escribe uno de ejemplo (comentado) en la ruta por defecto, sin
sobrescribir uno existente salvo con `--force`:

```sh
hueman init
```

hueman busca el config en este orden de precedencia:

1. `hueman --config /ruta/al/config.yaml`
2. variable `HUEMAN_CONFIG`
3. `~/.config/hueman/config.yaml`

El directorio actual no se busca (un config puede ejecutar comandos).

## Verificar

```sh
hueman --config /ruta/al/config.yaml list
hueman --config /ruta/al/config.yaml set <paleta> --dry-run
```

## Actualizar

Usa la misma herramienta con la que instalaste:

```sh
pipx upgrade hueman-cli          # si instalaste con pipx
python3 -m pip install -U hueman-cli   # si instalaste con pip
```

Comprueba la versión con `hueman --version`. Tu config no se toca; para ver
qué cambió entre versiones, revisa el [changelog](changelog.md).

## Desinstalar

```sh
pipx uninstall hueman-cli        # si instalaste con pipx
python3 -m pip uninstall hueman-cli    # si instalaste con pip
```

Desinstalar solo quita el paquete. **No** borra nada de lo que hueman escribió
fuera de él:

- **Tu config**: `~/.config/hueman/config.yaml` (o la ruta que usabas con
  `--config` o `HUEMAN_CONFIG`).
- **El tema activo**: el `state_file` (por defecto `~/.config/hueman/current`)
  y, si usas `state_sync`, su revisión en `<state_file>.revision`.
- **El repo de estado de `state_sync` tipo `git`**: un repo bare propio en
  `$XDG_STATE_HOME/hueman/state-sync/` (por defecto
  `~/.local/state/hueman/state-sync/`), salvo que definas `workdir`. La rama
  `hueman-state` del remoto tampoco se borra.
- **Los archivos generados** en cada `outputs` de tus targets (kitty, tmux,
  etc.), más el archivo de `logging.file` si lo configuraste. Los targets en
  modo `patch` modifican un bloque dentro de un archivo tuyo: hueman no lo
  revierte.

Para encontrarlos, mira tu config *antes* de desinstalar: las rutas están en
`outputs`, `state_file`, `logging.file` y `state_sync`. `hueman status` indica
cuántos outputs existen en disco. Después borra a mano lo que ya no quieras:

```sh
rm -r ~/.config/hueman
rm -r ~/.local/state/hueman      # solo si usaste state_sync tipo git
```

Revisa antes de borrar: si tus targets generan configs que otras herramientas
siguen usando, esas conservarán el último tema aplicado.
