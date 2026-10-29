# Configuration

YAML file owned by the **user** (not machine truth inside the hueman repo).
Commented schema: `hueman init` (`hueman/data/hueman.config.example.yaml`).

## Top-level keys

| Key | Role |
|-----|------|
| `vars` | `${name}` variables for paths (see [Variables](#variables)) |
| `state_file` | Where the active palette name is stored |
| `palette_dirs` | Custom palettes (win by name) |
| `template_dirs` | Custom templates (win by file name) |
| `reload_failure` | `warn` (default) or `error` for hooks |
| `state_sync` | Opt-in multi-node sync (`type: git` \| `file`) |
| `targets` | Name → target map |
| `post_apply` | List of command strings after a full `set`; a bare string is rejected |
| `logging` | `level` (default `INFO`) and optional `file` (file log in addition to stderr). `level` must be DEBUG, INFO, WARNING, ERROR, or CRITICAL; the `file` directory must exist and be writable |

## File resolution

1. `--config`  
2. `HUEMAN_CONFIG`  
3. `~/.config/hueman/config.yaml`  

The current directory is **intentionally not** searched: a config can run
commands (`reload`, `post_apply`), and running hueman inside someone else's
repo must not pick up that repo's `hueman.config.yaml`. If you want a config
next to a project, pass it explicitly with `--config`.

## Placeholders in `reload` / `post_apply`

Commands accept `{name}` (alias `{palette}`) and `{section.key}` (dotted
lookup in the active palette, e.g. `{kitty.color4}`). Values are inserted with
`shlex.quote`. `${VAR}`, `$(...)`, and braces without a dot (e.g.
`find -exec {} +`) are left alone. An unknown `{section.key}` yields a clean
`Config invalida` error (exit 1) before writing anything.

```yaml
reload: "python3 ~/x.py --name {name} --color {kitty.color4}"
```

With `set --dry-run`, expanded `post_apply` commands are printed.

## `reload` / `post_apply` failures

Each command's exit code is logged. `reload_failure` (`warn` by default, or
`error`) decides what happens when one exits ≠ 0; each target may override it,
and `post_apply` uses the global policy.

- `warn`: log a warning and `set` exits 0.
- `error`: log an error, the remaining steps still run (best-effort), and
  `set` exits 1.

A write error (permissions, full disk) is a clean target error (log + exit 1)
and the original file is left intact.

## State file

`state_file` stores the active palette name (one line). It is written only on a
full, real `set`: not on `--dry-run`, not with `--only`. `status` and `{name}`
in hooks use that name. With `state_sync`, the local revision lives separately
at `<state_file>.revision` (see [Sync across nodes](state-sync.md)).

## Using with a dotfiles repo

The engine knows nothing about your paths: the whole map lives in a config you
keep in your dotfiles repo.

1. Store the config (and your `palettes.custom/` / `templates.custom/`) in the
   repo, e.g. `~/dotfiles/hueman/config.yaml`.
2. Symlink that directory as `~/.config/hueman`
   (`ln -s ~/dotfiles/hueman ~/.config/hueman`) so `set` finds the config
   without flags.
3. Optional: your own wrapper if you need a fixed interpreter, e.g.
   `exec python3 -m hueman "$@"` from a specific environment.

Schema or invalid YAML errors → clear message and exit 1 (no traceback).

## Variables

`vars` defines reusable values so full paths are not repeated; the target repo
changes in one place:

```yaml
vars:
  repo: "~/dotfiles"
targets:
  kitty:
    template: kitty.conf.j2
    palette_key: kitty
    outputs:
      - "${repo}/kitty/theme.conf"
```

Rules:

- `vars` is a name → string map. Names match `[A-Za-z_][A-Za-z0-9_]*`.
  A non-string value or invalid name is a config error.
- `${name}` is substituted **only** in path keys: each target's `outputs` and
  `skip_unless_path_exists`, and top-level `state_file`, `palette_dirs`, and
  `template_dirs`. Substitution happens before expanding `~`.
- **Not** substituted in `reload`, `post_apply`, patch regex/markers,
  `extra_vars`, or template bodies (in `reload`/`post_apply`, `${VAR}` remains
  shell).
- An undefined `${name}` in a path key is a config error
  (`Config invalida: ...`, exit 1) that names the variable and where it was used.
- Values may include `~`, but do not nest: a `${...}` inside a variable value
  is an error.
- A `$` that is not exactly `${name}` (e.g. `$HOME`) is left as-is.
- An empty value is valid and substitutes to an empty string.
- `--var NAME=VALUE` on the command line (see [CLI](cli.md)) overrides or adds
  variables on top of the file.

## Targets

See [Targets and render](targets.md) and
[Add support for a tool](guides/add-a-tool.md).
