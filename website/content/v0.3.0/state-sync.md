# Sync across nodes

Opt-in via `state_sync` in the config. Publishes `{palette, revision}` so other
machines can converge with `hueman sync`. Without the key, nothing changes.
Examples assume the `hueman` command is installed (see [Install](install.md)).

## Backends

The backend is chosen with `state_sync.type`; the abstract interface is
`StateSource` (`hueman/engine/statesource.py`) and the engine only uses it through
`build_source`. An unknown type is a config error that lists the valid ones.

### `type: git` (default)

```yaml
state_sync:
  type: git                 # default; configs without `type` behave the same
  repo: "~/dotfiles"        # repo used to resolve the remote URL
  remote: origin            # default
  branch: hueman-state      # default
  # timeout: 15             # seconds per git call (default 15)
```

- Every full `set` publishes `{palette, revision}` on the orphan
  `hueman-state` branch of the remote: a single rewritten commit and
  `push --force-with-lease`.
- On push rejection it fetches: the higher `revision` wins; ties go to the
  accepted push, with bounded retries.
- hueman uses its own bare git repo under `$XDG_STATE_HOME/hueman/` (or
  `workdir`) and **does not touch your working tree**.
- Without git, a remote, or network, `set` applies locally and warns.

### `type: file`

```yaml
state_sync:
  type: file
  path: "~/Sync/hueman.state.yaml"   # folder synced by Syncthing/Dropbox
```

Stores the same `{palette, revision}` with atomic writes; the higher
`revision` wins and ties go to the last accepted write. If the folder is
missing (not mounted) it counts as unreachable and is not created.

HTTP backend: pending (needs a server compare-and-set protocol).

### Backend contract

Covered by `tests/test_state_source_contract.py`: never throws, bounded time,
monotonic `revision` (higher wins; ties go to the accepted write),
`read_result()` distinguishes "reachable but empty" from "unreachable", and
`write()` only returns True if the state was actually published.

## Commands

- `set` publishes after applying. `--dry-run` and `--only` neither write nor
  push state.
- `sync` applies only if the remote revision is higher than local.
- `status` shows local revision, remote revision, and drift.

### `sync`

Fetches `hueman-state`. If the remote `revision` is higher, applies the
palette (without publishing a new revision) and stores the local revision.
Otherwise it does nothing: no writes, no reload (idempotent). The local
revision lives at `<state_file>.revision`; `state_file` remains only the
palette name, and `set` updates the revision when publishing.

If remote state names a palette that does not exist on this node, `sync`
emits a notice (`la paleta remota '<name>' no esta disponible localmente`),
writes nothing, does not advance the local revision, and exits 0
(`unknown-palette`), so shell startup is not broken. Remote state whose
palette name is invalid (path, `..`) is treated as unreadable remote state.

Meant for shell startup:

- Quiet when nothing changed; never hangs (each git call has a timeout,
  `state_sync.timeout`, default 15 s; ssh with `BatchMode`).
- Only exits non-zero on real errors (missing palette, failed target under
  `reload_failure`).
- No network, no remote, or no `state_sync` exits 0 with a stderr notice;
  `-q/--quiet` silences them.
- Never applies local-cache data when the remote is unreachable.

### Drift in `status`

| Drift | Meaning |
|-------|---------|
| `in sync` | Local and remote share the same revision |
| `behind` | Remote is newer: run `sync` |
| `ahead` | Local is newer and not published |
| `no remote state` | Remote is reachable but has no state yet |
| `remote unreachable` | Could not read the remote; remote revision is marked `local cache` |

## Two machines, step by step

1. On each node, add `state_sync` to its config (same `repo`/`remote`, or the
   same `path` for `type: file`).
2. On node A run a full `set`:
   `hueman --config PATH set <palette>`. The first time creates the orphan
   `hueman-state` branch and publishes revision 1.
3. On node B run `hueman --config PATH sync`: applies the palette and stores
   the local revision.
4. `hueman --config PATH status` on both should show `in sync`.

`set --dry-run` and `set --only` never publish, so they cannot seed state.

## Run `sync` automatically

```sh
# 1. Shell startup (~/.zshrc or ~/.bashrc)
hueman sync -q

# 2. systemd user timer (~/.config/systemd/user/hueman-sync.{service,timer})
#    [Service] ExecStart=/path/to/hueman sync -q
#    [Timer]   OnBootSec=1min  OnUnitActiveSec=15min
#    systemctl --user enable --now hueman-sync.timer

# 3. cron
*/15 * * * * /path/to/hueman sync -q

# 4. git hook in your dotfiles repo (.git/hooks/post-merge)
#!/bin/sh
hueman sync -q
```

Adjust `hueman` or the absolute CLI path to your install (`command -v hueman`;
systemd and cron do not load your shell `PATH`).
