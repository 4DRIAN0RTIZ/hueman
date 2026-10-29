# Releases and publish retry

Releases come from the `release.yml` workflow when `dev` is merged into `main`.
Jobs:

| Job | What it does |
|---|---|
| `bump` | Computes the version with git-cliff, updates `CHANGELOG.md`, creates the tag and pushes it |
| `release` | Creates the GitHub Release from the tag |
| `publish` | Builds sdist and wheel and uploads to PyPI (Trusted Publishing, `pypi` environment) |
| `sync-dev` | Fast-forwards `dev` to `main` with `git merge --ff-only` |

`bump` only cuts a release when there are `feat`, `fix`, or `perf` commits
(or a `BREAKING CHANGE`) since the last tag. A merge to `main` that is only
docs, CI, or chores publishes nothing. A manual run (`workflow_dispatch`) skips
that check.

## Retry a failed publish

Before retrying, see where it failed:

- **`publish` failed but the tag already exists.** Open the run in the Actions
  tab and use "Re-run failed jobs". Only `publish` runs again: it checks out
  the tag and rebuilds the same code. Do not move the tag or cut another
  version.
- **The tag exists and re-run is not possible** (for example the run is too
  old). Dispatch `workflow_dispatch` on `main` from Actions. Because `bump`
  sees the computed version already matches the latest tag, it reports
  `released=false` and the other jobs are skipped — this path does not
  republish. Push a new `fix:` commit to `main` for a patch version, or upload
  the tag build by hand (see below).
- **PyPI already has the files for that version.** PyPI does not allow
  re-uploading the same filename. Check pypi.org/project/hueman-cli for which
  files exist; if they are all there, there is nothing to retry. If one is
  missing, the action only uses `skip-existing` when configured; by default it
  fails, and the clean fix is a new patch version.
- **`bump` failed before pushing the tag.** Nothing was published: re-run the
  whole workflow with "Re-run all jobs".

Manual upload from the tag, last resort only:

```bash
git checkout vX.Y.Z
python -m pip install build twine
python -m build
twine upload dist/*
```

`sync-dev` fails on purpose if `dev` moved ahead with commits `main` does not
have (for example from the changelog bot). Fix it by hand by merging `main`
into `dev`; do not force-push.
