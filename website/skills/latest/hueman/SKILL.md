---
name: hueman
description: "Operate hueman, a Python CLI (hueman.py) that turns one YAML palette plus Jinja2 templates into config files for the user's apps. Use when the user mentions hueman or asks to apply, switch, inspect or sync a hueman theme, to find out why a hueman target was skipped, or to add a template, target or palette to a hueman setup. Do NOT use when hueman is not mentioned, or when the user only wants some colors in a one-off config file."
license: MIT
metadata:
  version: "0.1.0"
  compatible-with:
    hueman: ">=0.1.0"
---

# hueman

hueman reads a palette (`palettes/<name>.yaml`) and renders Jinja2 templates into the files declared in the user's own `hueman.config.yaml`. It is not a dotfile manager: it installs, links and versions nothing, and it never guesses paths. This skill teaches you to operate it safely. The installed `hueman.py` is the authority for syntax; this file is only guidance.

Versioning: this file is versioned by the git tag of the hueman repo (`skills/hueman/SKILL.md` at tag `vX.Y.Z`). `metadata.version` is the hueman release it describes. If a flag or message here disagrees with the installed tool, trust the tool and say so.

## Learn the CLI from the tool

Do not guess flags or subcommands. Run:

```sh
python3 hueman.py --help
python3 hueman.py <subcommand> --help
```

Run it from the hueman repo root. Do not assume a `hueman` binary is on `PATH`. `--config <path>` is a global option and goes before the subcommand. Always pass it explicitly; the implicit order is `--config`, `$HUEMAN_CONFIG`, `./hueman.config.yaml`, `~/.config/hueman/config.yaml`.

Subcommands at the time of writing: `list`, `status`, `set <palette> [--dry-run] [--only NAME[,NAME]]`, `sync [-q]`. If `--help` shows others, use the help text.

## Standard sequence

```sh
python3 hueman.py --config CFG list                      # palettes, read-only
python3 hueman.py --config CFG status                    # active theme, outputs found on disk
python3 hueman.py --config CFG set PALETTE --dry-run     # plan, writes nothing
python3 hueman.py --config CFG set PALETTE               # real apply
```

1. Run `list` and `status` first. They are read-only.
2. Run `set ... --dry-run` and show the user every `[DRY RUN] escribiría <path>` line plus any `post_apply` lines.
3. Run the real `set` only after the user explicitly approves that list. `set` writes outside the repo: every `outputs` path, the `state_file` (default `~/.config/hueman/current`), and runs `reload`/`post_apply` shell commands.
4. `sync` also writes outside the repo (it applies a remote palette). Ask first. Without `state_sync` configured it only warns and exits 0.
5. Report the exit code. Exit 1 means a config problem or at least one target failed, even if other targets were written.

`--dry-run` writes nothing, creates no directories, runs no `reload`, saves no `state_file`, publishes no state. It still prints the `post_apply` commands that would run.

`--only a,b` (or repeated `--only`) limits `set` to targets by name or `fnmatch` glob. It does NOT save the `state_file`, does NOT run `post_apply`, does NOT publish state. It is a partial re-render: use it to test one target, never to "switch theme". If nothing matches, exit 1 and the valid names are printed.

## Safety rules

- Dry-run first, always, and show the paths. Never run a real `set` or `sync` without explicit approval of those paths.
- Never write real user paths, secrets or machine-specific config into the hueman repo. Use `hueman.config.example.yaml` or a temp fixture, and keep the real config where the user keeps it.
- Never add hostname/environment detection or per-tool Python branches. Tool-specific logic lives in YAML + Jinja.
- `mode: patch` never creates a file: a missing output is skipped with an INFO line, not an error. Tell the user instead of creating the file yourself.
- `reload` (per target, only after an effective write) and `post_apply` (once, at the end of a full `set`) are best-effort shell commands (`sh -c`). A failure logs a warning and does not stop the rest, unless `reload_failure: error`, which makes the exit code 1. Never treat them as validation.
- Do not promise that `--only` persists state or that patch creates files.
- If you change the repo, follow its conventions: Conventional Commits, no hand edits to `CHANGELOG.md`.

## Known sharp edges

- Unknown `palette_key`: if the target's `palette_key` is not a top-level section of the palette, the target is skipped with an INFO line `... la paleta no tiene la seccion '<key>', omitido` (exit 0, not an error). Compare it with the palette's top-level keys.
- Bad `{section.key}` placeholder in `reload` or `post_apply` is a clean `Config invalida: placeholder desconocido ...` error (exit 1, no traceback), raised before anything is written (no outputs, no `state_file`, no reload); it also applies under `--dry-run`. With `--only`, only the selected targets' `reload` is validated. `{name}` and `{palette}` are always valid; shell `${VAR}` is left alone.
- Non-idempotent `regex_splice`: if `marker_regex` (or the `marker_begin`/`marker_end` pair) does not match the file, the rendered block is appended at the end. If the appended block then still does not match the marker, every run appends another copy. Verify the marker matches an existing block, and use `(?m)` when anchoring with `^`/`$`.
- Missing template variables render as empty text, not an error. Missing `extra_vars` paths or `json_scheme_upsert` keys skip that target and make the exit code 1.
- Targets are skipped without error when `skip_unless_path_exists` or `skip_if_missing_parent` is not satisfied.

## Diagnosing a skipped target

1. Re-run `set PALETTE --dry-run --only TARGET` and read the INFO/WARNING lines (`omitido`, `no existe`, `no encontrado`, `plantilla ... no encontrada`, `no tiene la clave ... requerida`).
2. No line at all: suspect `palette_key` (sharp edge above).
3. Check that the output exists (patch mode) and that `skip_*` conditions hold.
4. Check template names against `template_dirs` (user dirs win) and `templates/`.
5. Report the config path used, the exact output, and the exit code. Do not retry blindly with a real `set`.

## Adding a template, target or palette (locally)

- Keep user additions outside the repo: a directory in `template_dirs` / `palette_dirs` of the user's config. User files win over packaged ones with the same name. Packaging upstream is optional.
- Template: a `.j2` file that sees only the palette section named by `palette_key`, plus `theme_name` and `extra_vars`. Filters: `contrast`, `is_dark`. Use `jinja_delimiters` if the target format already uses `{{ }}`.
- Target: an entry under `targets:` with `template`, `palette_key`, `mode` (`overwrite` default, or `patch`), explicit `outputs`. Copy a working target from `hueman.config.example.yaml` instead of inventing keys.
- Palette: copy a packaged YAML and change values only; keep the keys templates read. Confirm it appears in `list`.
- Validate with `set PALETTE --dry-run --only NEWTARGET`, show the paths, then get approval for the real run.

## When not to use this skill

- The user did not mention hueman or its theming workflow.
- The user wants colors in a single config once (edit that file directly).
- The user asks about a different theming tool or a dotfile manager.
