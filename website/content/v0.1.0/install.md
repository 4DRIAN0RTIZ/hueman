# Instalación

## Requisitos

- Python 3
- Dependencias: Jinja2 y PyYAML (`requirements.txt`)

```sh
python3 -m pip install -r requirements.txt
# o el flujo que uses en tu entorno
```

## Obtener hueman

Clona o descarga el repo y ejecuta el CLI desde la raíz:

```sh
python3 hueman.py --help
```

Opcional: enlaza o envuelve el script en tu `PATH`.

## Config del usuario

hueman **no** trae tu mapeo de máquinas. Necesitas un config propio (copia
desde `hueman.config.example.yaml`) y pásalo así, en este orden de
precedencia:

1. `hueman.py --config /ruta/al/config.yaml`
2. variable `HUEMAN_CONFIG`
3. `./hueman.config.yaml` en el working directory
4. `~/.config/hueman/config.yaml`

## Verificar

```sh
python3 hueman.py --config /ruta/al/config.yaml list
python3 hueman.py --config /ruta/al/config.yaml set <paleta> --dry-run
```

En un checkout de desarrollo, `./init.sh` corre smoke tests y la suite.
