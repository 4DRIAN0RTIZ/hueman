# hueman

Gestor centralizado de temas: una paleta de color (YAML) alimenta templates
Jinja2 que generan la configuración real de kitty, tmux, nvim, starship,
Windows Terminal, y lo que declares en tu propio archivo de config. Sin
dependencias de ningún gestor de dotfiles externo — todo el mapeo de rutas
de salida vive en un `hueman.config.yaml` propio, fuera de esta carpeta.

## Uso

```
python3 hueman.py --config /ruta/a/hueman.config.yaml set <paleta> [--dry-run] [--only NOMBRE[,NOMBRE...]]
python3 hueman.py --config /ruta/a/hueman.config.yaml list
python3 hueman.py --config /ruta/a/hueman.config.yaml status
```

Ver `hueman.config.example.yaml` para el esquema completo de un target.

`--only` (repetible, acepta lista separada por comas y globs `fnmatch`, ej.
`--only 'qutebrowser_userstyle_*'`) limita `set` a los targets cuyo nombre
coincide: solo esos se renderizan y solo sus `reload` corren. Un patron sin
coincidencias termina con exit 1 y lista los targets validos. Con `--only`
**no** se escribe el state file (el tema activo no cambia) y **no** corre
`post_apply`: es una re-renderizacion parcial, no un cambio de tema.

### Fallos de `reload` / `post_apply`

Se registra el codigo de salida de cada comando. La clave `reload_failure`
(`warn` por defecto, o `error`) decide que pasa si uno sale con codigo != 0;
cada target puede sobreescribirla con su propio `reload_failure`. Con `warn`
se loguea un warning y `set` sale con 0; con `error` se loguea un error, el
resto de pasos se ejecuta igual (best-effort) y `set` sale con 1. `post_apply`
usa la politica global. Un error de escritura (permisos, disco lleno) es un
error limpio del target (log + exit 1) y su archivo original queda intacto.

### Placeholders en `reload` / `post_apply`

Los comandos pueden usar `{name}` (alias `{palette}`) y `{seccion.clave}`
(lookup con punto en la paleta activa, ej. `{kitty.color4}`). El valor se
inserta con `shlex.quote`. `${VAR}`, `$(...)` y llaves sin punto (ej.
`find -exec {} +`) quedan intactas; un `{a.b}` que no existe en la paleta
aborta con un error claro. Ejemplo:
`reload: "python3 ~/x.py --name {name} --color {kitty.color4}"`.
Con `set --dry-run` se imprimen los `post_apply` ya expandidos.

## Usar hueman con un repo de dotfiles

El motor no sabe nada de tus rutas: todo el mapeo vive en un `config.yaml`
que mantenés en tu repo de dotfiles. Patrón recomendado:

1. Guardá el config (y tus `palettes.custom/` y `templates.custom/`) en el
   repo, por ejemplo `~/dotfiles/hueman/config.yaml`.
2. Enlazá ese directorio como `~/.config/hueman` (`ln -s ~/dotfiles/hueman ~/.config/hueman`).
   Así `hueman set` encuentra el config sin flags.
3. Opcional: un wrapper `bin/hueman` con `exec python3 ~/Projects/hueman/hueman.py "$@"`.

### Resolución del config

Orden de precedencia: `--config RUTA` > variable `HUEMAN_CONFIG` >
`./hueman.config.yaml` en el directorio actual > `~/.config/hueman/config.yaml`.

### Comandos

```
hueman list                                  # paletas disponibles
hueman status                                # tema activo + outputs existentes
hueman set <paleta> --dry-run                # muestra que escribiria, sin tocar nada
hueman set <paleta>                          # aplica: render, reload por target, post_apply
hueman set <paleta> --only 'a_*' --only b    # re-render parcial (globs fnmatch, repetible, o a,b)
```

`--only` no actualiza el state file ni corre `post_apply`. Si algun target
falla porque la paleta no trae una clave que necesita (`palette_key` o un
`extra_vars`), se omite con un warning que nombra target y clave, el resto
sigue y `set` termina con exit 1.

### Placeholders en hooks

`reload` y `post_apply` aceptan `{name}` (alias `{palette}`) y
`{seccion.clave}` (ej. `{kitty.color4}`), sustituidos con `shlex.quote`.
`${VAR}` y llaves sin punto quedan intactas; un `{a.b}` inexistente aborta.

### Guardas de salida

- `skip_if_missing_parent: true` — omite cada output cuyo directorio padre no existe.
- `skip_unless_path_exists: RUTA | [RUTA, ...]` — omite el target entero
  (sin escribir ni disparar reload) salvo que existan todas las rutas.
  Ej.: solo tocar el JSON de Windhawk si existe `/mnt/c/Windows/System32/schtasks.exe`.

El `reload` de un target solo corre si realmente se escribio al menos un
output (en `--dry-run` nunca corre).

### State file

`state_file` guarda el nombre de la paleta activa (una linea). Se escribe solo
en un `set` completo y real: no en `--dry-run`, no con `--only`. `status` y
`{name}` en hooks leen/usan ese nombre.

## Arquitectura

- `engine/colors.py` — helpers de contraste/luminancia (WCAG), expuestos como filtros Jinja `contrast`/`is_dark`.
- `engine/palettes.py` — carga `palettes/*.yaml` empaquetadas + `palette_dirs` custom del config (custom gana en caso de choque de nombre).
- `engine/targets.py` — modelo declarativo de un target (`Target`, `PatchSpec`).
- `engine/render.py` — dos funciones genéricas, `render_overwrite` y `render_patch` (con estrategias `regex_splice` y `json_scheme_upsert`) — ningún target tiene código Python propio.
- `engine/reload.py` — ejecuta el comando de reload de cada target (best-effort) + los `post_apply` globales.
- `engine/config.py` — carga `hueman.config.yaml` y monta el logger.

`palettes/` y `templates/` traen ~24 paletas estéticas genéricas y templates para las herramientas más comunes (kitty, tmux, polybar, nvim/nightfox, dunst, bspwm, yazi, qutebrowser, rofi, fzf, atuin, oh-my-posh, wezterm, starship). Para targets idiosincráticos (herramientas propias, poco comunes) usá `template_dirs` en tu config en vez de pedir que se agreguen acá.

## Diferencias de comportamiento a tener en cuenta si venís de un motor viejo basado en detección de host/entorno

1. **`outputs` es una lista estática, no "descubierta" en cada corrida.** Si listás una ruta que hoy no existe, un target `overwrite` la va a crear (`mkdir -p` + write). Si antes tu motor omitía en silencio un entorno que no tenía la carpeta creada, ahora simplemente la crea.
2. **El `reload` de un target solo se dispara si ese target efectivamente escribió algo** (es decir, si `palette_key` estaba presente en la paleta). No hay un paso de "reload global" que se intente sin importar qué se renderizó.
3. **Nada de detección de hostname/entorno vive acá.** Si tu reload depende de "qué máquina soy" (ej. elegir entre `launch.sh` de distintos perfiles de polybar), resolvé eso en un script wrapper propio y pasalo como `reload:` — el motor solo ejecuta el comando que le des.

## Repo propio

Esta carpeta es autocontenida a propósito: nada dentro de `hueman/` importa
código fuera de sí misma, salvo el archivo de config externo que cada usuario
provee. Vive en `~/Projects/hueman`, separada de cualquier repo de dotfiles.

Un repo de dotfiles que la use solo necesita un wrapper apuntando acá y su
propio `hueman.config.yaml`.
