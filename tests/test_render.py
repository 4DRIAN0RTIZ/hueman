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
        "before\n# BEGIN HUEMAN\nmanaged=true\n# END HUEMAN\n\nafter\n"
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
