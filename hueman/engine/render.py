"""Motor de render genérico: dos modos (overwrite, patch) compartidos por
TODOS los targets — nada de código Python específico por herramienta."""

import json
import re
from pathlib import Path

import jinja2
import jinja2.sandbox

from .colors import contrast_text, is_dark
from .fsutil import atomic_write_text


class TargetRenderError(Exception):
    """A target could not be rendered (e.g. the palette lacks a required key)."""


def _dig(data: dict, dotted_path: str):
    cur = data
    for part in dotted_path.split("."):
        cur = cur[part]
    return cur


def make_jinja_env(template_dirs: list, packaged_dir: Path, delimiters=None) -> jinja2.sandbox.SandboxedEnvironment:
    """Entorno Jinja en sandbox: una plantilla ajena no alcanza internals de
    Python (`__class__`, `__globals__`...).

    ChoiceLoader: los template_dirs custom del usuario se resuelven ANTES
    que los empaquetados — así un target idiosincrático puede referenciar un
    template por nombre igual que uno genérico."""
    loader = jinja2.ChoiceLoader([
        jinja2.FileSystemLoader([str(d) for d in template_dirs]),
        jinja2.FileSystemLoader(str(packaged_dir)),
    ])
    kwargs = {"loader": loader, "keep_trailing_newline": True}
    if delimiters:
        kwargs["variable_start_string"], kwargs["variable_end_string"] = delimiters
    env = jinja2.sandbox.SandboxedEnvironment(**kwargs)
    env.filters["contrast"] = contrast_text
    env.filters["is_dark"] = is_dark
    return env


def build_context(target, name: str, palette: dict) -> dict:
    context = {"theme_name": name}
    if target.palette_key and target.palette_key in palette:
        context.update(palette[target.palette_key])
    for key, dotted_path in target.extra_vars.items():
        try:
            context[key] = _dig(palette, dotted_path)
        except (KeyError, TypeError):
            raise KeyError(dotted_path) from None
    return context


def render_template(env: jinja2.Environment, target, name: str, palette: dict) -> str:
    context = build_context(target, name, palette)
    return env.get_template(target.template).render(**context)


def _write(path: Path, content: str, dry_run: bool, logger, make_executable: bool = False):
    if dry_run:
        print(f"[DRY RUN] escribiría {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, content, make_executable)
    logger.info(f"Generado: {path}")


def _missing_palette_section(target, palette, logger) -> bool:
    """True (con log INFO) si el target apunta a una seccion que la paleta no tiene."""
    if target.palette_key and target.palette_key not in palette:
        logger.info(f"{target.name}: la paleta no tiene la seccion '{target.palette_key}', omitido")
        return True
    return False


def render_overwrite(env, target, name, palette, dry_run, logger) -> bool:
    if _missing_palette_section(target, palette, logger):
        return False
    content = render_template(env, target, name, palette)
    wrote = False
    for out in target.outputs:
        if target.skip_if_missing_parent and not out.parent.exists():
            logger.info(f"{target.name}: {out.parent} no existe, omitido")
            continue
        _write(out, content, dry_run, logger, target.make_executable)
        wrote = True
    return wrote


def _apply_regex_splice(original: str, rendered: str, patch, logger) -> str:
    if patch.marker_regex:
        # Bloque delimitado por un único regex (ej. una sección TOML entera).
        block = rendered
        pattern = re.compile(patch.marker_regex, re.DOTALL)
        inserted = not pattern.search(original)
        if not inserted:
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
        # Si el regex no reconoce el bloque recién insertado, se duplicará.
        if inserted and not pattern.search(content):
            logger.warning(
                "marker_regex no reconoce el bloque insertado; "
                "se volvera a insertar en la siguiente ejecucion"
            )
    else:
        # Marcadores begin/end literales envolviendo el contenido renderizado.
        marker_begin = patch.marker_begin
        marker_end = patch.marker_end
        if patch.marker_end_regex:
            end_pattern = patch.marker_end_regex
        else:
            # Consume the newline after END: full_block re-adds it.
            end_pattern = re.escape(marker_end) + r"\n?"
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
    if _missing_palette_section(target, palette, logger):
        return False

    if patch.strategy == "json_scheme_upsert":
        section = palette[patch.palette_section]
        scheme_name = patch.scheme_name or "Dotfiles"
        wrote = False
        for out in target.outputs:
            if not out.exists():
                logger.info(f"{target.name}: {out} no encontrado, omitido")
                continue
            original = out.read_text(encoding="utf-8")
            try:
                content = _apply_json_scheme_upsert(original, section, scheme_name)
            except json.JSONDecodeError as exc:
                raise TargetRenderError(f"{target.name}: {out} no es JSON valido ({exc})") from exc
            wrote = True
            if dry_run:
                print(f"[DRY RUN] escribiría {out} (scheme '{scheme_name}')")
                continue
            atomic_write_text(out, content)
            logger.info(f"{target.name}: scheme '{scheme_name}' actualizado en {out}")
        return wrote

    # regex_splice
    rendered = render_template(env, target, name, palette) if target.template else ""
    wrote = False
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
        wrote = True
    return wrote


def render_target(env, target, name, palette, dry_run, logger) -> bool:
    missing = [p for p in target.skip_unless_path_exists if not p.exists()]
    if missing:
        logger.info(f"{target.name}: {missing[0]} no existe, target omitido")
        return False
    try:
        if target.mode == "overwrite":
            return render_overwrite(env, target, name, palette, dry_run, logger)
        return render_patch(env, target, name, palette, dry_run, logger)
    except jinja2.TemplateNotFound as exc:
        raise TargetRenderError(f"{target.name}: plantilla {exc.name!r} no encontrada") from exc
    except jinja2.exceptions.SecurityError as exc:
        raise TargetRenderError(
            f"{target.name}: la plantilla intento una operacion no permitida en el sandbox ({exc})"
        ) from exc
    except OSError as exc:
        raise TargetRenderError(f"{target.name}: error de E/S ({exc})") from exc
    except (KeyError, TypeError) as exc:
        key = exc.args[0] if exc.args else exc
        raise TargetRenderError(
            f"{target.name}: la paleta '{name}' no tiene la clave {key!r} requerida"
        ) from exc
