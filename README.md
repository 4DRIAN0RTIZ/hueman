<p align="center">
  <img src="website/assets/img/logo.png" alt="hueman" width="128" />
</p>

<h1 align="center">hueman</h1>

<p align="center"><strong>One palette. Every tool.</strong></p>

<p align="center">
One theme for your terminal, editor, prompt, and the rest of your setup.<br />
You own the map — which file each app uses — and one command paints it everywhere.<br />
Not a dotfiles manager: output paths live in your own <code>hueman.config.yaml</code>,
outside this repo.
</p>

## Quickstart

```sh
pipx install hueman-cli                               # or: pip install hueman-cli
hueman init                                           # sample config → ~/.config/hueman/config.yaml
# point targets/outputs at your paths, then:
hueman set <palette> --dry-run
hueman set <palette>
```

From source (Python >= 3.9):

```sh
git clone https://github.com/NeanderTeam/hueman.git
cd hueman && pip install -e .
```

Upgrade: `pipx upgrade hueman-cli` (or `pip install -U hueman-cli`).  
Uninstall: `pipx uninstall hueman-cli` (or `pip uninstall hueman-cli`); your
config and generated files are left alone (details in the
[install guide](https://hueman.cuevaneander.tech/?p=install)).

Other commands: `init` (sample config), `list` (palettes), `status` (active
theme), `sync` (shared state across machines).

## Core ideas

- One palette, many targets; output mapping is declarative.
- Packaged templates and palettes are defaults; custom dirs win.
- `overwrite` for full generated files, `patch` for blocks inside hand-edited
  configs.
- Per-target `reload` and global `post_apply`, best-effort, with `warn` /
  `error` policy.
- Optional sync of the active palette across machines (`state_sync`).
- Adding a tool is a template + a target, not an engine change.

## Packaged tools

`hueman/palettes/` and `hueman/templates/` ship 25 generic palettes and
templates for common tools (kitty, tmux, polybar, nvim/nightfox, dunst, bspwm,
yazi, qutebrowser, rofi, fzf, atuin, oh-my-posh, wezterm, starship, Termux,
herdr, and more). For idiosyncratic targets use `template_dirs` in your config
instead of asking them to be packaged here.

## Docs

Full site: **[hueman.cuevaneander.tech](https://hueman.cuevaneander.tech)**  
(`/` = landing, `?p=intro` = docs)

Local preview (sources under `website/`):

```sh
python3 -m http.server 8765 --directory website
```

then open `http://localhost:8765`.

## Support

Bug or idea? Open an issue at
[github.com/NeanderTeam/hueman/issues](https://github.com/NeanderTeam/hueman/issues).

## Repo layout

| Path | Contents |
|---|---|
| `hueman/cli.py` | CLI and orchestration (`hueman` command) |
| `hueman/engine/` | Config, palettes, targets, render, reload, shared state |
| `hueman/palettes/`, `hueman/templates/` | Packaged YAML palettes and Jinja2 templates |
| `hueman/data/hueman.config.example.yaml` | Commented external config example (`hueman init`) |
| `tests/` | Test suite |
| `website/` | Landing + documentation site |

The repo is self-contained: nothing inside imports code from outside itself,
except the external config each user provides. A dotfiles repo only needs
`hueman` installed and its own `hueman.config.yaml`.

## License

MIT, see [LICENSE](LICENSE).
