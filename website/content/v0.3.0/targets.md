# Targets and render

A **target** declares how a template (or patch) reaches one or more files.

## Common fields

| Field | Description |
|-------|-------------|
| `template` | `.j2` file name (searched in `template_dirs`, then packaged) |
| `palette_key` | Palette section injected into the Jinja context |
| `mode` | `overwrite` or `patch` |
| `outputs` | Explicit list of output paths |
| `reload` | Shell command after an effective write |
| `reload_failure` | Override `warn` \| `error` |
| `make_executable` | Set the executable bit |
| `skip_if_missing_parent` | Skip an output if its parent directory is missing |
| `skip_unless_path_exists` | Skip the whole target if any path is missing |
| `jinja_delimiters` | Alternate pair instead of `{{` `}}` |
| `extra_vars` | Name → dotted palette path map |
| `patch` | Patch spec when `mode: patch` |

If `palette_key` is not a section of the palette, the target is skipped with an
INFO line `... la paleta no tiene la seccion '<key>', omitido` and no error
(exit 0). A missing template variable renders empty. Only a missing
`extra_vars` path or a `json_scheme_upsert` section fails (warning + exit 1).

### Output guards

- `skip_if_missing_parent: true` — skip each output whose parent directory does
  not exist.
- `skip_unless_path_exists: PATH | [PATH, ...]` — skip the whole target (no
  write, no reload) unless every path exists. Example: only touch the Windhawk
  JSON if `/mnt/c/Windows/System32/schtasks.exe` exists.

A target's `reload` only runs if at least one output was actually written
(never on `--dry-run`).

## Overwrite

Generates the full file. Atomic write (temp + `fsync` + replace). Creates
parents unless `skip_if_missing_parent`.

## Patch

Does not create new files. Strategies:

- `regex_splice` — block via `marker_regex` or `marker_begin`/`marker_end`,
  with optional `replacements` and `ensure_after`. With `marker_regex`, if
  there is no match and no `insert_after_section_regex` (or its regex also
  misses), the block is appended at the end; repeating `set` duplicates it if
  the regex does not recognize the inserted block (hueman warns: the problem is
  your `marker_regex`, not a missing anchor)  
- `json_scheme_upsert` — JSON schemes (e.g. Kitty) without a template  

## Packaged templates

Each `.j2` under `hueman/templates/` expects a specific palette section. `—` in
notes means nothing extra.

| Template | Tool | `palette_key` | Notes |
|----------|------|---------------|-------|
| `atuin_theme.toml.j2` | atuin | `polybar` | — |
| `bottom_theme.toml.j2` | bottom | `polybar` | — |
| `bspwm_colors.conf.j2` | bspwm | `polybar` | — |
| `claude_statusline.sh.j2` | Claude Code status line | `polybar` | — |
| `dunst_colors.conf.j2` | dunst | `polybar` | — |
| `fzf_opts.j2` | fzf | `polybar` | — |
| `fzf_theme.j2` | fzf (loader) | — | Does not read palette variables |
| `herdr_theme_custom.toml.j2` | herdr | `polybar` | — |
| `k9s_theme.yaml.j2` | k9s | `polybar` | — |
| `kitty.conf.j2` | kitty | `kitty` | — |
| `lazydocker_theme.yml.j2` | lazydocker | — | Does not read palette variables |
| `leaf_theme.toml.j2` | leaf | `polybar` | — |
| `newt_colors.j2` | newt / whiptail | `polybar` | — |
| `nvim_nightfox_theme.lua.j2` | Neovim (nightfox) | `kitty` | — |
| `omp.omp.json.j2` | oh-my-posh | `omp` | `jinja_delimiters: ["[[", "]]"]`: JSON already uses Go `{{ }}` |
| `opencode_theme.json.j2` | opencode | `polybar` | Needs `extra_vars`: `active_border_color`, `inactive_border_color`, `color4`, `color5`, `color13`. Source is up to you; the `kitty` section has them |
| `pi_theme.json.j2` | pi | `pi` | Reads full `pi.vars` |
| `polybar_colors.ini.j2` | polybar | `polybar` | — |
| `posting_theme.yaml.j2` | posting | `polybar` | `extra_vars`: `panel: pi.vars.elevatedBg` |
| `qutebrowser_github.user.js.j2` | qutebrowser (GitHub userstyle) | `polybar` | — |
| `qutebrowser_google.user.js.j2` | qutebrowser (Google userstyle) | `polybar` | — |
| `qutebrowser_hteam.user.js.j2` | qutebrowser (hteam userstyle) | `polybar` | — |
| `qutebrowser_theme.py.j2` | qutebrowser | `polybar` | On Windows: see [Windows and WSL](guides/windows.md) |
| `rofi_theme.rasi.j2` | rofi | `polybar` | — |
| `sshub_theme.toml.j2` | sshub | `polybar` | — |
| `starship_block.toml.j2` | starship | `polybar` | Meant for `patch`; see `hueman/data/hueman.config.example.yaml` (or `hueman init`) |
| `termux_colors.properties.j2` | Termux | `kitty` | See [Termux and proot](guides/termux.md) |
| `tmux.conf.j2` | tmux | `tmux` | — |
| `tuicr_theme.toml.j2` | tuicr | `polybar` | — |
| `wezterm_colors.lua.j2` | WezTerm | `kitty` | See [Windows and WSL](guides/windows.md) |
| `windhawk_taskbar.json.j2` | Windhawk (taskbar) | `polybar` | See [Windows and WSL](guides/windows.md) |
| `yazi_theme.toml.j2` | yazi | `polybar` | — |
| `zen_theme.json.j2` | Zen Browser | `polybar` | — |

`palette_key` and `extra_vars` were checked by rendering each template against
`catppuccin-mocha`. Output paths are declared by each user.

## Jinja filters

Templates run in a Jinja sandbox (no reach into Python internals like
`__class__`); a blocked operation fails that target cleanly. Still review
third-party templates before use.

- `contrast` — `#1a1a1a` or `#f5f5f5` from the color's luminance  
- `is_dark` — boolean with the same criterion  

## Extending

For idiosyncratic tools (yours, uncommon ones) use `template_dirs` in your
config instead of asking for packaged templates.


Step-by-step guide: [Add support for a tool](guides/add-a-tool.md).
Example with reload outside the process: [Termux and proot](guides/termux.md).
