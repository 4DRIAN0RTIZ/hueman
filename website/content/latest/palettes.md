# Palettes

YAML under `hueman/palettes/` (packaged) and `palette_dirs` (custom). The palette
name is the file stem and only allows letters, digits, `.`, `_`, and `-`
(must start with a letter or digit, no `..`): paths like `/abs/x` or `../x` are
rejected before touching disk.

## Precedence

Custom by name wins over packaged.

## Common sections

- `meta` — human-readable name  
- `kitty` — full terminal (ANSI, cursor, tabs, …); also used by Termux, WezTerm, and Neovim  
- `polybar` — semantic UI tokens (`background`, `primary`, …); most templates read this  
- `tmux`, `pi` (with `pi.vars`), and `omp` — one per tool  

Templates only see the section for their `palette_key` (plus `theme_name` and
`extra_vars`).

Which template reads which section: [Packaged templates](targets.md).

## Add your own

[Add a palette](guides/add-a-palette.md).
