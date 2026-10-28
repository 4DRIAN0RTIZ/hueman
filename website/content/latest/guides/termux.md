# Termux y proot

Termux lee sus colores de `~/.termux/colors.properties`. hueman puede
generar ese archivo con la plantilla empaquetada `termux_colors.properties.j2`,
que usa la sección `kitty` de la paleta (`foreground`, `background`,
`cursor` y `color0`–`color15`).

## Target

```yaml
targets:
  termux:
    template: termux_colors.properties.j2
    palette_key: kitty
    mode: overwrite
    outputs:
      - "~/.termux/colors.properties"
    # En proot, apunta al archivo real de Termux, no a un symlink.
    # Solo si hueman corre en Termux (no en proot): ver más abajo.
    # reload: "termux-reload-settings"
```

El resultado es un `key=#rrggbb` por línea, sin comillas, precedido por un
comentario `#`. El archivo se sobreescribe completo en cada `hueman set`.

`reload` es un comando por target: se ejecuta con `sh -c` solo después de
una escritura efectiva (no en `--dry-run` ni si todos los outputs se
omitieron). Un fallo se registra según `reload_failure`.

## Dentro de proot

En un distro proot (por ejemplo Debian o Arch bajo `proot-distro`) no existe
`termux-reload-settings`, así que un `reload` directo falla. Dos piezas lo
resuelven:

1. `outputs` debe apuntar al **archivo real** que lee Termux, visto desde el
   proot. Si el home de Termux está montado dentro del proot (por ejemplo en
   `~/baseTermux`), usa `~/baseTermux/.termux/colors.properties`.
2. Un watcher del lado Termux vigila el mtime y recarga.

> **No uses un symlink como output.** hueman escribe de forma atómica
> (archivo temporal + `os.replace`), y si el destino es un symlink lo
> **reemplaza por un archivo normal** y deja intacto el archivo al que
> apuntaba. Termux seguiría leyendo el archivo viejo. Apunta `outputs` al
> archivo final, no a un enlace.

Guarda esto como `~/.termux/theme-watcher` en **Termux** (no en el proot) y
dale permisos con `chmod +x`:

```bash
#!/data/data/com.termux/files/usr/bin/bash
# theme-watcher: vigila colors.properties y recarga Termux cuando cambia
COLORS="$HOME/.termux/colors.properties"
LOCKFILE="$HOME/.termux/.theme-watcher.pid"
if [ -f "$LOCKFILE" ] && kill -0 "$(cat "$LOCKFILE")" 2>/dev/null; then exit 0; fi
echo $$ > "$LOCKFILE"
trap "rm -f $LOCKFILE" EXIT
LAST_MTIME=$(stat -c %Y "$COLORS" 2>/dev/null)
while true; do
    sleep 2
    CURRENT_MTIME=$(stat -c %Y "$COLORS" 2>/dev/null)
    if [ -n "$CURRENT_MTIME" ] && [ "$CURRENT_MTIME" != "$LAST_MTIME" ]; then
        termux-reload-settings
        LAST_MTIME="$CURRENT_MTIME"
    fi
done
```

El lockfile evita instancias duplicadas. Para arrancarlo con cada sesión,
agrega al `~/.bashrc` de Termux:

```bash
~/.termux/theme-watcher &>/dev/null &
```

En este caso omite `reload` en el target: el watcher se encarga.

## Checklist

- [ ] La paleta trae la sección `kitty` con las 19 claves.
- [ ] `outputs` apunta a `~/.termux/colors.properties` y el directorio
      `~/.termux` existe (o deja que hueman lo cree).
- [ ] En proot: `outputs` es el archivo real que lee Termux, no un symlink.
- [ ] El watcher está en el lado Termux, es ejecutable y corre
      (`cat ~/.termux/.theme-watcher.pid`).

## Diagnóstico

- **Los colores no cambian en Termux**: reinicia la sesión o ejecuta
  `termux-reload-settings` a mano. Si eso funciona, el problema es el watcher.
- **`reload` falla en proot con exit 127**: `termux-reload-settings` no existe
  ahí; quita `reload` y usa el watcher.
- **El watcher no arranca**: un `.theme-watcher.pid` huérfano se ignora si el
  proceso ya no existe; revisa permisos de ejecución y la ruta del shebang.
- **Clave faltante**: si una paleta propia omite `cursor` o `colorN`, ese
  target falla (warning y exit 1); copia las claves de una paleta empaquetada.

## Ver también

- [Targets y render](../targets.md)
- [Agregar una paleta](add-a-palette.md)
