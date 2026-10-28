# Qué es hueman

hueman aplica una **paleta YAML** a las configs de tus apps mediante
**templates Jinja2**. El mapeo de salidas es **declarativo** y vive en tu
propio `hueman.config.yaml`: la herramienta no adivina rutas ni depende de un
gestor de dotfiles concreto.

Ideas centrales:

- Una paleta, muchos targets.
- Templates y paletas empaquetados son defaults; los directorios custom ganan.
- Overwrite para archivos generados enteros; patch para bloques en configs
  editadas a mano.
- Reload y post_apply best-effort, con política `warn` / `error`.
- Sync opcional de la paleta activa entre máquinas (`state_sync`).

La extensión es a propósito simple: **agregar una tool nueva es un template +
un target**, no un cambio al motor. Guía: [Agregar soporte a una tool](guides/add-a-tool.md).
