# Configuración

Archivo YAML del **usuario** (no vive dentro del repo de hueman como verdad
de máquina). Esquema comentado: `hueman.config.example.yaml`.

## Claves de nivel superior

| Clave | Rol |
|-------|-----|
| `state_file` | Dónde guardar el nombre de la paleta activa |
| `palette_dirs` | Paletas custom (ganan por nombre) |
| `template_dirs` | Templates custom (ganan por nombre de archivo) |
| `reload_failure` | `warn` (default) o `error` para hooks |
| `state_sync` | Opt-in sync multi-nodo (`type: git` \| `file`) |
| `targets` | Mapa nombre → target |
| `post_apply` | Lista de comandos al final de un `set` completo |
| `logging` | `level` (default `INFO`) y `file` (ruta opcional; se añade un log a archivo además de stderr) |

## Resolución del archivo

1. `--config`  
2. `HUEMAN_CONFIG`  
3. `./hueman.config.yaml`  
4. `~/.config/hueman/config.yaml`  

`reload` y `post_apply` aceptan `{name}`/`{palette}` y `{seccion.clave}` (valor
de la paleta activa). Un `{seccion.clave}` inexistente lanza `ValueError` sin
capturar: `set` aborta con traceback.

Errores de esquema o YAML inválido → mensaje claro y exit 1 (sin traceback).

## Targets

Ver [Targets y render](targets.md) y
[Agregar soporte a una tool](guides/add-a-tool.md).
