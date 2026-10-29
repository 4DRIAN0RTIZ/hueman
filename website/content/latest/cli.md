# CLI

```text
hueman [--config PATH] init [--force]
hueman [--config PATH] [--var NAME=VALUE ...] list
hueman [--config PATH] [--var NAME=VALUE ...] status
hueman [--config PATH] [--var NAME=VALUE ...] set <palette> [--dry-run] [--only NAME[,NAME...]]
hueman [--config PATH] [--var NAME=VALUE ...] sync [-q|--quiet]
```

## Global options

These go before the subcommand.

| Option | Effect |
|--------|--------|
| `--config PATH` | Config file (see [Configuration](configuration.md)) |
| `--version` | Print the installed version and exit |
| `--var NAME=VALUE` | Define or override a `vars:` value for `${NAME}` in path keys. Repeatable. Example: `hueman --var repo=~/dotfiles set <palette>`. Invalid form (no `=` or invalid name) exits 2 |

## `init`

Writes the packaged example config to the resolved config path
(`--config`, `HUEMAN_CONFIG`, `./hueman.config.yaml`, or
`~/.config/hueman/config.yaml`), creating missing directories. Works without an
existing config. If the file already exists, exits 1 and leaves it alone unless
`--force`.

## `list`

Available palettes (packaged + `palette_dirs`), alphabetical. Without a config
file, lists packaged ones only.

## `set <palette>`

Renders every target, writes outputs, runs `reload` per target that actually
wrote, then `post_apply`. Persists the palette name in `state_file`. With
`state_sync`, publishes `{palette, revision}` (not on `--dry-run` or `--only`).

| Flag | Effect |
|------|--------|
| `--dry-run` | No writes, no dirs, no real reload; prints the plan |
| `--only` | Only targets whose name matches (comma or `fnmatch` glob). Does not write state or run `post_apply`. No match → exit 1 |

If a target fails because the palette lacks a key it needs (`palette_key` with
`extra_vars`, or the `json_scheme_upsert` section), it is skipped with a warning
that names the target and key; the rest continue and `set` exits 1.

## `status`

Active palette and, with `state_sync`, revisions and drift (`in sync`, `behind`,
`ahead`, `no remote state`, `remote unreachable`).

## `sync`

Pulls remote state and applies when the remote revision is higher. Meant for
shell startup (`-q`). No network / no `state_sync` → exit 0 with a notice. An
unknown placeholder in `reload`/`post_apply` yields the same clean
`Config invalida` error (exit 1, no traceback) and the revision does not
advance. If the remote palette is missing locally (or its name is invalid),
`sync` warns, does not advance the revision, and exits 0.

## Exit codes (summary)

- Invalid config or palette (including undefined `${name}`) → 1  
- Invalid `--var` form → 2  
- Target render/write error → 1  
- `reload_failure: error` and hook ≠ 0 → 1 (the rest still runs best-effort)  
- `reload_failure: warn` → 0 even if the hook fails  
