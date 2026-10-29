# hueman for agents

Playbook for you, coding agent, when someone asks for help with hueman. Guide
them to install, configure, apply a theme, and diagnose failures. If anything
here contradicts the code or the docs, the code wins: verify it.

To operate hueman yourself (apply, inspect, diagnose), use the Agent Skill
`skills/latest/hueman/SKILL.md`: this guide teaches you how to guide a person;
the skill teaches you how to run hueman.

Static site under `website/`: the bare URL (`/` or `index.html` with no query) is
the product **landing**. Docs live in the same `index.html` SPA with
`?v=<version>&p=<pageId>` (e.g. `?p=intro`, `?v=latest&p=install`). Page ids:
`intro`, `install`, `quickstart`, `cli`, `configuration`, `targets`, `palettes`,
`state-sync`, `add-tool`, `add-palette`, `termux`, `windows`, `architecture`,
`troubleshooting`, `changelog`.

## The idea in five lines

- **One palette. Every tool.** hueman is a Python CLI (package `hueman-cli`,
  command `hueman`) that applies one theme across the apps you declare.
- The map “which template goes to which file” lives in the user’s own
  `hueman.config.yaml`. hueman does not guess paths, hostname, or environment.
- It is not a dotfiles manager: it does not install, link, or version anything.
  It only writes colors to the paths in `outputs`.
- One palette feeds many targets. Switching theme is a `set`.
- Supporting a new app is a template + a target, not an engine change
  (`p=intro`, `p=architecture`).

## Vocabulary, in the order worth explaining

1. **Palette**: YAML under `hueman/palettes/` (packaged) or `palette_dirs` (user).
   Name is the file without `.yaml`; on a name clash the user one wins. Typical
   sections: `meta`, `kitty` (`color0`–`color15`, cursor…), `polybar`
   (`background`, `background_alt`, `foreground`, `primary`, `secondary`,
   `alert`, `success`, `warning`, `muted`). `p=palettes`
2. **Template**: `.j2` under `hueman/templates/` or `template_dirs` (user wins).
   Sees only the palette section given by `palette_key`, plus `theme_name` and
   `extra_vars`. Filters: `contrast`, `is_dark`.
3. **Target**: entry under `targets:` with `template`, `palette_key`, `mode`,
   `outputs` (explicit paths) and optionals (`reload`, `reload_failure`,
   `make_executable`, `skip_if_missing_parent`, `skip_unless_path_exists`,
   `jinja_delimiters`, `extra_vars`, `patch`). `p=targets`
4. **Mode**:
   - `overwrite` (default): the file belongs to hueman; fully replaced, atomic
     write, parents created.
   - `patch`: the file belongs to the user; hueman only touches a block
     (`regex_splice` with `marker_regex` or `marker_begin`/`marker_end`; or
     `json_scheme_upsert`, which uses the `kitty` section and needs no
     template). **Never creates the file**: if missing, it is skipped.
5. **`reload` / `post_apply`**: `reload` is per target, only after an effective
   write; `post_apply` runs once at the end of a full `set`. They accept
   `{name}`/`{palette}` and `{section.key}` (palette value, shell-quoted).
   Best-effort: a failure does not stop the rest. `reload_failure` (`warn` by
   default, or `error`) decides whether a failure yields exit 1.
6. **`state_sync`** (opt-in): publishes `{palette, revision}` so other machines
   converge with `sync`. Backends `git` (orphan branch, default `hueman-state`)
   and `file`. `p=state-sync`

## First session with the human

Before touching anything, ask (one thing at a time) where their config lives or
will live, and which apps they want themed. `set` writes **outside the
project**: every `outputs` path and `state_file` (default
`~/.config/hueman/current`). Do not run a real `set` without their explicit OK
on the path list.

**Install** (`p=install`). Needs Python >= 3.9. Install with
`pipx install hueman-cli` (recommended for a CLI) or `pip install hueman-cli`;
from source: `git clone https://github.com/NeanderTeam/hueman.git && cd hueman && pip install -e .`.
Jinja2 and PyYAML come as dependencies. The command is `hueman`, but do not
assume it is on `PATH`: check with `hueman --version` or `command -v hueman`.
If not, from a source checkout use `python3 -m hueman ...` from the repo root.

**Config.** hueman does not ship a machine map; start from the packaged
example: `hueman init` (use `--config <path>` to choose where; does not
overwrite without `--force`). Always pass `--config <path>` so you do not
depend on implicit resolution.

**Sequence** (`p=quickstart`, `p=cli`):

```sh
hueman --config <path> list                    # palettes, alphabetical
hueman --config <path> status                  # active theme, outputs on disk
hueman --config <path> set <palette> --dry-run # plan, no writes
hueman --config <path> set <palette>           # apply
```

- `--dry-run` prints `[DRY RUN] escribiría <path>` per output and the
  `post_apply` commands that would run. It does not write, create directories,
  run `reload`, save `state_file`, or publish state. Show that list and wait
  for approval.
- `set <palette> --only a,b` limits targets by name or `fnmatch` glob
  (repeatable flag). Does not save `state_file`, run `post_apply`, or publish.
  If nothing matches: exit 1 with the valid names. Use it to test a new target.
- `sync [-q]` applies remote state only if its revision is higher; with no
  network or no `state_sync` it warns and exits 0.

## Configuration in one screen

Path resolution order: `--config`, `HUEMAN_CONFIG`, `~/.config/hueman/config.yaml`.
The current directory is not searched (a config can run commands). If missing:
`Config no encontrada: <path>`, exit 1. Invalid YAML or schema:
`Config invalida: ...`, exit 1, no traceback.

Top-level keys (`p=configuration`): `state_file`, `palette_dirs`,
`template_dirs`, `reload_failure`, `state_sync` (`type: git` with
`repo`/`remote`/`branch`/`workdir`/`timeout`, or `type: file` with `path`),
`targets`, `post_apply`.

## Extending

- **New app**: template in a user `template_dirs` + target in their config.
  Start local; packaging upstream is optional. Test with
  `set <palette> --dry-run --only <target>`, then without `--dry-run`. Guide:
  `p=add-tool`.
- **New palette**: YAML in a `palette_dirs`; copy a packaged one and change
  hex values, keeping the keys templates read. Confirm with `list`. Guide:
  `p=add-palette`.
- No `if tool == ...` branches in Python: tool-specific logic lives in YAML +
  Jinja.

## Diagnosis: symptom, cause, check

Gather first: config path in use, full output, exit code. Official summary:
`p=troubleshooting`.

| Symptom | Cause (verified in code) | Check |
|---|---|---|
| `Config no encontrada` | No path in the resolution order exists | `echo "$HUEMAN_CONFIG"`; `hueman init` or pass `--config` |
| Palette missing / `Paleta no encontrada` | File is not `.yaml`, dir absent from `palette_dirs`, or invalid YAML (`Paleta invalida`, exit 1) | `list`; the error lists available names |
| `plantilla '<x>' no encontrada` | Wrong `.j2` name or outside `template_dirs`/`hueman/templates/`; target skipped, exit 1 | Exact file name |
| Target does not write and no error | `skip_unless_path_exists` or `skip_if_missing_parent` not met; `patch` on a missing file; `--only` or `--dry-run` | INFO lines `omitido` / `no existe` |
| INFO `... la paleta no tiene la seccion '<key>', omitido` | `palette_key` is not a top-level palette section (exit 0, not an error) | Compare `palette_key` with the YAML top-level keys |
| `la paleta '<x>' no tiene la clave '<k>' requerida` | Missing `extra_vars` path or `json_scheme_upsert` key; target skipped, exit 1 | Add the key to the palette |
| Empty values in the output | Missing template variable in the section: Jinja renders empty, does not fail | Diff `.j2` variables against the section |
| Literal `{{ ... }}` in the output | Delimiters other than expected | Target `jinja_delimiters` |
| Patch duplicates the block | `marker_regex` with no match and no `insert_after_section_regex`: block is **appended**; if the regex still does not match the inserted block, hueman warns (cause is `marker_regex`) | Review the regex; `(?m)` if you use `^`/`$` in `ensure_after` |
| Exit 1 with theme applied | Some target skipped on error, or `reload_failure: error` and a hook returned ≠ 0 | Messages `reload fallo (exit N)` / `post_apply fallo` |
| Reload “does nothing” | Only runs after an effective write and without `--dry-run`; uses `sh -c` | Log shows `reload: <cmd> (exit N)`; have the human run it by hand |
| `set` or `sync` fails with `Config invalida: placeholder desconocido` (before writing; `sync` does not advance revision) | Unknown `{section.key}` in `reload`/`post_apply` | Fix the key; shell `${VAR}` is left alone |
| `sync` does not apply | Remote unreachable, no state, remote palette missing locally (notice, exit 0, revision not advanced) or invalid name, or local revision >= remote (never applies cache) | `status`, `Drift:` line (`in sync`, `behind`, `ahead`, `no remote state`, `remote unreachable`); `type: file` folder is not created |

## Rules for you

- Do not invent flags, keys, target fields, or paths. If it is not here, in the
  docs, or in the code, it does not exist; read `hueman/cli.py` or
  `hueman/engine/*.py` and say so.
- Always propose `--dry-run` first and show the paths before a real `set`. Ask
  confirmation for anything that writes outside the project (`set`, `sync`,
  creating config under `~`).
- Do not write real user paths or secrets into the hueman repo; use
  `hueman.config.example.yaml` or temp fixtures.
- `reload` and `post_apply` are best-effort: do not use them as validation;
  confirm with the log and exit code.
- `patch` does not create files and `--only` does not persist state: do not
  promise otherwise.
- Do not add hostname/environment detection or per-tool logic to the engine.
- If you change the repo: Conventional Commits, branches from `dev`, no hand
  edits to `CHANGELOG.md`.
