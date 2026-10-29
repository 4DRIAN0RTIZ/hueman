# Sync entre nodos

Opt-in vía `state_sync` en el config. Publica `{palette, revision}` para que
otras máquinas converjan con `hueman sync`. Sin la clave, nada cambia. Los
ejemplos asumen el comando `hueman` instalado (ver
[Instalación](install.md)).

## Backends

El backend se elige con `state_sync.type`; la interfaz abstracta es
`StateSource` (`hueman/engine/statesource.py`) y el motor solo la usa a través de
`build_source`. Un tipo desconocido es un error de config que lista los
válidos.

### `type: git` (default)

```yaml
state_sync:
  type: git                 # default; configs sin `type` siguen igual
  repo: "~/dotfiles"        # repo del que se toma la URL del remoto
  remote: origin            # default
  branch: hueman-state      # default
  # timeout: 15             # segundos por llamada git (default 15)
```

- Cada `set` completo publica `{palette, revision}` en la rama huérfana
  `hueman-state` del remoto: un único commit reescrito y `push
  --force-with-lease`.
- Ante rechazo del push se hace fetch: gana la `revision` mayor y el empate lo
  resuelve el push aceptado, con reintentos acotados.
- hueman usa un repo git propio (bare) bajo `$XDG_STATE_HOME/hueman/` (o
  `workdir`) y **no toca tu working tree**.
- Sin git, remoto o red, `set` aplica en local y avisa.

### `type: file`

```yaml
state_sync:
  type: file
  path: "~/Sync/hueman.state.yaml"   # carpeta sincronizada por Syncthing/Dropbox
```

Guarda el mismo `{palette, revision}` con escritura atómica; gana la
`revision` mayor y el empate lo gana la última escritura aceptada. Si la
carpeta no existe (no montada) cuenta como inalcanzable y no se crea.

Backend HTTP: pendiente (requiere definir un protocolo de compare-and-set del
servidor).

### Contrato de un backend

Probado por `tests/test_state_source_contract.py`: nunca lanza, tiempos
acotados, `revision` monótona (mayor gana, empate gana la escritura
aceptada), `read_result()` distingue "alcanzable pero vacío" de
"inalcanzable" y `write()` solo devuelve True si el estado quedó publicado.

## Comandos

- `set` publica tras aplicar. `--dry-run` y `--only` no escriben ni empujan
  estado.
- `sync` aplica solo si la revisión remota es mayor que la local.
- `status` muestra revisión local, remota y drift.

### `sync`

Hace fetch de `hueman-state`. Si la `revision` remota es mayor, aplica la
paleta (sin publicar una revisión nueva) y guarda la revisión local. Si no,
no hace nada: sin escrituras ni reload (idempotente). La revisión local vive
en `<state_file>.revision`; el `state_file` sigue siendo solo el nombre de la
paleta, y `set` actualiza la revisión al publicar.

Pensado para el arranque del shell:

- Silencioso si no hay cambios; nunca cuelga (cada llamada git tiene
  timeout, `state_sync.timeout`, 15 s por defecto; ssh con `BatchMode`).
- Solo sale con código != 0 ante errores reales (paleta inexistente, target
  fallido según `reload_failure`).
- Sin red, sin remoto o sin `state_sync` sale 0 con un aviso en stderr;
  `-q/--quiet` los silencia.
- Nunca aplica datos de la copia local cuando el remoto es inalcanzable.

### Drift en `status`

| Drift | Significado |
|-------|-------------|
| `in sync` | Local y remoto tienen la misma revisión |
| `behind` | El remoto es más nuevo: corre `sync` |
| `ahead` | La local es más nueva y no está publicada |
| `no remote state` | El remoto es alcanzable pero aún no hay estado |
| `remote unreachable` | No se pudo leer el remoto; la revisión remota se marca como `local cache` |

## Dos máquinas, paso a paso

1. En cada nodo, agrega `state_sync` a su config (mismo `repo`/`remote` o el
   mismo `path` para `type: file`).
2. En el nodo A corre un `set` completo:
   `hueman --config RUTA set <paleta>`. La primera vez crea la
   rama huérfana `hueman-state` y publica la revisión 1.
3. En el nodo B corre `hueman --config RUTA sync`: aplica la
   paleta y guarda la revisión local.
4. `hueman --config RUTA status` en ambos debe mostrar `in sync`.

`set --dry-run` y `set --only` nunca publican, así que no sirven para
sembrar el estado.

## Correr `sync` automáticamente

```sh
# 1. Arranque del shell (~/.zshrc o ~/.bashrc)
hueman sync -q

# 2. Timer de usuario de systemd (~/.config/systemd/user/hueman-sync.{service,timer})
#    [Service] ExecStart=/ruta/a/hueman sync -q
#    [Timer]   OnBootSec=1min  OnUnitActiveSec=15min
#    systemctl --user enable --now hueman-sync.timer

# 3. cron
*/15 * * * * /ruta/a/hueman sync -q

# 4. Hook de git en tu repo de dotfiles (.git/hooks/post-merge)
#!/bin/sh
hueman sync -q
```

Ajusta `hueman` o la ruta absoluta al CLI según tu instalación (`command -v
hueman`; systemd y cron no cargan el `PATH` de tu shell).
