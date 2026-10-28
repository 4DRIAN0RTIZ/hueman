# Quickstart

1. Copia `hueman.config.example.yaml` a tu repo de dotfiles y ajusta
   `outputs`, `palette_dirs` y `template_dirs`.
2. Lista paletas:

```sh
python3 hueman.py --config ~/dotfiles/theme/hueman.config.yaml list
```

3. Prueba sin escribir:

```sh
python3 hueman.py --config ~/dotfiles/theme/hueman.config.yaml set catppuccin-mocha --dry-run
```

4. Aplica:

```sh
python3 hueman.py --config ~/dotfiles/theme/hueman.config.yaml set catppuccin-mocha
```

5. Para una app que aún no tiene template empaquetado, sigue
   [Agregar soporte a una tool](guides/add-a-tool.md).
