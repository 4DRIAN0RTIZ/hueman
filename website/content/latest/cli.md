# CLI

```text
hueman [--config RUTA] [--var NOMBRE=VALOR ...] list
hueman [--config RUTA] [--var NOMBRE=VALOR ...] status
hueman [--config RUTA] [--var NOMBRE=VALOR ...] set <paleta> [--dry-run] [--only NOMBRE[,NOMBRE...]]
hueman [--config RUTA] [--var NOMBRE=VALOR ...] sync [-q|--quiet]
```

## Opciones globales

Van antes del subcomando.

| Opción | Efecto |
|--------|--------|
| `--config RUTA` | Archivo de configuración (ver [Configuración](configuration.md)) |
| `--version` | Imprime la versión instalada y sale |
| `--var NOMBRE=VALOR` | Define o sobreescribe una variable de `vars:` para `${NOMBRE}` en las claves de rutas. Repetible. Ej.: `hueman --var repo=~/dotfiles set <paleta>`. Una forma inválida (sin `=` o nombre inválido) sale con exit 2 |

## `list`

Paletas disponibles (empaquetadas + `palette_dirs`), orden alfabético.

## `set <paleta>`

Renderiza todos los targets, escribe salidas, corre `reload` por target con
escritura efectiva y `post_apply` al final. Persiste el nombre de paleta en
`state_file`. Con `state_sync`, publica `{palette, revision}` (no en
`--dry-run` ni `--only`).

| Flag | Efecto |
|------|--------|
| `--dry-run` | No escribe, no crea dirs, no reload real; muestra plan |
| `--only` | Solo targets cuyo nombre matchea (coma o glob `fnmatch`). No escribe state ni corre `post_apply`. Sin match → exit 1 |

Si un target falla porque la paleta no trae una clave que necesita
(`palette_key` con `extra_vars`, o la sección de `json_scheme_upsert`), se
omite con un warning que nombra target y clave, el resto sigue y `set` sale 1.

## `status`

Paleta activa y, con `state_sync`, revisiones y drift (`in sync`, `behind`,
`ahead`, `no remote state`, `remote unreachable`).

## `sync`

Pull de estado remoto y aplica si la revision remota es mayor. Pensado para
startup de shell (`-q`). Sin red / sin `state_sync` → exit 0 con aviso. Un placeholder desconocido en
`reload`/`post_apply` da el mismo error limpio `Config invalida` (exit 1, sin
traceback) y la revision no avanza.

## Códigos de salida (resumen)

- Config o paleta inválida (incluye `${nombre}` sin definir) → 1  
- `--var` con forma inválida → 2  
- Target con error de render/escritura → 1  
- `reload_failure: error` y hook ≠ 0 → 1 (el resto sigue best-effort)  
- `reload_failure: warn` → 0 aunque el hook falle  
