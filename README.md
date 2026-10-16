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

### Estado compartido (`state_sync`, opt-in)

Con `state_sync: {repo, remote, branch}` en el config, cada `set` publica
`{palette, revision}` en la rama huerfana `hueman-state` del remoto (un unico
commit reescrito + `push --force-with-lease`; ante rechazo se hace fetch, gana
la `revision` mayor y el empate lo resuelve el push aceptado, con reintentos
acotados). hueman usa un repo git propio bajo `$XDG_STATE_HOME/hueman/` y no
toca tu working tree. Sin git, remoto o red, `set` aplica en local y avisa.
`--dry-run` y `--only` no escriben ni empujan estado. Sin la clave, nada cambia.

#### Backends (`state_sync.type`)

La fuente de verdad esta detras de la interfaz abstracta `StateSource`
(`engine/statesource.py`); el motor solo la usa a traves de `build_source`.
El backend se elige con `state_sync.type`: `git` (default, lo descrito arriba;
configs sin `type` siguen igual) o `file`:

```yaml
state_sync:
  type: file
  path: "~/Sync/hueman.state.yaml"   # carpeta sincronizada por Syncthing/Dropbox
```

`file` guarda el mismo `{palette, revision}`, con escritura atomica; gana la
`revision` mayor y el empate lo gana la ultima escritura aceptada. Si la
carpeta no existe (no montada) cuenta como inalcanzable y no se crea. Un tipo
desconocido es un `ConfigError` que lista los validos. Backend HTTP: pendiente
(requiere definir un protocolo de compare-and-set del servidor).

Contrato de un backend (probado por `tests/test_state_source_contract.py`):
nunca lanza, tiempos acotados, `revision` monotona (mayor gana, empate gana la
escritura aceptada), `read_result()` distingue "alcanzable pero vacio" de
"inalcanzable" y `write()` solo devuelve True si el estado quedo publicado.

#### `hueman sync` y drift

`hueman sync` hace fetch de `hueman-state`; si la `revision` remota es mayor
que la local aplica la paleta (sin publicar una revision nueva) y guarda la
revision local. Si no, no hace nada: sin escrituras ni reload (idempotente).
La revision local vive en `<state_file>.revision` (el state file sigue siendo
solo el nombre de la paleta). `set` la actualiza al publicar.

Pensado para correr en el arranque del shell: silencioso si no hay cambios,
nunca cuelga (cada llamada git tiene timeout, `state_sync.timeout`, 15 s por
defecto; ssh con `BatchMode`) y solo sale con codigo != 0 ante errores reales
(paleta inexistente, target fallido segun `reload_failure`). Sin red, sin
remoto o sin `state_sync` sale con 0 y un aviso en stderr; `-q/--quiet` los
silencia. Nunca aplica datos de la copia local cuando el remoto es inalcanzable.

`hueman status` (con `state_sync`) muestra revision local, remota y el drift:
`in sync`, `behind` (corre `sync`), `ahead` (local mas nueva, no publicada),
`no remote state` o `remote unreachable` (la revision remota se marca como
`local cache`).

Disparadores:

```sh
# 1. arranque del shell (~/.zshrc o ~/.bashrc)
hueman sync -q

# 2. systemd user timer (~/.config/systemd/user/hueman-sync.{service,timer})
#    [Service] ExecStart=/path/to/hueman.py sync -q
#    [Timer]   OnBootSec=1min  OnUnitActiveSec=15min
#    systemctl --user enable --now hueman-sync.timer

# 3. cron
*/15 * * * * /path/to/hueman.py sync -q

# 4. hook de git en tu repo de dotfiles (.git/hooks/post-merge)
#!/bin/sh
hueman sync -q
```

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
