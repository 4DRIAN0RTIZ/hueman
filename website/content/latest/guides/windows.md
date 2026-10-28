# Windows y WSL

hueman corre dentro de WSL y escribe en el disco de Windows a través de
`/mnt/c`. Con eso se pueden themear Windows Terminal, WezTerm, qutebrowser y
la barra de tareas (vía Windhawk). Esta guía muestra los cuatro patrones.

## Rutas en `outputs`

Las rutas de Windows se ven desde WSL como `/mnt/c/Users/<usuario>/...`. Para
no repetirlas, define una variable en `vars` (ver [Variables](../configuration.md#variables)):

```yaml
vars:
  win_home: "/mnt/c/Users/<usuario>"
```

`${win_home}` se sustituye en `outputs` y `skip_unless_path_exists`, pero no en
`reload`, `post_apply` ni en los marcadores de `patch`. `~` también funciona en
esas rutas (ahí apunta al home de WSL, no al de Windows). Con
`--var win_home=...` se puede sobreescribir desde la línea de comandos.

## Windows Terminal

Estrategia `json_scheme_upsert`: inserta o actualiza un scheme dentro de
`settings.json` a partir de la sección `kitty` de la paleta, sin template.

```yaml
targets:
  windows_terminal:
    mode: patch
    palette_key: kitty
    outputs:
      - "${win_home}/AppData/Local/Packages/Microsoft.WindowsTerminal_8wekyb3d8bbwe/LocalState/settings.json"
    patch:
      strategy: json_scheme_upsert
      palette_section: kitty
      scheme_name: Dotfiles
```

`scheme_name` es el nombre del scheme (default `Dotfiles`). Hay que asignarlo
una vez en Windows Terminal (`"colorScheme": "Dotfiles"` en el perfil); después
cada `hueman set` lo actualiza. El archivo debe existir y ser JSON válido.

## WezTerm

Usa la plantilla empaquetada `wezterm_colors.lua.j2` (sección `kitty`), que
define `config.colors = { ... }`. Modo `patch` con `marker_begin`/`marker_end`:

```yaml
targets:
  wezterm_windows:
    template: wezterm_colors.lua.j2
    mode: patch
    palette_key: kitty
    outputs:
      - "${win_home}/.wezterm.lua"
    patch:
      marker_begin: "-- BEGIN hueman managed colors"
      marker_end: "-- END hueman managed colors"
```

Los marcadores son texto que eliges tú; solo tienen que coincidir entre el
config y el `.wezterm.lua`. hueman reemplaza todo lo que haya entre ellos. El
modo patch nunca crea archivos: `.wezterm.lua` debe existir. Si los marcadores
no están, el bloque se agrega al final del archivo, que puede quedar después
del `return config`; lo recomendable es escribir los dos marcadores a mano en
el lugar correcto, antes del `return`:

```lua
-- BEGIN hueman managed colors
-- END hueman managed colors
```

## qutebrowser en Windows

Overwrite del tema generado, protegido por `skip_if_missing_parent`: si el
directorio no existe (qutebrowser no instalado o sin esa carpeta) se omite sin
error.

```yaml
targets:
  qutebrowser_windows:
    template: qutebrowser_theme.py.j2
    mode: overwrite
    palette_key: polybar
    skip_if_missing_parent: true
    outputs:
      - "${win_home}/AppData/Roaming/qutebrowser/config/modules/themes/current.py"
```

Tu `config.py` de qutebrowser debe importar ese módulo.

## Barra de tareas con Windhawk

El mod `windows-11-taskbar-styler` de Windhawk guarda sus colores en el
registro (`HKLM`), que WSL no puede escribir. La solución son dos piezas:

1. hueman escribe un JSON con `fill` y `text` (plantilla `windhawk_taskbar.json.j2`,
   sección `polybar`: `background` y `primary`).
2. Una tarea programada de Windows, con privilegios elevados, lee ese JSON y
   aplica los colores. Se usa una tarea porque `schtasks.exe /run` la lanza
   desde WSL sin prompt de UAC; la elevación se concede una sola vez al
   instalarla.

```yaml
targets:
  windhawk_taskbar:
    template: windhawk_taskbar.json.j2
    mode: overwrite
    palette_key: polybar
    skip_if_missing_parent: true
    skip_unless_path_exists: /mnt/c/Windows/System32/schtasks.exe
    outputs:
      - "${win_home}/AppData/Local/DotfilesTheme/taskbar-colors.json"
    reload: "schtasks.exe /run /tn <NombreTarea> >/dev/null 2>&1 || true"
```

- `skip_unless_path_exists` omite el target entero fuera de WSL.
- `reload` corre solo tras una escritura efectiva; con `|| true` es
  best-effort aunque la tarea no esté instalada (ver también `reload_failure`
  en [Configuración](../configuration.md)).

Instalación única de la tarea, desde un PowerShell como Administrador, con los
ejemplos del repo `examples/windows/` (`install-windhawk-taskbar-task.ps1` y
`windhawk-taskbar-apply.ps1`, en la misma carpeta):

```powershell
powershell -ExecutionPolicy Bypass -File .\install-windhawk-taskbar-task.ps1 -TaskName <NombreTarea>
```

El nombre por defecto de la tarea es `DotfilesThemeWindhawk` y el JSON por
defecto está en `$env:LOCALAPPDATA\DotfilesTheme\taskbar-colors.json`; si
cambias alguno (`-TaskName`, `-DataFile`), ajusta el target igual. Los scripts
son ejemplos para adaptar y no se probaron en Windows; léelos antes de usarlos.
