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

## Security

Report vulnerabilities privately; see [SECURITY.md](SECURITY.md).
