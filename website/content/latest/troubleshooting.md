# Diagnóstico

| Problema | Qué mirar |
|----------|-----------|
| No encuentra config | Orden `--config` / `HUEMAN_CONFIG` / `~/.config/hueman/config.yaml` (el cwd no se busca) |
| Paleta no listada | Nombre de archivo, `palette_dirs`, YAML válido |
| Template no encontrado | Nombre exacto, `template_dirs`, empaquetado vs custom |
| Archivo no cambia | `--dry-run`, `--only`, skip guards, `palette_key` que no es sección de la paleta (INFO `la paleta no tiene la seccion '<key>', omitido`, exit 0), patch sin match |
| Valores vacíos en la salida | Variable ausente en el contexto: Jinja la renderiza como cadena vacía, sin error. Revisa `palette_key` y los nombres de clave |
| `{{ … }}` literales | Solo con `jinja_delimiters` distintos de `{{ }}`: la plantilla usa otros delimitadores |
| `Config invalida: placeholder desconocido` | `{seccion.clave}` inexistente en `reload` o `post_apply`: `set` (y `sync`, sin avanzar la revision) sale con error limpio (exit 1) antes de escribir nada |
| Bloque duplicado en un patch | `marker_regex` sin match ni `insert_after_section_regex`: añade el bloque al final en cada corrida; hueman registra un warning si tu `marker_regex` no reconoce el bloque que insertó |
| Exit 1 con tema aplicado | Targets omitidos por error, o `reload_failure: error` |
| Sync no aplica | `status` drift; remoto inalcanzable; revision local ≥ remota; paleta remota inexistente en este nodo (aviso, exit 0) |

Más contexto al extender tools: [Agregar soporte a una tool](guides/add-a-tool.md).

## Si vienes de un motor basado en detección de host/entorno

1. **`outputs` es una lista estática, no "descubierta" en cada corrida.** Si
   listas una ruta que hoy no existe, un target `overwrite` la crea
   (`mkdir -p` + write). Si antes tu motor omitía en silencio un entorno sin
   la carpeta, ahora la crea; usa `skip_if_missing_parent` para omitirla.
2. **El `reload` de un target solo se dispara si ese target escribió algo.**
   No hay un paso de "reload global" que corra sin importar qué se renderizó.
3. **No hay detección de hostname/entorno en el motor.** Si tu reload depende
   de "qué máquina soy", resuélvelo en un script wrapper propio y pásalo como
   `reload:`; el motor solo ejecuta el comando que le des.
