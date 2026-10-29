# What is hueman

**One palette. Every tool.**

hueman keeps your terminal, editor, prompt, and the rest of your setup on the
same theme. You own the map — which file each app uses — and one command paints
it everywhere.

Core ideas:

- One palette, many targets.
- Packaged templates and palettes are defaults; your custom dirs win.
- Overwrite for full generated files; patch for blocks inside hand-edited configs.
- Reload and post_apply are best-effort, with a `warn` / `error` policy.
- Optional sync of the active palette across machines (`state_sync`).

Extension stays simple on purpose: **adding a tool is a template + a target**,
not an engine change. Guide: [Add support for a tool](guides/add-a-tool.md).
