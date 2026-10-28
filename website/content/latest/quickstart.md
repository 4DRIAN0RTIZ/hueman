# Quickstart

> Los ejemplos usan `python3 hueman.py`; el repo no trae un comando `hueman`
> (ver [Instalación](install.md)). Si creas el wrapper, quita el prefijo.

## 1. Config mínima

Guarda esto como `~/dotfiles/theme/hueman.config.yaml`. Dos targets con
templates empaquetados, cada uno con su lista explícita de `outputs`:

```yaml
state_file: "~/.config/hueman/current"   # dónde recordar la paleta activa

targets:
  kitty:
    template: kitty.conf.j2     # template empaquetado
    palette_key: kitty          # sección de la paleta que recibe el template
    mode: overwrite             # reescribe el archivo completo
    outputs:
      - "~/.config/kitty/theme.conf"

  tmux:
    template: tmux.conf.j2
    palette_key: tmux
    mode: overwrite
    outputs:
      - "~/.config/tmux/theme.conf"
```

Más opciones (patch, reload, `palette_dirs`) en
[Configuración](configuration.md) y [Targets](targets.md).

## 2. Lista las paletas

```sh
python3 hueman.py --config ~/dotfiles/theme/hueman.config.yaml list
```

```text
arctic-ice
autumn
catppuccin-latte
catppuccin-mocha
copperwave
...
```

## 3. Prueba sin escribir

```sh
python3 hueman.py --config ~/dotfiles/theme/hueman.config.yaml set catppuccin-mocha --dry-run
```

```text
[DRY RUN] escribiría ~/.config/kitty/theme.conf
[DRY RUN] escribiría ~/.config/tmux/theme.conf
```

## 4. Aplica

```sh
python3 hueman.py --config ~/dotfiles/theme/hueman.config.yaml set catppuccin-mocha
```

```text
INFO: Generado: ~/.config/kitty/theme.conf
INFO: Generado: ~/.config/tmux/theme.conf
INFO: Tema activo: catppuccin-mocha
```

## Cómo saber que funcionó

```sh
python3 hueman.py --config ~/dotfiles/theme/hueman.config.yaml status
```

```text
Tema activo: catppuccin-mocha
Paletas disponibles: arctic-ice, autumn, catppuccin-latte, catppuccin-mocha, ...
Targets configurados: 2 (2/2 outputs existentes en disco)
```

(La línea de paletas real lista las 25 empaquetadas; aquí se acorta.)
Y el archivo generado:

```sh
head -5 ~/.config/kitty/theme.conf
```

```text
# Generado por hueman — no editar a mano, se sobreescribe en cada `hueman set`.
foreground            #cdd6f4
background            #1e1e2e
selection_foreground  #1e1e2e
selection_background  #f5e0dc
```

## Si algo falla

Una paleta inexistente termina con exit 1 y lista las disponibles:

```text
ERROR: Paleta no encontrada: no-existe. Disponibles: arctic-ice, autumn, ...
```

(La lista real incluye todas las paletas.) Más casos en
[Troubleshooting](troubleshooting.md).

## Siguiente

- Una app sin template empaquetado: [Agregar soporte a una tool](guides/add-a-tool.md).
- Tu propia paleta: [Agregar una paleta](guides/add-a-palette.md).
- Referencia de comandos: [CLI](cli.md).
