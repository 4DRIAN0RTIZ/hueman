# Contributing

## Setup

```bash
pip install -e ".[dev]"
python -m pytest -q
```

## Workflow

- Branch from `dev` (`feat/...`, `fix/...`, `docs/...`) and open the PR against `dev`.
- `main` only carries releases; do not target it.
- Use [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `docs:`, `ci:`, `chore:`, `test:`).
- `CHANGELOG.md` is generated from commit messages. Do not edit it by hand.

## Tests

Behavior changes need tests. Writing the failing test first is welcome.
Run `python -m pytest -q` before opening the PR.

## Documentation

The docs live in `website/content/latest` (written in Spanish).

- Add a tool or target: [add-a-tool](website/content/latest/guides/add-a-tool.md)
- Add a palette: [add-a-palette](website/content/latest/guides/add-a-palette.md)

Targets stay declarative: tool-specific logic belongs in YAML and Jinja
templates, not in Python.

### Freezing docs for a release

The site is static (`website/`, no build step). `content/latest` is the editable
tip; each release gets a frozen copy. Page ids in `content/*/nav.json` are used
as URLs (`?p=<id>`), so do not rename them.

1. Cut the release as usual.
2. Copy `website/content/latest/` to `website/content/vX.Y.Z/`.
3. Add an entry to `website/data/versions.json` with `channel: release`, the
   `semver` and the release date as `updated`; bump `updated` on `latest`.
4. Check that every nav id resolves, internal links work and the changelog has a
   section for that tag.

## Security

Report vulnerabilities privately; see [SECURITY.md](SECURITY.md).
