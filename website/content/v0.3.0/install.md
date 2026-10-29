# Install

## Requirements

- Python 3.9 or newer
- Dependencies (Jinja2 and PyYAML) install with the package

## Install

The package is `hueman-cli`; it provides the `hueman` command. For a CLI tool,
`pipx` is recommended — it isolates the install in its own environment:

```sh
pipx install hueman-cli
```

Or with pip:

```sh
python3 -m pip install hueman-cli
```

Verify:

```sh
hueman --version
hueman --help
```

`python3 -m hueman` also works if the command is not on your `PATH`.

## From source

To contribute, or if the package is not on your index yet:

```sh
git clone https://github.com/NeanderTeam/hueman.git
cd hueman
pip install -e .
hueman --version
```

The version comes from git tags. On a development checkout, `./init.sh` runs
smoke checks and the test suite.

## User config

hueman **does not** ship your machine map. You need your own config:
`hueman init` writes a commented example to the default path, and will not
overwrite an existing file unless you pass `--force`:

```sh
hueman init
```

hueman resolves the config in this order:

1. `hueman --config /path/to/config.yaml`
2. `HUEMAN_CONFIG` environment variable
3. `~/.config/hueman/config.yaml`

The current working directory is never searched (a config can run commands).

## Verify

```sh
hueman --config /path/to/config.yaml list
hueman --config /path/to/config.yaml set <palette> --dry-run
```

## Upgrade

Use the same tool you installed with:

```sh
pipx upgrade hueman-cli          # if you used pipx
python3 -m pip install -U hueman-cli   # if you used pip
```

Check the version with `hueman --version`. Your config is left alone; see the
[changelog](changelog.md) for what changed between releases.

## Uninstall

```sh
pipx uninstall hueman-cli        # if you used pipx
python3 -m pip uninstall hueman-cli    # if you used pip
```

Uninstall only removes the package. It **does not** delete anything hueman
wrote outside it:

- **Your config**: `~/.config/hueman/config.yaml` (or the path you used with
  `--config` / `HUEMAN_CONFIG`).
- **Active theme**: the `state_file` (default `~/.config/hueman/current`) and,
  if you use `state_sync`, its revision at `<state_file>.revision`.
- **`state_sync` git workdir**: a bare repo under
  `$XDG_STATE_HOME/hueman/state-sync/` (default
  `~/.local/state/hueman/state-sync/`), unless you set `workdir`. The remote
  `hueman-state` branch is not deleted either.
- **Generated files** under each target `outputs` (kitty, tmux, …), plus
  `logging.file` if you set one. `patch` targets change a block inside a file
  you own: hueman does not roll that back.

To find them, read your config *before* uninstalling: paths live in `outputs`,
`state_file`, `logging.file`, and `state_sync`. `hueman status` reports how many
outputs exist on disk. Then delete what you no longer want by hand:

```sh
rm -r ~/.config/hueman
rm -r ~/.local/state/hueman      # only if you used git state_sync
```

Check before deleting: if your targets generate configs other tools still use,
those keep the last applied theme.
