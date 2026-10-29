# Hueman documentation site

Static documentation portal (`#15`–`#19`): versioned Markdown content plus a
zero-build HTML shell that loads it in the browser.

## Preview locally

Serve **this directory** over HTTP (fetch does not work from `file://`):

```sh
python3 -m http.server 8765 --directory website
# open http://127.0.0.1:8765/
```

Deep links use query params (section anchors keep the URL hash):
`?v=latest&p=add-tool`, `?v=v0.1.0&p=cli#checklist-rapido`.

Legacy `#/latest/add-tool` hashes are still accepted and rewritten.

## Deploy

The site is plain static files; there is no build step. Publish the contents of
`website/` as the web root of `hueman.cuevaneander.tech`:

- Any static file server works. All asset and content paths are relative and
  routing uses query params, so no rewrite or fallback rule is needed.
- Serve over HTTPS and make sure `.md`, `.json` and `.js` files are served
  (the portal fetches `content/`, `data/` and `assets/js/` at runtime).
- The portal requests `content/` and `data/` with `cache: "no-cache"`, so a
  revalidating cache is fine; avoid long `max-age` on those paths or visitors
  will see stale docs after a release.
- `index.html` points its canonical URL and Open Graph tags at
  `https://hueman.cuevaneander.tech/`; change them if the domain changes.
- Smoke test after publishing: open `/`, `/?p=install`, `/?v=v0.1.0&p=cli`
  and `/robots.txt`.

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

## Shell layout

| Path | Role |
|------|------|
| `index.html` | Portal chrome |
| `assets/css/site.css` | Layout, typography, responsive nav |
| `assets/js/app.js` | Version/page router, Markdown render, nav |
| `assets/js/marked.min.js` | Vendored Markdown parser (no build step) |
| `data/versions.json` | Version registry |
| `data/changelog.md` | Changelog copy for the portal |
| `content/<version>/` | Versioned Markdown + `nav.json` |

OpenWiki (`openwiki/`) remains generated evidence, not this user-facing site.
The shell does not change the Python CLI.
