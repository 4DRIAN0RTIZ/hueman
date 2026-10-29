# Arquitectura

Capas del CLI (sin lógica por nombre de app):

| Módulo | Rol |
|--------|-----|
| `hueman/cli.py` | CLI y orquestación (entry point `hueman`, también `python3 -m hueman`) |
| `hueman/engine/config.py` | Carga de config y logger |
| `hueman/engine/palettes.py` | Precedencia y carga de paletas |
| `hueman/engine/targets.py` | Modelo declarativo Target / PatchSpec |
| `hueman/engine/render.py` | Jinja, overwrite, patch |
| `hueman/engine/colors.py` | Filtros `contrast` / `is_dark` |
| `hueman/engine/reload.py` | Ejecución best-effort de hooks |
| `hueman/engine/fsutil.py` | Escritura atómica |
| `hueman/engine/statesource.py` | StateSource (git / file) |

Principio: **lo específico de una tool vive en YAML + Jinja**, no en ramas
Python. Por eso [agregar una tool](guides/add-a-tool.md) no requiere parchear
el motor.

## Repo autocontenido

El repo es autocontenido a propósito: nada dentro de él importa código fuera
de sí mismo, salvo el archivo de config externo que cada usuario provee. Un
repo de dotfiles que lo use solo necesita tener `hueman` instalado y su
propio `hueman.config.yaml` (ver [Configuración](configuration.md)).
