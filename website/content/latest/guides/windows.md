# Windows and WSL

hueman runs inside WSL and writes to the Windows disk through `/mnt/c`. That
covers theming Windows Terminal, WezTerm, qutebrowser, and the taskbar (via
Windhawk). This guide shows the four patterns.

## Paths in `outputs`

Windows paths appear from WSL as `/mnt/c/Users/<user>/...`. To avoid repeating
them, define a variable in `vars` (see [Variables](../configuration.md#variables)):

```yaml
vars:
  win_home: "/mnt/c/Users/<user>"
```

`${win_home}` is substituted in `outputs` and `skip_unless_path_exists`, but not
in `reload`, `post_apply`, or patch markers. `~` also works in those paths
(there it is the WSL home, not Windows). `--var win_home=...` can override from
the command line.

## Windows Terminal

`json_scheme_upsert` strategy: insert or update a scheme inside `settings.json`
from the palette's `kitty` section, with no template.

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

`scheme_name` is the scheme name (default `Dotfiles`). Assign it once in
Windows Terminal (`"colorScheme": "Dotfiles"` on the profile); after that every
`hueman set` updates it. The file must exist and be valid JSON.

## WezTerm

Uses the packaged template `wezterm_colors.lua.j2` (`kitty` section), which
defines `config.colors = { ... }`. `patch` mode with `marker_begin`/`marker_end`:

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

Markers are text you choose; they only need to match between the config and
`.wezterm.lua`. hueman replaces everything between them. Patch mode never
creates files: `.wezterm.lua` must exist. If the markers are missing, the block
is appended at the end of the file, which can land after `return config`; the
usual approach is to place both markers by hand in the right spot, before the
`return`:

```lua
-- BEGIN hueman managed colors
-- END hueman managed colors
```

## qutebrowser on Windows

Overwrite of the generated theme, guarded by `skip_if_missing_parent`: if the
directory does not exist (qutebrowser not installed or without that folder) it
is skipped without error.

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

Your qutebrowser `config.py` must import that module.

## Taskbar with Windhawk

Windhawk's `windows-11-taskbar-styler` mod stores colors in the registry
(`HKLM`), which WSL cannot write. The fix is two parts:

1. hueman writes a JSON with `fill` and `text` (template
   `windhawk_taskbar.json.j2`, `polybar` section: `background` and `primary`).
2. A Windows scheduled task with elevated privileges reads that JSON and
   applies the colors. A task is used because `schtasks.exe /run` can launch it
   from WSL without a UAC prompt; elevation is granted once when installing it.

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
    reload: "schtasks.exe /run /tn <TaskName> >/dev/null 2>&1 || true"
```

- `skip_unless_path_exists` skips the whole target outside WSL.
- `reload` runs only after an effective write; with `|| true` it is
  best-effort even if the task is not installed (see also `reload_failure` in
  [Configuration](../configuration.md)).

One-time task install, from an Administrator PowerShell, with the repo examples
([`examples/windows/`](https://github.com/NeanderTeam/hueman/tree/main/examples/windows))
(`install-windhawk-taskbar-task.ps1` and `windhawk-taskbar-apply.ps1`, same
folder):

```powershell
powershell -ExecutionPolicy Bypass -File .\install-windhawk-taskbar-task.ps1 -TaskName <TaskName>
```

The default task name is `DotfilesThemeWindhawk` and the default JSON lives at
`$env:LOCALAPPDATA\DotfilesTheme\taskbar-colors.json`; if you change either
(`-TaskName`, `-DataFile`), adjust the target to match. The scripts are
examples to adapt and were not tested on Windows; read them before use.
