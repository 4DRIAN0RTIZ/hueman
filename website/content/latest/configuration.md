# Configuración

Archivo YAML del **usuario** (no vive dentro del repo de hueman como verdad
de máquina). Esquema comentado: `hueman.config.example.yaml`.

## Claves de nivel superior

| Clave | Rol |
|-------|-----|
| `vars` | Variables `${nombre}` para las rutas (ver [Variables](#variables)) |
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

`reload` y `post_apply` aceptan `{name}`/`{palette}` y `{seccion.clave}` (valor
de la paleta activa). Un `{seccion.clave}` inexistente lanza `ValueError` sin
capturar: `set` aborta con traceback.

Errores de esquema o YAML inválido → mensaje claro y exit 1 (sin traceback).

## Variables

`vars` define valores reutilizables para no repetir rutas completas; así el
repo de destino se cambia en un solo lugar:

```yaml
vars:
  repo: "~/dotfiles"
targets:
  kitty:
    template: kitty.conf.j2
    palette_key: kitty
    outputs:
      - "${repo}/kitty/theme.conf"
```

Reglas:

- `vars` es un mapeo nombre → string. Los nombres siguen `[A-Za-z_][A-Za-z0-9_]*`.
  Un valor que no sea string, o un nombre inválido, es error de configuración.
- `${nombre}` se sustituye **solo** en claves de rutas: `outputs` y
  `skip_unless_path_exists` de cada target, y `state_file`, `palette_dirs` y
  `template_dirs` de nivel superior. La sustitución ocurre antes de expandir `~`.
- **No** se sustituye en `reload`, `post_apply`, regex o marcadores de `patch`,
  `extra_vars` ni en el contenido de los templates (en `reload`/`post_apply`
  `${VAR}` sigue siendo del shell).
- Un `${nombre}` no definido en una clave de rutas es un error de configuración
  (`Config invalida: ...`, exit 1) que nombra la variable y dónde se usó.
- Los valores pueden llevar `~`, pero no se anidan: un `${...}` dentro del valor
  de una variable es error.
- Un `$` que no forma exactamente `${nombre}` (por ejemplo `$HOME`) se deja tal cual.
- Un valor vacío es válido y se sustituye por una cadena vacía.
- `--var NOMBRE=VALOR` en la línea de comandos (ver [CLI](cli.md)) sobreescribe
  o agrega variables a las del archivo.

## Targets

Ver [Targets y render](targets.md) y
[Agregar soporte a una tool](guides/add-a-tool.md).
