# Configuración

Archivo YAML del **usuario** (no vive dentro del repo de hueman como verdad
de máquina). Esquema comentado: `hueman.config.example.yaml`.

## Claves de nivel superior

| Clave | Rol |
|-------|-----|
| `state_file` | Dónde guardar el nombre de la paleta activa |
| `palette_dirs` | Paletas custom (ganan por nombre) |
| `template_dirs` | Templates custom (ganan por nombre de archivo) |
| `reload_failure` | `warn` (default) o `error` para hooks |
| `state_sync` | Opt-in sync multi-nodo (`type: git` \| `file`) |
| `targets` | Mapa nombre → target |
| `post_apply` | Lista de comandos al final de un `set` completo |
| `logging` | `level` (default `INFO`) y `file` (ruta opcional; se añade un log a archivo además de stderr) |

## Resolución del archivo

1. `--config`  
2. `HUEMAN_CONFIG`  
3. `./hueman.config.yaml`  
4. `~/.config/hueman/config.yaml`  

## Placeholders en `reload` / `post_apply`

Los comandos aceptan `{name}` (alias `{palette}`) y `{seccion.clave}` (lookup
con punto en la paleta activa, ej. `{kitty.color4}`). El valor se inserta con
`shlex.quote`. `${VAR}`, `$(...)` y llaves sin punto (ej. `find -exec {} +`)
quedan intactas. Un `{seccion.clave}` inexistente lanza `ValueError` sin
capturar: `set` aborta con traceback.

```yaml
reload: "python3 ~/x.py --name {name} --color {kitty.color4}"
```

Con `set --dry-run` se imprimen los `post_apply` ya expandidos.

## Fallos de `reload` / `post_apply`

Se registra el código de salida de cada comando. `reload_failure` (`warn` por
defecto, o `error`) decide qué pasa si uno sale != 0; cada target puede
sobreescribirla, y `post_apply` usa la política global.

- `warn`: se loguea un warning y `set` sale 0.
- `error`: se loguea un error, el resto de pasos se ejecuta igual
  (best-effort) y `set` sale 1.

Un error de escritura (permisos, disco lleno) es un error limpio del target
(log + exit 1) y su archivo original queda intacto.

## State file

`state_file` guarda el nombre de la paleta activa (una línea). Se escribe solo
en un `set` completo y real: no en `--dry-run`, no con `--only`. `status` y
`{name}` en los hooks usan ese nombre. Con `state_sync`, la revisión local
vive aparte en `<state_file>.revision` (ver [Sync entre nodos](state-sync.md)).

## Usar con un repo de dotfiles

El motor no sabe nada de tus rutas: todo el mapeo vive en un config que
mantienes en tu repo de dotfiles.

1. Guarda el config (y tus `palettes.custom/` y `templates.custom/`) en el
   repo, por ejemplo `~/dotfiles/hueman/config.yaml`.
2. Enlaza ese directorio como `~/.config/hueman`
   (`ln -s ~/dotfiles/hueman ~/.config/hueman`); así `set` encuentra el config
   sin flags.
3. Opcional: un wrapper `bin/hueman` con `exec python3 /ruta/a/hueman.py "$@"`.

Errores de esquema o YAML inválido → mensaje claro y exit 1 (sin traceback).

## Targets

Ver [Targets y render](targets.md) y
[Agregar soporte a una tool](guides/add-a-tool.md).
