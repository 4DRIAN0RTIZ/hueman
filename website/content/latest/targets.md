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

Si `palette_key` no es una sección de la paleta, el target se omite con una línea INFO
`... la paleta no tiene la seccion '<key>', omitido` y sin error (exit 0). Una variable de plantilla ausente se renderiza vacía.
Solo falla (warning + exit 1) una ruta de `extra_vars` inexistente o la sección
de `json_scheme_upsert`.

### Guardas de salida

- `skip_if_missing_parent: true` — omite cada output cuyo directorio padre no
  existe.
- `skip_unless_path_exists: RUTA | [RUTA, ...]` — omite el target entero (sin
  escribir ni disparar reload) salvo que existan todas las rutas. Ej.: solo
  tocar el JSON de Windhawk si existe
  `/mnt/c/Windows/System32/schtasks.exe`.

El `reload` de un target solo corre si realmente se escribió al menos un
output (en `--dry-run` nunca corre).

## Overwrite

Genera el archivo completo. Escritura atómica (temp + `fsync` + replace).
Crea padres salvo `skip_if_missing_parent`.

## Patch

No crea archivos nuevos. Estrategias:

- `regex_splice` — bloque por `marker_regex` o `marker_begin`/`marker_end`,
  con `replacements` y `ensure_after` opcionales. Con `marker_regex`, si no
  hay match y no hay `insert_after_section_regex` (o su regex tampoco
  coincide), el bloque se añade al final del archivo; repetir `set` lo
  duplica si el regex no reconoce el bloque insertado (hueman lo avisa con un
  warning: el problema es tu `marker_regex`, no un ancla faltante)  
- `json_scheme_upsert` — schemes JSON (ej. Kitty) sin template  

## Templates empaquetados

Cada `.j2` de `hueman/templates/` espera una sección concreta de la paleta. `—` en
notas significa que no hay nada que añadir.

| Template | Herramienta | `palette_key` | Notas |
|----------|-------------|---------------|-------|
| `atuin_theme.toml.j2` | atuin | `polybar` | — |
| `bottom_theme.toml.j2` | bottom | `polybar` | — |
| `bspwm_colors.conf.j2` | bspwm | `polybar` | — |
| `claude_statusline.sh.j2` | status line de Claude Code | `polybar` | — |
| `dunst_colors.conf.j2` | dunst | `polybar` | — |
| `fzf_opts.j2` | fzf | `polybar` | — |
| `fzf_theme.j2` | fzf (cargador) | — | No lee variables de la paleta |
| `herdr_theme_custom.toml.j2` | herdr | `polybar` | — |
| `k9s_theme.yaml.j2` | k9s | `polybar` | — |
| `kitty.conf.j2` | kitty | `kitty` | — |
| `lazydocker_theme.yml.j2` | lazydocker | — | No lee variables de la paleta |
| `leaf_theme.toml.j2` | leaf | `polybar` | — |
| `newt_colors.j2` | newt / whiptail | `polybar` | — |
| `nvim_nightfox_theme.lua.j2` | Neovim (nightfox) | `kitty` | — |
| `omp.omp.json.j2` | oh-my-posh | `omp` | `jinja_delimiters: ["[[", "]]"]`: el JSON ya usa `{{ }}` de Go |
| `opencode_theme.json.j2` | opencode | `polybar` | Requiere `extra_vars`: `active_border_color`, `inactive_border_color`, `color4`, `color5`, `color13`. De dónde salen es tu decisión; la sección `kitty` los tiene |
| `pi_theme.json.j2` | pi | `pi` | Lee `pi.vars` completo |
| `polybar_colors.ini.j2` | polybar | `polybar` | — |
| `posting_theme.yaml.j2` | posting | `polybar` | `extra_vars`: `panel: pi.vars.elevatedBg` |
| `qutebrowser_github.user.js.j2` | qutebrowser (userstyle GitHub) | `polybar` | — |
| `qutebrowser_google.user.js.j2` | qutebrowser (userstyle Google) | `polybar` | — |
| `qutebrowser_hteam.user.js.j2` | qutebrowser (userstyle hteam) | `polybar` | — |
| `qutebrowser_theme.py.j2` | qutebrowser | `polybar` | En Windows: ver [Windows y WSL](guides/windows.md) |
| `rofi_theme.rasi.j2` | rofi | `polybar` | — |
| `sshub_theme.toml.j2` | sshub | `polybar` | — |
| `starship_block.toml.j2` | starship | `polybar` | Pensado para `patch`; ver `hueman/data/hueman.config.example.yaml` (o `hueman init`) |
| `termux_colors.properties.j2` | Termux | `kitty` | Ver [Termux y proot](guides/termux.md) |
| `tmux.conf.j2` | tmux | `tmux` | — |
| `tuicr_theme.toml.j2` | tuicr | `polybar` | — |
| `wezterm_colors.lua.j2` | WezTerm | `kitty` | Ver [Windows y WSL](guides/windows.md) |
| `windhawk_taskbar.json.j2` | Windhawk (barra de tareas) | `polybar` | Ver [Windows y WSL](guides/windows.md) |
| `yazi_theme.toml.j2` | yazi | `polybar` | — |
| `zen_theme.json.j2` | Zen Browser | `polybar` | — |

El `palette_key` y las `extra_vars` se comprobaron renderizando cada template
contra `catppuccin-mocha`. Las rutas de salida las declara cada usuario.

## Filtros Jinja

- `contrast` — `#1a1a1a` o `#f5f5f5` según luminancia del color  
- `is_dark` — booleano con el mismo criterio  

## Extender

Para herramientas idiosincráticas (propias, poco comunes) usa `template_dirs`
en tu config en vez de pedir que se agreguen a los templates empaquetados.


Guía paso a paso: [Agregar soporte a una tool](guides/add-a-tool.md).
Ejemplo con reload fuera del proceso: [Termux y proot](guides/termux.md).
