# Architecture

CLI layers (no per-app branching):

| Module | Role |
|--------|------|
| `hueman/cli.py` | CLI and orchestration (entry point `hueman`, also `python3 -m hueman`) |
| `hueman/engine/config.py` | Config load and logger |
| `hueman/engine/palettes.py` | Palette precedence and loading |
| `hueman/engine/targets.py` | Declarative Target / PatchSpec model |
| `hueman/engine/render.py` | Jinja, overwrite, patch |
| `hueman/engine/colors.py` | `contrast` / `is_dark` filters |
| `hueman/engine/reload.py` | Best-effort hook execution |
| `hueman/engine/fsutil.py` | Atomic writes |
| `hueman/engine/statesource.py` | StateSource (git / file) |

Principle: **tool-specific logic lives in YAML + Jinja**, not Python branches.
That is why [adding a tool](guides/add-a-tool.md) does not require patching the
engine.

## Self-contained repo

The repo is self-contained on purpose: nothing inside it imports code from
outside itself, except the external config file each user provides. A
dotfiles repo that uses it only needs `hueman` installed and its own
`hueman.config.yaml` (see [Configuration](configuration.md)).
