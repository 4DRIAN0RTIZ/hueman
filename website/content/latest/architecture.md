# Arquitectura

Capas del CLI (sin lógica por nombre de app):

| Módulo | Rol |
|--------|-----|
| `hueman.py` | CLI y orquestación |
| `engine/config.py` | Carga de config y logger |
| `engine/palettes.py` | Precedencia y carga de paletas |
| `engine/targets.py` | Modelo declarativo Target / PatchSpec |
| `engine/render.py` | Jinja, overwrite, patch |
| `engine/colors.py` | Filtros `contrast` / `is_dark` |
| `engine/reload.py` | Ejecución best-effort de hooks |
| `engine/fsutil.py` | Escritura atómica |
| `engine/statesource.py` | StateSource (git / file) |

Principio: **lo específico de una tool vive en YAML + Jinja**, no en ramas
Python. Por eso [agregar una tool](guides/add-a-tool.md) no requiere parchear
el motor.
