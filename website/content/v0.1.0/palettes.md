# Paletas

YAML bajo `palettes/` (empaquetadas) y `palette_dirs` (custom). El nombre de
la paleta es el stem del archivo.

## Precedencia

Custom por nombre gana sobre empaquetada.

## Secciones habituales

- `meta` — nombre legible  
- `kitty` — terminal completo (ANSI, cursor, tabs, …)  
- `polybar` — tokens semánticos UI (`background`, `primary`, …)  
- Otras por app (`tmux`, `pi`, …) según templates que las lean  

Los templates solo ven la sección de su `palette_key` (más `theme_name` y
`extra_vars`).

## Agregar la tuya

[Agregar una paleta](guides/add-a-palette.md).
