# Agregar soporte a una tool

hueman no conoce kitty, tmux ni whiptail por nombre. Solo conoce **targets
declarativos**: un template Jinja, una clave de paleta y una lista de archivos
de salida. Por eso puedes themear una app nueva **sin tocar el motor Python**.

Hay dos caminos:

| Camino | Dónde vive | Cuándo usarlo |
|--------|------------|---------------|
| **Local (tuyo)** | tu `hueman.config.yaml` + `template_dirs` | La tool es tuya, experimental, o aún no quieres upstream |
| **Empaquetado (upstream)** | PR a este repo (`templates/`, opcionalmente paletas) | La tool es común y quieres que otros la usen sin copiar templates |

Empieza siempre por el camino local. Si funciona, opcionalmente súbelo
empaquetado.

## Checklist rápido

1. Entender **qué archivo de config** consume la tool y su formato.
2. Elegir **modo**: `overwrite` (archivo entero) o `patch` (solo un bloque).
3. Elegir **qué colores** de la paleta usar (`palette_key`, casi siempre
   `polybar` o `kitty`).
4. Escribir el **template** `.j2`.
5. Declarar el **target** en tu config con `outputs` reales.
6. Probar con `set --dry-run` y luego `set --only <nombre>`.
7. (Opcional) `reload` para que la app recoja el cambio en caliente.
8. (Opcional) PR para empaquetar el template en el repo.

## 1. Qué necesita la tool

Anota:

- Ruta del archivo de tema o config (ej. `~/.config/miapp/theme.conf`).
- Si la app **reescribe todo el archivo** o solo una sección.
- Si acepta **hex** (`#rrggbb`), nombres ANSI, o ambos.
- Cómo **recarga** el tema (señal, comando, reinicio).
- Si la app **solo existe en algunas máquinas** (guarda con
  `skip_unless_path_exists` / `skip_if_missing_parent`).

Si la app lee un archivo de colores completo, usa **overwrite**. Si el usuario
edita a mano el mismo archivo (starship, algunos TOML), usa **patch**.

## 2. Template Jinja

Crea un archivo en tu directorio custom, por ejemplo:

```text
~/dotfiles/theme/templates.custom/miapp_theme.conf.j2
```

y decláralo en el config:

```yaml
template_dirs:
  - "~/dotfiles/theme/templates.custom"
```

Los `template_dirs` del usuario **ganan** sobre los empaquetados: mismo nombre
de archivo = se usa el tuyo.

### Contexto disponible

- Claves de la sección `palette_key` se expanden en la raíz del template
  (ej. con `palette_key: polybar` usas `{{ background }}`, `{{ primary }}`, …).
- `theme_name` siempre está disponible.
- `extra_vars` en el target puede inyectar rutas punteadas extra de la paleta.
- Filtros globales: `contrast` (texto legible sobre un fondo) e `is_dark`.

Sección semántica mínima que la mayoría de UIs pueden mapear (`polybar` en
las paletas empaquetadas):

| Clave | Uso típico |
|-------|------------|
| `background` | fondo principal |
| `background_alt` | paneles / elevated |
| `foreground` | texto |
| `primary` | acento principal |
| `secondary` | acento secundario |
| `alert` | error / crítico |
| `success` | ok |
| `warning` | aviso |
| `muted` | texto secundario |

Si la tool es un emulador de terminal completo, suele convenir `palette_key:
kitty` (ANSI 0–15, cursor, tabs, …).

### Ejemplo mínimo (overwrite)

```jinja
{# Generado por hueman — no editar a mano. #}
[colors]
background = "{{ background }}"
foreground = "{{ foreground }}"
accent = "{{ primary }}"
danger = "{{ alert }}"
text_on_accent = "{{ primary | contrast }}"
```

### Cabecera y comentarios

- Si el formato de la app **acepta comentarios**, marca el archivo como
  generado por hueman.
- Si **no** acepta comentarios (ej. `NEWT_COLORS_FILE`), usa un comentario
  Jinja `{# ... #}` que **no** se imprime, y no dejes líneas de más en la
  salida.

### Delimitadores alternativos

Si el destino ya usa `{{ ... }}` (JSON con mustache, etc.), declara
`jinja_delimiters` en el target, por ejemplo `["[[", "]]"]`, y escribe el
template con esos delimitadores.

## 3. Target en el config

```yaml
targets:
  miapp_theme:
    template: miapp_theme.conf.j2
    palette_key: polybar
    mode: overwrite
    outputs:
      - "~/.config/miapp/theme.conf"
    # Solo si miapp está instalada en esta máquina:
    # skip_unless_path_exists: "~/.config/miapp"
    # skip_if_missing_parent: true
    reload: "command -v miapp >/dev/null && miapp reload-theme || true"
    # reload_failure: warn   # o error; hereda el global si se omite
```

Reglas importantes:

- **`outputs` es explícito**. hueman no adivina rutas ni hostnames.
- **`mode: overwrite`** crea padres si hace falta (salvo
  `skip_if_missing_parent`) y reemplaza el archivo entero con escritura
  atómica.
- **`mode: patch`** **no crea** archivos inexistentes: si el destino no
  existe, se omite. Necesitas un `patch:` válido (`regex_splice` o
  `json_scheme_upsert`).
- Varios `outputs` reciben el **mismo** render (útil para copiar el tema a
  más de un path).
- `make_executable: true` si el output es un script.

### Patch (cuando no puedes pisar el archivo)

```yaml
targets:
  miapp_block:
    template: miapp_block.j2
    palette_key: polybar
    mode: patch
    patch:
      marker_begin: "# --- BEGIN hueman miapp ---"
      marker_end: "# --- END hueman miapp ---"
      # o marker_regex / insert_after_section_regex; ver config de ejemplo
    outputs:
      - "~/.config/miapp/config.toml"
```

El template debe generar **solo el bloque gestionado**, no el archivo entero.

## 4. Probar

```sh
# Ver qué se escribiría, sin tocar disco ni disparar reload
python3 hueman.py --config ~/dotfiles/theme/hueman.config.yaml \
  set mi-paleta --dry-run --only miapp_theme

# Aplicar solo ese target (no cambia el state file ni corre post_apply)
python3 hueman.py --config ~/dotfiles/theme/hueman.config.yaml \
  set mi-paleta --only miapp_theme

# Aplicación completa de tema
python3 hueman.py --config ~/dotfiles/theme/hueman.config.yaml set mi-paleta
```

Comprueba:

- El archivo de salida tiene los hex esperados y **ningún** `{{` sin renderizar.
- La app muestra el tema (manual o vía `reload`).
- Un segundo `set` no ensucia el archivo (idempotencia).
- En una máquina sin la app, las guardas omiten el target sin fallar el resto.

## 5. Reload y post_apply

- `reload` corre **por target**, solo si hubo escritura efectiva.
- `post_apply` corre **una vez** al final de un `set` completo (no con
  `--only`).
- Placeholders útiles: `{name}` / `{palette}`, y `{seccion.clave}` dentro de
  la paleta (van con quoting de shell). `${VAR}` del shell no se toca.
- Política `reload_failure: warn|error` (global o por target).

## 6. Subir el soporte upstream (opcional)

Cuando el template es genérico y reutilizable:

1. Copia el `.j2` a `templates/` en un fork de hueman.
2. No metas rutas de tu home ni secrets.
3. Si necesitas claves de paleta **nuevas**, documenta la sección o reutiliza
   `polybar` / `kitty` para no romper paletas existentes.
4. Añade o ajusta tests si el repo ya cubre el caso (render, dry-run, etc.).
5. Abre un PR a `dev` con un commit Conventional (`feat(templates): ...`).
6. El usuario solo necesita el target en **su** config; el template ya viaja
   con la herramienta.

Los targets empaquetados de ejemplo viven en `hueman.config.example.yaml`;
cada máquina sigue declarando sus propios `outputs`.

## 7. Errores frecuentes

| Síntoma | Causa probable |
|---------|----------------|
| `missing template …` en tests de config real | El template solo está en custom y algo espera el empaquetado; empaqueta o alinea nombres |
| Valores vacíos en el archivo | Clave ausente en la paleta o `palette_key` que apunta a una clave equivocada dentro de una sección válida: Jinja renderiza vacío |
| Se escriben `{{ background }}` literales | Solo con `jinja_delimiters` que no coinciden con los de la plantilla |
| Target omitido en silencio | `palette_key` que no es sección de la paleta / `skip_unless_path_exists` / padre ausente / patch sobre archivo inexistente |
| `ValueError: placeholder desconocido` | `{seccion.clave}` inexistente en `reload`/`post_apply`: `set` aborta con traceback |
| `set` exit 1 tras reload | `reload_failure: error` y el comando de reload falló |
| Patch no aplica o se duplica | `marker_regex` sin match: sin `insert_after_section_regex` añade el bloque al final en cada corrida; o falta `(?m)` si usas `^`/`$` en `ensure_after` |
| Colores “de fábrica” en newt/whiptail | Faltan elementos en el archivo: el formato reemplaza la paleta entera |

## 8. Qué no hacer

- No agregues ramas `if tool == "…"` en Python: la lógica de la tool va en
  YAML + Jinja.
- No hardcodees hostname ni detección mágica de entorno en el motor.
- No escribas rutas absolutas de un usuario concreto dentro del repo público.
- No uses `mode: patch` esperando que cree el archivo: primero créalo a mano
  o usa overwrite.

## Siguiente lectura

- [Targets y render](../targets.md) — modos y campos al detalle  
- [Paletas](../palettes.md) — secciones y precedencia  
- [Termux y proot](termux.md) — ejemplo de target cuyo reload ocurre fuera del proceso  
- [Windows y WSL](windows.md) — ejemplo de targets en Windows con `vars` y parcheo de configs existentes  
- [Agregar una paleta](add-a-palette.md) — colores nuevos sin tocar templates  
- `hueman.config.example.yaml` en el repo — esquema comentado  
