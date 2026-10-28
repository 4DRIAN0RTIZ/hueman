# Diagnóstico

| Problema | Qué mirar |
|----------|-----------|
| No encuentra config | Orden `--config` / `HUEMAN_CONFIG` / cwd / XDG |
| Paleta no listada | Nombre de archivo, `palette_dirs`, YAML válido |
| Template no encontrado | Nombre exacto, `template_dirs`, empaquetado vs custom |
| Archivo no cambia | `--dry-run`, `--only`, skip guards, patch sin match |
| Colores crudos `{{ … }}` | `palette_key` y claves de la paleta |
| Exit 1 con tema aplicado | Targets omitidos por error, o `reload_failure: error` |
| Sync no aplica | `status` drift; remoto inalcanzable; revision local ≥ remota |

Más contexto al extender tools: [Agregar soporte a una tool](guides/add-a-tool.md).
