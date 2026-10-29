# Paletas

YAML bajo `hueman/palettes/` (empaquetadas) y `palette_dirs` (custom). El nombre de
la paleta es el stem del archivo y solo admite letras, dígitos, `.`, `_` y `-`
(debe empezar por letra o dígito, sin `..`): rutas como `/abs/x` o `../x` se
rechazan antes de tocar el disco.

## Precedencia

Custom por nombre gana sobre empaquetada.

## Secciones habituales

- `meta` — nombre legible  
- `kitty` — terminal completo (ANSI, cursor, tabs, …); lo usan también Termux, WezTerm y Neovim  
- `polybar` — tokens semánticos UI (`background`, `primary`, …); lo leen la mayoría de templates  
- `tmux`, `pi` (con `pi.vars`) y `omp` — una por herramienta  

Los templates solo ven la sección de su `palette_key` (más `theme_name` y
`extra_vars`).

Qué template lee cada sección: [Templates empaquetados](targets.md).

## Agregar la tuya

[Agregar una paleta](guides/add-a-palette.md).
