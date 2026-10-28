import logging
import stat

import pytest

from engine.palettes import PaletteLoader
from engine.render import make_jinja_env, render_target
from engine.targets import PatchSpec, Target

LOG = logging.getLogger("hueman-tests")


def env_with(tmp_path, **templates):
    tdir = tmp_path / "templates"
    tdir.mkdir(exist_ok=True)
    for name, body in templates.items():
        (tdir / name).write_text(body)
    return make_jinja_env([], tdir)


def test_overwrite_writes_every_output_and_replaces_stale_content(tmp_path):
    env = env_with(tmp_path, **{"t.j2": "v={{ theme_name }}\n"})
    outs = [tmp_path / "a" / "x.conf", tmp_path / "b" / "y.conf"]
    outs[1].parent.mkdir()
    outs[1].write_text("stale\n")
    target = Target(name="t", template="t.j2", outputs=outs)
    assert render_target(env, target, "nord", {}, False, LOG) is True
    assert [o.read_text() for o in outs] == ["v=nord\n"] * 2


def test_overwrite_make_executable_sets_exec_bits(tmp_path):
    env = env_with(tmp_path, **{"t.j2": "#!/bin/sh\n"})
    out = tmp_path / "run.sh"
    render_target(env, Target(name="t", template="t.j2", outputs=[out], make_executable=True),
                  "n", {}, False, LOG)
    assert out.stat().st_mode & stat.S_IXUSR


def test_overwrite_uses_palette_key_section_as_context(tmp_path):
    env = env_with(tmp_path, **{"t.j2": "bg={{ bg }}\n"})
    out = tmp_path / "o"
    target = Target(name="t", template="t.j2", palette_key="kitty", outputs=[out])
    render_target(env, target, "n", {"kitty": {"bg": "#111"}}, False, LOG)
    assert out.read_text() == "bg=#111\n"


def test_overwrite_returns_false_when_palette_key_absent(tmp_path):
    env = env_with(tmp_path, **{"t.j2": "x"})
    out = tmp_path / "o"
    target = Target(name="t", template="t.j2", palette_key="kitty", outputs=[out])
    assert render_target(env, target, "n", {}, False, LOG) is False
    assert not out.exists()


def test_custom_jinja_delimiters_and_color_filters(tmp_path):
    tdir = tmp_path / "templates"
    tdir.mkdir()
    (tdir / "t.j2").write_text("fg=<< bg | contrast >> dark=<< bg | is_dark >>\n")
    env = make_jinja_env([], tdir, ("<<", ">>"))
    out = tmp_path / "o"
    target = Target(name="t", template="t.j2", palette_key="k", outputs=[out],
                    jinja_delimiters=("<<", ">>"))
    render_target(env, target, "n", {"k": {"bg": "#000000"}}, False, LOG)
    assert out.read_text() == "fg=#f5f5f5 dark=True\n"


def test_user_template_dir_precedes_packaged(tmp_path):
    user, packaged = tmp_path / "user", tmp_path / "packaged"
    user.mkdir()
    packaged.mkdir()
    (user / "t.j2").write_text("user\n")
    (packaged / "t.j2").write_text("packaged\n")
    env = make_jinja_env([user], packaged)
    out = tmp_path / "o"
    render_target(env, Target(name="t", template="t.j2", outputs=[out]), "n", {}, False, LOG)
    assert out.read_text() == "user\n"


def test_missing_template_raises_clean_target_error(tmp_path):
    from engine.render import TargetRenderError
    env = env_with(tmp_path)
    target = Target(name="t", template="ghost.j2", outputs=[tmp_path / "o"])
    with pytest.raises(TargetRenderError):
        render_target(env, target, "n", {}, False, LOG)
    assert not (tmp_path / "o").exists()


def test_patch_dry_run_leaves_file_untouched(tmp_path):
    env = env_with(tmp_path, **{"b.j2": "new\n"})
    out = tmp_path / "c.conf"
    out.write_text("keep\n# BEGIN\nold\n# END\n")
    target = Target(name="t", mode="patch", template="b.j2", outputs=[out],
                    patch=PatchSpec(marker_begin="# BEGIN", marker_end="# END"))
    assert render_target(env, target, "n", {}, True, LOG) is True
    assert out.read_text() == "keep\n# BEGIN\nold\n# END\n"


def test_patch_marker_regex_replaces_section_or_appends(tmp_path):
    env = env_with(tmp_path, **{"b.j2": "[theme]\nx=2\n"})
    patch = PatchSpec(marker_regex=r"\[theme\]\nx=\d+\n")
    target = Target(name="t", mode="patch", template="b.j2", patch=patch,
                    outputs=[tmp_path / "has", tmp_path / "lacks"])
    (tmp_path / "has").write_text("a\n[theme]\nx=1\nz\n")
    (tmp_path / "lacks").write_text("a\n")
    render_target(env, target, "n", {}, False, LOG)
    assert (tmp_path / "has").read_text() == "a\n[theme]\nx=2\nz\n"
    assert (tmp_path / "lacks").read_text() == "a\n\n[theme]\nx=2\n"


def test_patch_marker_regex_inserts_after_section_when_absent(tmp_path):
    env = env_with(tmp_path, **{"b.j2": "[theme]\n"})
    patch = PatchSpec(marker_regex=r"\[theme\]\n", insert_after_section_regex=r"\[main\]\n")
    out = tmp_path / "c"
    out.write_text("[main]\nk=1\n")
    target = Target(name="t", mode="patch", template="b.j2", patch=patch, outputs=[out])
    render_target(env, target, "n", {}, False, LOG)
    assert out.read_text() == "[main]\n\n[theme]\nk=1\n"


def test_patch_replacements_and_ensure_after_apply_once(tmp_path):
    env = env_with(tmp_path, **{"b.j2": "blk\n"})
    patch = PatchSpec(
        marker_begin="# B", marker_end="# E",
        replacements=[["OLD", "NEW"]],
        ensure_after=[{"if_missing_regex": "(?m)^import x$", "anchor": "top\n", "insert": "import x\n"}],
    )
    out = tmp_path / "c"
    out.write_text("top\nOLD\n")
    target = Target(name="t", mode="patch", template="b.j2", patch=patch, outputs=[out])
    for _ in range(2):
        render_target(env, target, "n", {}, False, LOG)
    text = out.read_text()
    assert "NEW" in text and "OLD" not in text
    assert text.count("import x") == 1


def test_json_scheme_patch_rejects_invalid_json_without_modifying_file(tmp_path):
    from engine.render import TargetRenderError
    env = env_with(tmp_path)
    out = tmp_path / "s.json"
    out.write_text("{not json")
    kitty = {k: "#000" for k in ["background", "foreground", "cursor", "selection_background"]}
    kitty.update({f"color{i}": "#000" for i in range(16)})
    target = Target(name="t", mode="patch", outputs=[out],
                    patch=PatchSpec(strategy="json_scheme_upsert"))
    with pytest.raises(TargetRenderError):
        render_target(env, target, "n", {"kitty": kitty}, False, LOG)
    assert out.read_text() == "{not json"


def test_palette_precedence_first_custom_dir_wins_over_later_and_packaged(tmp_path):
    dirs = [tmp_path / n for n in ("packaged", "c1", "c2")]
    for d in dirs:
        d.mkdir()
        (d / "p.yaml").write_text(f"src: {d.name}\n")
    loader = PaletteLoader(dirs[0], [dirs[1], dirs[2]], LOG)
    assert loader.load("p")["src"] == "c1"
    assert loader.list_palettes() == ["p"]


def test_palette_precedence_ignores_missing_custom_dir(tmp_path):
    packaged = tmp_path / "packaged"
    packaged.mkdir()
    (packaged / "p.yaml").write_text("src: packaged\n")
    loader = PaletteLoader(packaged, [tmp_path / "does-not-exist"], LOG)
    assert loader.load("p")["src"] == "packaged"


class _RecLog:
    def __init__(self):
        self.warnings = []

    def warning(self, msg):
        self.warnings.append(msg)


def _splice_runs(regex, rendered, original, runs=1):
    from types import SimpleNamespace
    from engine.render import _apply_regex_splice
    patch = SimpleNamespace(marker_regex=regex, insert_after_section_regex=None,
                            replacements=[], ensure_after=[])
    log = _RecLog()
    content = original
    for _ in range(runs):
        content = _apply_regex_splice(content, rendered, patch, log)
    return content, log.warnings


def test_marker_regex_not_matching_own_output_warns_once():
    content, warns = _splice_runs(r"\[colors\].*?(?=\n\[|\Z)", "color=1\n", "a=1\n")
    assert content == "a=1\n\ncolor=1\n"
    assert len(warns) == 1
    assert "marker_regex" in warns[0]


def test_marker_regex_matching_own_output_is_idempotent_without_warning():
    content, warns = _splice_runs(r"(?s)color=1\n", "color=1\n", "a=1\n", runs=3)
    assert content.count("color=1") == 1
    assert warns == []


def test_marker_regex_replace_path_does_not_warn():
    content, warns = _splice_runs(r"\[colors\].*?(?=\n\[|\Z)", "[colors]\nx=2\n",
                                  "a=1\n[colors]\nx=1\n")
    assert content == "a=1\n[colors]\nx=2\n"
    assert warns == []
