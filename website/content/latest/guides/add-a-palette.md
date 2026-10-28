# Agregar una paleta

Una paleta es un YAML con secciones de color. hueman lista y carga por
**nombre de archivo** (sin `.yaml`).

## Camino local

1. Crea `~/dotfiles/theme/palettes.custom/mi-tema.yaml`.
2. Declara el directorio:

```yaml
palette_dirs:
  - "~/dotfiles/theme/palettes.custom"
```

3. `python3 hueman.py --config <config> list` debe mostrar `mi-tema`.
4. `python3 hueman.py --config <config> set mi-tema` la aplica.

Si el nombre coincide con una paleta empaquetada, **gana la custom**.

## Forma mínima útil

Casi todos los templates genéricos leen la sección `polybar`. Los de terminal
leen `kitty`. Copia una paleta empaquetada y cambia hex:

```yaml
meta:
  name: mi-tema

kitty:
  foreground: "#e0e0e0"
  background: "#1a1a1a"
  # ... color0-15, cursor, tabs, etc.

polybar:
  background: "#1a1a1a"
  background_alt: "#2a2a2a"
  foreground: "#e0e0e0"
  primary: "#89b4fa"
  secondary: "#94e2d5"
  alert: "#f38ba8"
  success: "#a6e3a1"
  warning: "#f9e2af"
  muted: "#7f849c"
```

Mantén las **mismas claves** que usan tus templates. Una clave que el
template pide y la paleta no trae se renderiza **vacía**, sin error. Solo falla
(warning + exit 1) una ruta de `extra_vars` o la sección de
`json_scheme_upsert`. Si `palette_key` no es sección de la paleta, el target se
omite sin aviso.

## Upstream

Para empaquetar: añade el YAML bajo `palettes/` en un PR (`feat(palettes): …`).
Sin rutas de usuario ni secretos.

## Ver también

- [Agregar soporte a una tool](add-a-tool.md)
- [Paletas](../palettes.md)
