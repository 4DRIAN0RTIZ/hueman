"""Motor de render genérico: dos modos (overwrite, patch) compartidos por
TODOS los targets — nada de código Python específico por herramienta."""

import json
import re
from pathlib import Path

import jinja2

from .colors import contrast_text, is_dark


def _dig(data: dict, dotted_path: str):
    cur = data
    for part in dotted_path.split("."):
        cur = cur[part]
    return cur


def make_jinja_env(template_dirs: list, packaged_dir: Path, delimiters=None) -> jinja2.Environment:
    """ChoiceLoader: los template_dirs custom del usuario se resuelven ANTES
    que los empaquetados — así un target idiosincrático puede referenciar un
    template por nombre igual que uno genérico."""
    loader = jinja2.ChoiceLoader([
        jinja2.FileSystemLoader([str(d) for d in template_dirs]),
        jinja2.FileSystemLoader(str(packaged_dir)),
    ])
    kwargs = {"loader": loader, "keep_trailing_newline": True}
    if delimiters:
        kwargs["variable_start_string"], kwargs["variable_end_string"] = delimiters
    env = jinja2.Environment(**kwargs)
    env.filters["contrast"] = contrast_text
    env.filters["is_dark"] = is_dark
    return env


def build_context(target, name: str, palette: dict) -> dict:
    context = {"theme_name": name}
    if target.palette_key and target.palette_key in palette:
        context.update(palette[target.palette_key])
    for key, dotted_path in target.extra_vars.items():
        context[key] = _dig(palette, dotted_path)
    return context


def render_template(env: jinja2.Environment, target, name: str, palette: dict) -> str:
    context = build_context(target, name, palette)
    return env.get_template(target.template).render(**context)


def _write(path: Path, content: str, dry_run: bool, logger, make_executable: bool = False):
    if dry_run:
        print(f"[DRY RUN] escribiría {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    if make_executable:
        path.chmod(path.stat().st_mode | 0o111)
    logger.info(f"Generado: {path}")


def render_overwrite(env, target, name, palette, dry_run, logger) -> bool:
    if target.palette_key and target.palette_key not in palette:
        return False
    content = render_template(env, target, name, palette)
    for out in target.outputs:
        if target.skip_if_missing_parent and not out.parent.exists():
            logger.info(f"{target.name}: {out.parent} no existe, omitido")
            continue
        _write(out, content, dry_run, logger, target.make_executable)
    return True


def _apply_regex_splice(original: str, rendered: str, patch, logger) -> str:
    if patch.marker_regex:
        # Bloque delimitado por un único regex (ej. una sección TOML entera).
        block = rendered
        pattern = re.compile(patch.marker_regex, re.DOTALL)
        if pattern.search(original):
            content = pattern.sub(lambda m: block, original, count=1)
        elif patch.insert_after_section_regex:
            section = re.search(patch.insert_after_section_regex, original, re.DOTALL)
            if section:
                insert_at = section.end()
                content = original[:insert_at] + "\n" + block + original[insert_at:]
            else:
                content = original.rstrip("\n") + "\n\n" + block
        else:
            content = original.rstrip("\n") + "\n\n" + block
    else:
        # Marcadores begin/end literales envolviendo el contenido renderizado.
        marker_begin = patch.marker_begin
        marker_end = patch.marker_end
        end_pattern = patch.marker_end_regex or re.escape(marker_end)
        pattern = re.compile(re.escape(marker_begin) + r".*?" + end_pattern, re.DOTALL)
        if marker_end and not patch.marker_end_regex:
            full_block = f"{marker_begin}\n{rendered}{marker_end}\n"
        else:
            full_block = f"{marker_begin}\n{rendered}"
        if pattern.search(original):
            content = pattern.sub(lambda m: full_block, original, count=1)
        else:
            content = original.rstrip("\n") + "\n\n" + full_block

    for old, new in patch.replacements:
        content = content.replace(old, new)
    for rule in patch.ensure_after:
        if not re.search(rule["if_missing_regex"], content):
            content = content.replace(rule["anchor"], rule["anchor"] + rule["insert"], 1)
    return content


def _apply_json_scheme_upsert(original: str, kitty: dict, scheme_name: str) -> str:
    data = json.loads(original)
    scheme = {
        "name": scheme_name,
        "background": kitty["background"],
        "foreground": kitty["foreground"],
        "black": kitty["color0"],
        "red": kitty["color1"],
        "green": kitty["color2"],
        "yellow": kitty["color3"],
        "blue": kitty["color4"],
        "purple": kitty["color5"],
        "cyan": kitty["color6"],
        "white": kitty["color7"],
        "brightBlack": kitty["color8"],
        "brightRed": kitty["color9"],
        "brightGreen": kitty["color10"],
        "brightYellow": kitty["color11"],
        "brightBlue": kitty["color12"],
        "brightPurple": kitty["color13"],
        "brightCyan": kitty["color14"],
        "brightWhite": kitty["color15"],
        "cursorColor": kitty["cursor"],
        "selectionBackground": kitty["selection_background"],
    }
    schemes = data.setdefault("schemes", [])
    for i, s in enumerate(schemes):
        if s.get("name") == scheme_name:
            schemes[i] = scheme
            break
    else:
        schemes.append(scheme)
    return json.dumps(data, indent=4, ensure_ascii=False) + "\n"


def render_patch(env, target, name, palette, dry_run, logger) -> bool:
    patch = target.patch
    if target.palette_key and target.palette_key not in palette:
        return False

    if patch.strategy == "json_scheme_upsert":
        section = palette[patch.palette_section]
        scheme_name = patch.scheme_name or "Dotfiles"
        for out in target.outputs:
            if not out.exists():
                logger.info(f"{target.name}: {out} no encontrado, omitido")
                continue
            original = out.read_text(encoding="utf-8")
            content = _apply_json_scheme_upsert(original, section, scheme_name)
            if dry_run:
                print(f"[DRY RUN] escribiría {out} (scheme '{scheme_name}')")
                continue
            out.write_text(content, encoding="utf-8")
            logger.info(f"{target.name}: scheme '{scheme_name}' actualizado en {out}")
        return True

    # regex_splice
    rendered = render_template(env, target, name, palette) if target.template else ""
    for out in target.outputs:
        if target.skip_if_missing_parent and not out.parent.exists():
            logger.info(f"{target.name}: {out.parent} no existe, omitido")
            continue
        if not out.exists():
            logger.info(f"{target.name}: {out} no encontrado, omitido")
            continue
        original = out.read_text()
        content = _apply_regex_splice(original, rendered, patch, logger)
        _write(out, content, dry_run, logger, target.make_executable)
    return True


def render_target(env, target, name, palette, dry_run, logger) -> bool:
    if target.mode == "overwrite":
        return render_overwrite(env, target, name, palette, dry_run, logger)
    return render_patch(env, target, name, palette, dry_run, logger)
