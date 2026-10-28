# hueman

Gestor centralizado de temas: una **paleta de color (YAML)** alimenta
**templates Jinja2** que generan la configuración real de tus herramientas
(kitty, tmux, nvim, starship, Windows Terminal, lo que declares en tu propio
config). Sin dependencias de ningún gestor de dotfiles: todo el mapeo de rutas
de salida vive en un `hueman.config.yaml` propio, fuera de este repo.

## Quickstart

```sh
python3 -m pip install -r requirements.txt            # Jinja2 + PyYAML
cp hueman.config.example.yaml ~/hueman.config.yaml    # ajusta tus targets
python3 hueman.py --config ~/hueman.config.yaml set <paleta> --dry-run
python3 hueman.py --config ~/hueman.config.yaml set <paleta>
```

Otros comandos: `list` (paletas), `status` (tema activo) y `sync` (estado
compartido entre máquinas).

## Ideas centrales

- Una paleta, muchos targets; el mapeo de salidas es declarativo.
- Templates y paletas empaquetados son defaults; los directorios custom ganan.
- `overwrite` para archivos generados enteros, `patch` para bloques dentro de
  configs editadas a mano.
- `reload` por target y `post_apply` global, best-effort, con política
  `warn` / `error`.
- Sync opcional de la paleta activa entre máquinas (`state_sync`).
- Agregar una tool nueva es un template + un target, no un cambio al motor.

## Herramientas empaquetadas

`palettes/` y `templates/` traen ~24 paletas estéticas genéricas y templates
para las herramientas más comunes (kitty, tmux, polybar, nvim/nightfox, dunst,
bspwm, yazi, qutebrowser, rofi, fzf, atuin, oh-my-posh, wezterm, starship,
Termux). Para targets idiosincráticos usa `template_dirs` en tu config en vez
de pedir que se agreguen aquí.

## Documentación

Documentación completa: **[hueman.cuevaneander.tech](https://hueman.cuevaneander.tech)**

Para verla en local (las fuentes están en `website/`):

```sh
python3 -m http.server 8765 --directory website
```

y abre `http://localhost:8765`.

## Estructura del repo

| Ruta | Contenido |
|---|---|
| `hueman.py` | CLI y orquestación |
| `engine/` | Config, paletas, targets, render, reload, estado compartido |
| `palettes/`, `templates/` | Paletas YAML y plantillas Jinja2 empaquetadas |
| `hueman.config.example.yaml` | Ejemplo comentado de config externa |
| `tests/` | Suite de tests |
| `website/` | Sitio de documentación |

El repo es autocontenido: nada dentro importa código fuera de sí mismo, salvo
el config externo que cada usuario provee. Un repo de dotfiles solo necesita
un wrapper apuntando aquí y su propio `hueman.config.yaml`.

## Licencia

MIT, ver [LICENSE](LICENSE).
