# Hueman documentation site (content)

Static documentation for the future portal (`#15`–`#19`). This directory holds
**versioned content and manifests only**; the HTML shell lands in issue `#17`.

## Versions

| id | channel | meaning |
|----|---------|---------|
| `latest` | tip | Editable docs for current mainline |
| `v0.1.0` | release | Frozen copy for the published tag |

Registry: `data/versions.json`. The portal loads that file, then Markdown under
the version's `contentDir`.

## Page map (stable ids)

Ids are anchors/slugs the portal and deep links must keep stable across
versions. Missing a page in an older snapshot is allowed; do not rename ids.

| id | path | audience |
|----|------|----------|
| `intro` | `intro.md` | everyone |
| `install` | `install.md` | new users |
| `quickstart` | `quickstart.md` | new users |
| `cli` | `cli.md` | operators |
| `configuration` | `configuration.md` | operators |
| `targets` | `targets.md` | operators / extenders |
| `palettes` | `palettes.md` | operators / extenders |
| `add-tool` | `guides/add-a-tool.md` | **extenders (primary)** |
| `add-palette` | `guides/add-a-palette.md` | extenders |
| `state-sync` | `state-sync.md` | multi-node |
| `architecture` | `architecture.md` | contributors |
| `troubleshooting` | `troubleshooting.md` | operators |
| `changelog` | derived from root `CHANGELOG.md` | everyone |

`add-tool` is first-class: the product idea is that anyone can theme a new app
with a Jinja template + a declarative target, without touching Python.

## Authoring rules

- Write user-facing docs in **Spanish** (project convention).
- Code, keys, paths, and shell samples stay as-is (English identifiers).
- Do not invent runtime behavior: prefer `README.md`, `hueman.config.example.yaml`,
  packaged templates, and tests as sources of truth.
- Prefer teaching the **custom** path first (`template_dirs` + user config); the
  **packaged** path (PR into this repo) is the optional upstream step.
- No machine-local home paths in examples; use `~/dotfiles/...` placeholders.
- Keep public GitHub issue text high-level; detailed acceptance lives in
  local `feature_list.json` (F9).

## Freeze a release (for `#19`)

1. Tag/release as usual (`dev` → `main` / release workflow).
2. Copy `content/latest/` → `content/vX.Y.Z/`.
3. Append an entry to `data/versions.json` with `channel: release`, freeze
   `updated` to the release date, set `semver`.
4. Leave `latest` as the editable tip; bump its `updated`.
5. Validate: every nav id resolves or is intentionally omitted; internal links
   and anchors work; changelog sections for that tag exist in `CHANGELOG.md`.

## Out of scope here

- Portal chrome, CSS, version selector UI (`#17`, `#18`).
- OpenWiki (`openwiki/`) is generated evidence, not the user-facing site.
- Changing the Python CLI or engine.
