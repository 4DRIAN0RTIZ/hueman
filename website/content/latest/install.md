# Instalación

## Requisitos

- Python 3
- Dependencias: Jinja2 y PyYAML (`requirements.txt`)

```sh
python3 -m pip install -r requirements.txt
# o el flujo que uses en tu entorno
```

## Obtener hueman

Clona el repo y ejecuta el CLI desde la raíz:

```sh
git clone <url-del-repo> ~/src/hueman
cd ~/src/hueman
python3 hueman.py --help
```

(La URL depende de dónde esté alojado el repo.)

Opcional: un wrapper en tu `PATH` para escribir `hueman` en vez de
`python3 hueman.py`. Por ejemplo `~/.local/bin/hueman`:

```sh
#!/bin/sh
exec python3 ~/src/hueman/hueman.py "$@"
```

Dale permisos con `chmod +x ~/.local/bin/hueman`. Un alias también sirve:
`alias hueman='python3 ~/src/hueman/hueman.py'`.

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
