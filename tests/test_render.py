import json
import logging

import pytest

from engine.render import make_jinja_env, render_target
from engine.targets import PatchSpec, Target


@pytest.fixture
def logger():
    return logging.getLogger("hueman-tests")


def env_for(tmp_path):
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    return make_jinja_env([], template_dir)


def test_overwrite_creates_parent_and_renders_template(tmp_path, logger):
    env = env_for(tmp_path)
    (tmp_path / "templates" / "demo.j2").write_text("theme={{ theme_name }}\n")
    output = tmp_path / "nested" / "demo.conf"
    target = Target(name="demo", template="demo.j2", outputs=[output])

    assert render_target(env, target, "nord", {}, False, logger) is True
    assert output.read_text() == "theme=nord\n"


def test_overwrite_dry_run_does_not_create_output(tmp_path, logger):
    env = env_for(tmp_path)
    (tmp_path / "templates" / "demo.j2").write_text("content\n")
    output = tmp_path / "new" / "demo.conf"
    target = Target(name="demo", template="demo.j2", outputs=[output])

    render_target(env, target, "nord", {}, True, logger)

    assert not output.exists()
    assert not output.parent.exists()


def test_overwrite_skips_missing_parent_when_configured(tmp_path, logger):
    env = env_for(tmp_path)
    (tmp_path / "templates" / "demo.j2").write_text("content\n")
    output = tmp_path / "missing" / "demo.conf"
    target = Target(
        name="demo", template="demo.j2", outputs=[output], skip_if_missing_parent=True
    )

    render_target(env, target, "nord", {}, False, logger)

    assert not output.exists()


def test_patch_replaces_marked_block_and_preserves_surrounding_text(tmp_path, logger):
    env = env_for(tmp_path)
    (tmp_path / "templates" / "block.j2").write_text("managed=true\n")
    output = tmp_path / "config.conf"
    output.write_text("before\n# BEGIN HUEMAN\nold\n# END HUEMAN\nafter\n")
    patch = PatchSpec(marker_begin="# BEGIN HUEMAN", marker_end="# END HUEMAN")
    target = Target(
        name="patch", mode="patch", template="block.j2", outputs=[output], patch=patch
    )

    render_target(env, target, "nord", {}, False, logger)

    assert output.read_text() == (
        "before\n# BEGIN HUEMAN\nmanaged=true\n# END HUEMAN\nafter\n"
    )


def test_patch_does_not_create_missing_output(tmp_path, logger):
    env = env_for(tmp_path)
    (tmp_path / "templates" / "block.j2").write_text("managed\n")
    output = tmp_path / "missing.conf"
    target = Target(
        name="patch",
        mode="patch",
        template="block.j2",
        outputs=[output],
        patch=PatchSpec(marker_regex="^managed$"),
    )

    render_target(env, target, "nord", {}, False, logger)

    assert not output.exists()


def test_json_scheme_patch_upserts_scheme(tmp_path, logger):
    env = env_for(tmp_path)
    output = tmp_path / "schemes.json"
    output.write_text(json.dumps({"schemes": [{"name": "Other"}]}))
    kitty = {"background": "#000000", "foreground": "#ffffff"}
    kitty.update({f"color{i}": f"#{i:06x}" for i in range(16)})
    kitty.update(cursor="#ffffff", selection_background="#333333")
    target = Target(
        name="kitty",
        mode="patch",
        outputs=[output],
        patch=PatchSpec(
            strategy="json_scheme_upsert", palette_section="kitty", scheme_name="Hueman"
        ),
    )

    render_target(env, target, "nord", {"kitty": kitty}, False, logger)

    schemes = json.loads(output.read_text())["schemes"]
    assert [scheme["name"] for scheme in schemes] == ["Other", "Hueman"]
    assert schemes[-1]["background"] == "#000000"


def test_windhawk_taskbar_template_matches_legacy_json(tmp_path, logger):
    from pathlib import Path

    packaged = Path(__file__).resolve().parent.parent / "templates"
    env = make_jinja_env([], packaged)
    palette = {"polybar": {"background": "#170b2f", "primary": "#ff2bd6"}}
    output = tmp_path / "taskbar-colors.json"
    target = Target(
        name="windhawk_taskbar",
        template="windhawk_taskbar.json.j2",
        palette_key="polybar",
        outputs=[output],
    )

    assert render_target(env, target, "synthwave", palette, False, logger) is True
    legacy = json.dumps({"fill": "#170b2f", "text": "#ff2bd6"}, indent=2) + "\n"
    assert output.read_text() == legacy


def _splice_target(tmp_path, output):
    env = env_for(tmp_path)
    (tmp_path / "templates" / "block.j2").write_text("managed=true\n")
    patch = PatchSpec(marker_begin="# BEGIN HUEMAN", marker_end="# END HUEMAN")
    target = Target(
        name="patch", mode="patch", template="block.j2", outputs=[output], patch=patch
    )
    return env, target


def _apply(env, target, output, logger):
    render_target(env, target, "nord", {}, False, logger)
    return output.read_text()


def test_marker_splice_is_idempotent_with_existing_markers(tmp_path, logger):
    output = tmp_path / "config.conf"
    output.write_text("before\n# BEGIN HUEMAN\nold\n# END HUEMAN\nafter\n")
    env, target = _splice_target(tmp_path, output)

    first = _apply(env, target, output, logger)
    second = _apply(env, target, output, logger)

    assert first == second
    assert first == "before\n# BEGIN HUEMAN\nmanaged=true\n# END HUEMAN\nafter\n"


def test_marker_splice_appends_once_without_markers_then_is_stable(tmp_path, logger):
    output = tmp_path / "config.conf"
    output.write_text("before\n")
    env, target = _splice_target(tmp_path, output)

    first = _apply(env, target, output, logger)
    second = _apply(env, target, output, logger)

    assert first == "before\n\n# BEGIN HUEMAN\nmanaged=true\n# END HUEMAN\n"
    assert second == first


def test_marker_splice_handles_end_marker_at_eof_without_newline(tmp_path, logger):
    output = tmp_path / "config.conf"
    output.write_text("before\n# BEGIN HUEMAN\nold\n# END HUEMAN")
    env, target = _splice_target(tmp_path, output)

    first = _apply(env, target, output, logger)
    second = _apply(env, target, output, logger)

    assert first == "before\n# BEGIN HUEMAN\nmanaged=true\n# END HUEMAN\n"
    assert second == first


def test_marker_splice_preserves_content_after_end_byte_for_byte(tmp_path, logger):
    output = tmp_path / "config.conf"
    tail = "\n\n  indented\n\tTAB  \n\nlast"
    output.write_text("# BEGIN HUEMAN\nold\n# END HUEMAN\n" + tail)
    env, target = _splice_target(tmp_path, output)

    out = _apply(env, target, output, logger)

    assert out.endswith("# END HUEMAN\n" + tail)


def test_overwrite_returns_false_when_every_output_skipped(tmp_path, logger):
    env = env_for(tmp_path)
    (tmp_path / "templates" / "demo.j2").write_text("content\n")
    target = Target(
        name="demo", template="demo.j2", skip_if_missing_parent=True,
        outputs=[tmp_path / "gone" / "a.conf", tmp_path / "gone2" / "b.conf"],
    )

    assert render_target(env, target, "nord", {}, False, logger) is False


def test_overwrite_returns_true_when_at_least_one_output_written(tmp_path, logger):
    env = env_for(tmp_path)
    (tmp_path / "templates" / "demo.j2").write_text("content\n")
    target = Target(
        name="demo", template="demo.j2", skip_if_missing_parent=True,
        outputs=[tmp_path / "gone" / "a.conf", tmp_path / "b.conf"],
    )

    assert render_target(env, target, "nord", {}, False, logger) is True


def test_overwrite_dry_run_returns_true_when_it_would_write(tmp_path, logger):
    env = env_for(tmp_path)
    (tmp_path / "templates" / "demo.j2").write_text("content\n")
    target = Target(name="demo", template="demo.j2", outputs=[tmp_path / "a.conf"])

    assert render_target(env, target, "nord", {}, True, logger) is True


def test_patch_returns_false_when_every_output_missing(tmp_path, logger):
    env, target = _splice_target(tmp_path, tmp_path / "missing.conf")

    assert render_target(env, target, "nord", {}, False, logger) is False


def test_patch_returns_false_when_parent_missing_and_skipped(tmp_path, logger):
    env, target = _splice_target(tmp_path, tmp_path / "nodir" / "c.conf")
    target.skip_if_missing_parent = True

    assert render_target(env, target, "nord", {}, False, logger) is False


def test_patch_returns_true_when_an_output_was_patched(tmp_path, logger):
    output = tmp_path / "config.conf"
    output.write_text("x\n")
    env, target = _splice_target(tmp_path, output)
    target.outputs = [tmp_path / "missing.conf", output]

    assert render_target(env, target, "nord", {}, False, logger) is True


def test_json_scheme_patch_returns_false_when_output_missing(tmp_path, logger):
    env = env_for(tmp_path)
    target = Target(
        name="wt", mode="patch", outputs=[tmp_path / "nope.json"],
        patch=PatchSpec(strategy="json_scheme_upsert", palette_section="kitty"),
    )

    assert render_target(env, target, "nord", {"kitty": {}}, False, logger) is False


def test_reload_not_fired_when_all_outputs_skipped(tmp_path, monkeypatch):
    from engine.config import HuemanConfig
    from hueman import Hueman

    (tmp_path / "t.j2").write_text("x\n")
    (tmp_path / "palette.yaml").write_text("name: demo\nkitty: {}\n")
    (tmp_path / "hueman.yaml").write_text(
        f"state_file: {tmp_path / 'state'}\npalette_dirs: [{tmp_path}]\n"
        f"template_dirs: [{tmp_path}]\ntargets:\n  t:\n    template: t.j2\n"
        f"    palette_key: kitty\n    skip_if_missing_parent: true\n"
        f"    outputs: ['{tmp_path}/nope/out']\n    reload: 'r'\n"
    )
    reloads = []
    monkeypatch.setattr("hueman.run_reload", lambda cmd, logger: reloads.append(cmd))

    Hueman(HuemanConfig(tmp_path / "hueman.yaml")).set_theme("palette")

    assert reloads == []


def test_missing_extra_var_key_raises_target_render_error_naming_target_and_key(tmp_path, logger):
    from engine.render import TargetRenderError

    env = env_for(tmp_path)
    (tmp_path / "templates" / "demo.j2").write_text("{{ panel }}\n")
    target = Target(
        name="posting", template="demo.j2", outputs=[tmp_path / "o"],
        extra_vars={"panel": "pi.vars.elevatedBg"},
    )

    with pytest.raises(TargetRenderError) as exc:
        render_target(env, target, "nord", {"pi": {}}, False, logger)

    assert "posting" in str(exc.value) and "pi.vars.elevatedBg" in str(exc.value)
    assert not (tmp_path / "o").exists()


def test_missing_json_scheme_section_raises_target_render_error(tmp_path, logger):
    from engine.render import TargetRenderError

    env = env_for(tmp_path)
    out = tmp_path / "s.json"
    out.write_text("{}")
    target = Target(
        name="wt", mode="patch", outputs=[out],
        patch=PatchSpec(strategy="json_scheme_upsert", palette_section="kitty"),
    )

    with pytest.raises(TargetRenderError) as exc:
        render_target(env, target, "nord", {}, False, logger)

    assert "wt" in str(exc.value) and "kitty" in str(exc.value)


def _failing_app(tmp_path, monkeypatch):
    from engine.config import HuemanConfig
    from hueman import Hueman

    (tmp_path / "t.j2").write_text("{{ panel|default('') }}ok\n")
    (tmp_path / "palette.yaml").write_text("name: demo\nkitty: {}\n")
    (tmp_path / "hueman.yaml").write_text(
        f"state_file: {tmp_path / 'state'}\npalette_dirs: [{tmp_path}]\n"
        f"template_dirs: [{tmp_path}]\ntargets:\n"
        f"  bad:\n    template: t.j2\n    palette_key: kitty\n"
        f"    extra_vars: {{panel: pi.vars.x}}\n    outputs: ['{tmp_path}/bad.out']\n"
        f"    reload: 'reload-bad'\n"
        f"  good:\n    template: t.j2\n    palette_key: kitty\n"
        f"    outputs: ['{tmp_path}/good.out']\n    reload: 'reload-good'\n"
        f"post_apply: ['echo done']\n"
    )
    reloads, post = [], []
    monkeypatch.setattr("hueman.run_reload", lambda cmd, logger: reloads.append(cmd))
    monkeypatch.setattr("hueman.run_post_apply", lambda c, logger: post.append(c))
    return Hueman(HuemanConfig(tmp_path / "hueman.yaml")), reloads, post


def test_set_theme_skips_failing_target_continues_and_returns_failures(tmp_path, monkeypatch, caplog):
    app, reloads, post = _failing_app(tmp_path, monkeypatch)

    with caplog.at_level(logging.WARNING, logger="hueman"):
        failed = app.set_theme("palette")

    assert failed == ["bad"]
    assert not (tmp_path / "bad.out").exists()
    assert (tmp_path / "good.out").exists()
    assert reloads == ["reload-good"]
    assert (tmp_path / "state").read_text() == "palette\n"
    assert any("bad" in r.message and "pi.vars.x" in r.message for r in caplog.records)


def test_cli_exits_nonzero_when_a_target_failed(tmp_path, monkeypatch):
    import hueman

    monkeypatch.setattr(hueman.Hueman, "set_theme", lambda self, *a, **k: ["bad"])
    (tmp_path / "c.yaml").write_text(f"state_file: {tmp_path / 's'}\ntargets: {{}}\n")
    monkeypatch.setattr("sys.argv", ["hueman", "--config", str(tmp_path / "c.yaml"), "set", "p"])

    with pytest.raises(SystemExit) as exc:
        hueman.main()

    assert exc.value.code == 1
