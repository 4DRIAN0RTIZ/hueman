# Sync entre nodos

Opt-in vía `state_sync` en el config. Publica `{palette, revision}` para que
otras máquinas converjan con `hueman sync`.

## Backends

- `type: git` (default) — rama huérfana (default `hueman-state`) en el remoto
  de tu repo de dotfiles; working tree del usuario intacto  
- `type: file` — un YAML en una carpeta ya sincronizada (Syncthing, etc.)  

## Comandos

- `set` publica tras aplicar (no con `--dry-run` / `--only`)  
- `sync` aplica solo si revision remota > local  
- `status` muestra drift  

Sin red o sin clave `state_sync`, `sync` sale 0 con aviso (seguro en
`.zshrc`). Detalle operativo y timers: README del repo.
