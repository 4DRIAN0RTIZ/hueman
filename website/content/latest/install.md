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
