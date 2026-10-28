# Diagnóstico

| Problema | Qué mirar |
|----------|-----------|
| No encuentra config | Orden `--config` / `HUEMAN_CONFIG` / cwd / XDG |
| Paleta no listada | Nombre de archivo, `palette_dirs`, YAML válido |
| Template no encontrado | Nombre exacto, `template_dirs`, empaquetado vs custom |
| Archivo no cambia | `--dry-run`, `--only`, skip guards, `palette_key` que no es sección de la paleta (omitido sin aviso), patch sin match |
| Valores vacíos en la salida | Variable ausente en el contexto: Jinja la renderiza como cadena vacía, sin error. Revisa `palette_key` y los nombres de clave |
| `{{ … }}` literales | Solo con `jinja_delimiters` distintos de `{{ }}`: la plantilla usa otros delimitadores |
| `ValueError: placeholder desconocido` | `{seccion.clave}` inexistente en `reload` o `post_apply`: aborta `set` con traceback |
| Bloque duplicado en un patch | `marker_regex` sin match ni `insert_after_section_regex`: añade el bloque al final en cada corrida |
| Exit 1 con tema aplicado | Targets omitidos por error, o `reload_failure: error` |
| Sync no aplica | `status` drift; remoto inalcanzable; revision local ≥ remota |

Más contexto al extender tools: [Agregar soporte a una tool](guides/add-a-tool.md).
