# Add a palette

A palette is a YAML file of color sections. hueman lists and loads by
**file name** (without `.yaml`). The name may only contain letters, digits,
`.`, `_`, and `-`, and must start with a letter or digit (no `..`, `/`, or
spaces); `hueman set` rejects anything else with `Nombre de paleta invalido`
(exit 1).

## Local path

1. Create `~/dotfiles/theme/palettes.custom/my-theme.yaml`.
2. Declare the directory:

```yaml
palette_dirs:
  - "~/dotfiles/theme/palettes.custom"
```

3. `hueman --config <config> list` should show `my-theme`.
4. `hueman --config <config> set my-theme` applies it.

If the name matches a packaged palette, **the custom one wins**.

## Useful minimal shape

Almost every generic template reads the `polybar` section. Terminal templates
read `kitty`. Copy a packaged palette and change the hex values:

```yaml
meta:
  name: my-theme

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

Keep the **same keys** your templates use. A key the template asks for and the
palette does not provide renders **empty**, with no error. Only an
`extra_vars` path or a `json_scheme_upsert` section fails (warning + exit 1).
If `palette_key` is not a section of the palette, the target is skipped with an
INFO log (`la paleta no tiene la seccion '<key>', omitido`) and exit 0.

## Upstream

To ship it: add the YAML under `hueman/palettes/` in a PR (`feat(palettes): …`).
No user paths or secrets.

## See also

- [Add support for a tool](add-a-tool.md)
- [Palettes](../palettes.md)
