# Targets y render

Un **target** declara cómo una plantilla (o un patch) llega a uno o más
archivos.

## Campos frecuentes

| Campo | Descripción |
|-------|-------------|
| `template` | Nombre del `.j2` (busca en `template_dirs` y luego empaquetados) |
| `palette_key` | Sección de la paleta inyectada al contexto Jinja |
| `mode` | `overwrite` o `patch` |
| `outputs` | Lista de rutas de salida (explícitas) |
| `reload` | Comando shell tras escritura efectiva |
| `reload_failure` | Override `warn` \| `error` |
| `make_executable` | Añade bit de ejecución |
| `skip_if_missing_parent` | Omite output si no existe el directorio padre |
| `skip_unless_path_exists` | Omite el target entero si falta alguna ruta |
| `jinja_delimiters` | Par alternativo a `{{` `}}` |
| `extra_vars` | Mapa nombre → ruta punteada en la paleta |
| `patch` | Spec de patch si `mode: patch` |

## Overwrite

Genera el archivo completo. Escritura atómica (temp + `fsync` + replace).
Crea padres salvo `skip_if_missing_parent`.

## Patch

No crea archivos nuevos. Estrategias:

- `regex_splice` — bloque por `marker_regex` o `marker_begin`/`marker_end`,
  con `replacements` y `ensure_after` opcionales  
- `json_scheme_upsert` — schemes JSON (ej. Kitty) sin template  

## Filtros Jinja

- `contrast` — `#1a1a1a` o `#f5f5f5` según luminancia del color  
- `is_dark` — booleano con el mismo criterio  

## Extender

Guía paso a paso: [Agregar soporte a una tool](guides/add-a-tool.md).
