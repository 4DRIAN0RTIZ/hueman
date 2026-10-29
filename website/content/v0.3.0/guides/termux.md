# Termux and proot

Termux reads its colors from `~/.termux/colors.properties`. hueman can
generate that file with the packaged template `termux_colors.properties.j2`,
which uses the palette's `kitty` section (`foreground`, `background`,
`cursor`, and `color0`–`color15`).

## Target

```yaml
targets:
  termux:
    template: termux_colors.properties.j2
    palette_key: kitty
    mode: overwrite
    outputs:
      - "~/.termux/colors.properties"
    # In proot, point at the real Termux file, not a symlink.
    # Only if hueman runs in Termux (not proot): see below.
    # reload: "termux-reload-settings"
```

The result is one `key=#rrggbb` per line, unquoted, preceded by a `#`
comment. The file is fully overwritten on every `hueman set`.

`reload` is a per-target command: it runs with `sh -c` only after an
effective write (not on `--dry-run`, and not if every output was skipped).
A failure is logged according to `reload_failure`.

## Inside proot

In a proot distro (for example Debian or Arch under `proot-distro`) there is
no `termux-reload-settings`, so a direct `reload` fails. Two pieces fix that:

1. `outputs` must point at the **real file** Termux reads, as seen from
   proot. If Termux's home is mounted inside proot (e.g. at `~/baseTermux`),
   use `~/baseTermux/.termux/colors.properties`.
2. A watcher on the Termux side watches mtime and reloads.

> **Do not use a symlink as an output.** hueman writes atomically (temp file
> + `os.replace`), and if the destination is a symlink it **replaces it with
> a regular file** and leaves the old target untouched. Termux would keep
> reading the old file. Point `outputs` at the final file, not a link.

Save this as `~/.termux/theme-watcher` on **Termux** (not proot) and
`chmod +x` it:

```bash
#!/data/data/com.termux/files/usr/bin/bash
# theme-watcher: watch colors.properties and reload Termux when it changes
COLORS="$HOME/.termux/colors.properties"
LOCKFILE="$HOME/.termux/.theme-watcher.pid"
if [ -f "$LOCKFILE" ] && kill -0 "$(cat "$LOCKFILE")" 2>/dev/null; then exit 0; fi
echo $$ > "$LOCKFILE"
trap "rm -f $LOCKFILE" EXIT
LAST_MTIME=$(stat -c %Y "$COLORS" 2>/dev/null)
while true; do
    sleep 2
    CURRENT_MTIME=$(stat -c %Y "$COLORS" 2>/dev/null)
    if [ -n "$CURRENT_MTIME" ] && [ "$CURRENT_MTIME" != "$LAST_MTIME" ]; then
        termux-reload-settings
        LAST_MTIME="$CURRENT_MTIME"
    fi
done
```

The lockfile avoids duplicate instances. To start it every session, add to
Termux's `~/.bashrc`:

```bash
~/.termux/theme-watcher &>/dev/null &
```

In that setup, omit `reload` on the target: the watcher handles it.

## Checklist

- [ ] The palette has a `kitty` section with all 19 keys.
- [ ] `outputs` points at `~/.termux/colors.properties` and the `~/.termux`
      directory exists (or let hueman create it).
- [ ] In proot: `outputs` is the real file Termux reads, not a symlink.
- [ ] The watcher lives on the Termux side, is executable, and is running
      (`cat ~/.termux/.theme-watcher.pid`).

## Diagnosis

- **Colors do not change in Termux**: restart the session or run
  `termux-reload-settings` by hand. If that works, the watcher is the problem.
- **`reload` fails in proot with exit 127**: `termux-reload-settings` is not
  there; drop `reload` and use the watcher.
- **Watcher does not start**: a stale `.theme-watcher.pid` is ignored if the
  process is gone; check execute permissions and the shebang path.
- **Missing key**: if a custom palette omits `cursor` or `colorN`, that
  target fails (warning and exit 1); copy keys from a packaged palette.

## See also

- [Targets and render](../targets.md)
- [Add a palette](add-a-palette.md)
