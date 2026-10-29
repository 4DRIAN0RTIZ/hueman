# hueman para agentes

Playbook para ti, agente de código, cuando una persona te pide ayuda con hueman. Guíala a instalar, configurar, aplicar un tema y diagnosticar fallos. Si algo de aquí contradice el código o los docs, gana el código: verifícalo.

Para operar hueman tú mismo (aplicar, inspeccionar, diagnosticar) usa la Agent Skill `skills/latest/hueman/SKILL.md`: esta guía enseña a guiar a una persona; la skill enseña a operar hueman.

Docs canónicas: `index.html?v=latest&p=<pageId>` en este mismo sitio. Ids: `intro`, `install`, `quickstart`, `cli`, `configuration`, `targets`, `palettes`, `state-sync`, `add-tool`, `add-palette`, `termux`, `windows`, `architecture`, `troubleshooting`, `changelog`.

## La idea en cinco líneas

- hueman es un CLI Python (paquete `hueman-cli`, comando `hueman`): una paleta YAML + plantillas Jinja2 = configs de las apps del usuario.
- El mapeo "qué template va a qué archivo" lo declara el usuario en su propio `hueman.config.yaml`. hueman no adivina rutas, hostname ni entorno.
- No es un gestor de dotfiles: no instala, enlaza ni versiona nada. Solo escribe colores en las rutas de `outputs`.
- Una paleta alimenta muchos targets. Cambiar de tema es un `set`.
- Soportar una app nueva es un template + un target, no un cambio al motor (`p=intro`, `p=architecture`).

## Vocabulario, en el orden en que conviene explicarlo

1. **Paleta**: YAML en `hueman/palettes/` (empaquetadas) o `palette_dirs` (del usuario). Su nombre es el archivo sin `.yaml`; a igualdad de nombre gana la del usuario. Secciones típicas: `meta`, `kitty` (`color0`-`color15`, cursor...), `polybar` (`background`, `background_alt`, `foreground`, `primary`, `secondary`, `alert`, `success`, `warning`, `muted`). `p=palettes`
2. **Template**: `.j2` en `hueman/templates/` o `template_dirs` (gana el del usuario). Solo ve la sección de la paleta dada por `palette_key`, más `theme_name` y `extra_vars`. Filtros: `contrast`, `is_dark`.
3. **Target**: entrada de `targets:` con `template`, `palette_key`, `mode`, `outputs` (rutas explícitas) y opcionales (`reload`, `reload_failure`, `make_executable`, `skip_if_missing_parent`, `skip_unless_path_exists`, `jinja_delimiters`, `extra_vars`, `patch`). `p=targets`
4. **Modo**:
   - `overwrite` (default): el archivo es de hueman; se reemplaza entero, con escritura atómica, y se crean los padres.
   - `patch`: el archivo es del usuario y hueman solo toca un bloque (`regex_splice` con `marker_regex` o `marker_begin`/`marker_end`; o `json_scheme_upsert`, que usa la sección `kitty` y no necesita template). **Nunca crea el archivo**: si no existe, lo omite.
5. **`reload` / `post_apply`**: `reload` es un comando por target, solo tras escritura efectiva; `post_apply` corre una vez al final de un `set` completo. Admiten `{name}`/`{palette}` y `{seccion.clave}` (valor de la paleta, con shell-quoting). Son best-effort: un fallo no detiene el resto. `reload_failure` (`warn` por defecto, o `error`) decide si un fallo da exit 1.
6. **`state_sync`** (opt-in): publica `{palette, revision}` para que otras máquinas converjan con `sync`. Backends `git` (rama huérfana, default `hueman-state`) y `file`. `p=state-sync`

## Primera sesión con el humano

Antes de tocar nada, pregúntale (una cosa a la vez) dónde vive o vivirá su config y qué apps quiere themear. `set` escribe **fuera del proyecto**: en cada `outputs` y en `state_file` (default `~/.config/hueman/current`). No ejecutes un `set` real sin su OK explícito sobre la lista de rutas.

**Instalar** (`p=install`). Requiere Python >= 3.9. Se instala con `pipx install hueman-cli` (recomendado para un CLI) o `pip install hueman-cli`; desde el código fuente: `git clone https://github.com/NeanderTeam/hueman.git && cd hueman && pip install -e .`. Jinja2 y PyYAML vienen como dependencias. El comando es `hueman`, pero no asumas que está en el `PATH`: verifica con `hueman --version` o `command -v hueman`. Si no está, desde un checkout del código fuente usa `python3 -m hueman ...` desde la raíz del repo.

**Config.** hueman no trae mapeo de máquinas; parte de `hueman.config.example.yaml` (esquema comentado). Pasa siempre `--config <ruta>` para no depender de la resolución implícita.

**Secuencia** (`p=quickstart`, `p=cli`):

```sh
hueman --config <ruta> list                    # paletas, alfabético
hueman --config <ruta> status                  # tema activo, outputs existentes en disco
hueman --config <ruta> set <paleta> --dry-run  # plan, sin escribir
hueman --config <ruta> set <paleta>            # aplica
```

- `--dry-run` imprime `[DRY RUN] escribiría <ruta>` por output y los `post_apply` que correrían. No escribe, no crea directorios, no ejecuta `reload`, no guarda `state_file` ni publica estado. Enséñale esa lista y espera su visto bueno.
- `set <paleta> --only a,b` limita a targets por nombre o glob `fnmatch` (flag repetible). No guarda `state_file`, no corre `post_apply`, no publica. Si nada coincide: exit 1 con los nombres válidos. Úsalo para probar un target nuevo.
- `sync [-q]` aplica el estado remoto solo si su revisión es mayor; sin red o sin `state_sync` avisa y sale 0.

## Configuración en una pantalla

Resolución de la ruta, en orden: `--config`, variable `HUEMAN_CONFIG`, `./hueman.config.yaml`, `~/.config/hueman/config.yaml`. Si no existe: `Config no encontrada: <ruta>`, exit 1. YAML o esquema inválidos: `Config invalida: ...`, exit 1, sin traceback.

Claves de primer nivel (`p=configuration`): `state_file`, `palette_dirs`, `template_dirs`, `reload_failure`, `state_sync` (`type: git` con `repo`/`remote`/`branch`/`workdir`/`timeout`, o `type: file` con `path`), `targets`, `post_apply`. El código lee además `logging` (`level`, `file`), que `p=configuration` no documenta: confírmalo en `hueman/engine/config.py` antes de recomendarlo.

## Extender

- **App nueva**: template en un `template_dirs` del usuario + target en su config. Empieza local; empaquetar upstream es opcional. Prueba con `set <paleta> --dry-run --only <target>` y luego sin `--dry-run`. Guía y checklist: `p=add-tool`.
- **Paleta nueva**: YAML en un `palette_dirs`; copia una empaquetada y cambia los hex, manteniendo las claves que leen los templates. Verifica con `list`. Guía: `p=add-palette`.
- Nada de ramas `if tool == ...` en Python: lo específico de cada tool vive en YAML + Jinja.

## Diagnóstico: síntoma, causa, comprobación

Reúne antes: ruta del config en uso, salida completa y exit code. Resumen oficial: `p=troubleshooting`.

| Síntoma | Causa (verificada en código) | Comprobación |
|---|---|---|
| `Config no encontrada` | Ninguna ruta del orden de resolución existe | `echo "$HUEMAN_CONFIG"`; pasa `--config` |
| Paleta no aparece / `Paleta no encontrada` | Archivo no es `.yaml`, directorio ausente de `palette_dirs`, o YAML inválido (`Paleta invalida`, exit 1) | `list`; el error enumera las disponibles |
| `plantilla '<x>' no encontrada` | Nombre de `.j2` incorrecto o fuera de `template_dirs`/`hueman/templates/`; target omitido, exit 1 | Nombre exacto del archivo |
| Un target no escribe y no hay error | `skip_unless_path_exists` o `skip_if_missing_parent` no se cumplen; `patch` sobre archivo inexistente; `--only` o `--dry-run` | Líneas `INFO` "omitido" / "no existe" |
| Línea `INFO` `... la paleta no tiene la seccion '<key>', omitido` | `palette_key` no existe como sección en la paleta (exit 0, no es error) | Compara `palette_key` con las claves de primer nivel del YAML |
| `la paleta '<x>' no tiene la clave '<k>' requerida` | Falta una ruta de `extra_vars` o una clave de `json_scheme_upsert`; target omitido, exit 1 | Añade la clave a la paleta |
| Valores vacíos en el output | Una variable de template ausente en la sección: Jinja la renderiza vacía, no falla | Contrasta variables del `.j2` con la sección |
| `{{ ... }}` literales en el output | Delimitadores distintos a los esperados | `jinja_delimiters` del target |
| Patch duplica el bloque | `marker_regex` sin match y sin `insert_after_section_regex`: el bloque se **añade al final**; si el regex tampoco reconoce el bloque insertado, hueman emite un warning (la causa es el `marker_regex`) | Revisa el regex; `(?m)` si usas `^`/`$` en `ensure_after` |
| Exit 1 con el tema aplicado | Algún target omitido por error, o `reload_failure: error` y un hook devolvió ≠ 0 | Mensajes `reload fallo (exit N)` / `post_apply fallo` |
| El reload "no hace nada" | Solo corre con escritura efectiva y sin `--dry-run`; usa `sh -c` | El log registra `reload: <cmd> (exit N)`; que el humano lo corra a mano |
| `set` o `sync` falla con `Config invalida: placeholder desconocido` (antes de escribir nada; `sync` no avanza la revision) | `{seccion.clave}` inexistente en `reload`/`post_apply` | Corrige la clave; `${VAR}` de shell no se toca |
| `sync` no aplica | Remoto inalcanzable, sin estado, o revisión local >= remota (nunca aplica caché) | `status`, línea `Drift:` (`in sync`, `behind`, `ahead`, `no remote state`, `remote unreachable`); la carpeta de `type: file` no se crea |

## Reglas para ti

- No inventes flags, claves, campos de target ni rutas. Si no está aquí, en los docs o en el código, no existe; lee `hueman/cli.py` o `hueman/engine/*.py` y dilo.
- Propón siempre `--dry-run` primero y muestra las rutas antes de un `set` real. Pide confirmación para todo lo que escriba fuera del proyecto (`set`, `sync`, crear config en `~`).
- No escribas rutas reales del usuario ni secretos dentro del repo de hueman; usa `hueman.config.example.yaml` o fixtures temporales.
- `reload` y `post_apply` son best-effort: no los uses como validación; confirma con el log y el exit code.
- `patch` no crea archivos y `--only` no persiste estado: no prometas lo contrario.
- No agregues detección de hostname/entorno ni lógica por tool al motor.
- Si modificas el repo: commits Conventional, ramas desde `dev`, sin editar `CHANGELOG.md` a mano.
