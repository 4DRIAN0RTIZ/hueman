"""Running the complete `set` twice must leave every output byte-identical."""

import json

import yaml

from hueman.engine.config import HuemanConfig
from hueman.cli import Hueman


def _kitty():
    kitty = {"background": "#000000", "foreground": "#ffffff", "cursor": "#fff",
             "selection_background": "#333"}
    kitty.update({f"color{i}": f"#{i:06x}" for i in range(16)})
    return kitty


def _build(tmp_path):
    tpl = tmp_path / "tpl"
    tpl.mkdir()
    (tpl / "full.j2").write_text("bg={{ background }}\n")
    (tpl / "block.j2").write_text("managed={{ background }}\n")
    (tpl / "section.j2").write_text("[palettes.dotfiles]\nbg = \"{{ background }}\"\n")
    out = tmp_path / "out"
    out.mkdir()
    (out / "marked.conf").write_text("a\n# BEGIN X\nold\n# END X\nz\n")
    (out / "unmarked.conf").write_text("a\n")
    (out / "starship.toml").write_text(
        'add_newline = false\n[x]\ny = 1\n[palettes.dotfiles]\nbg = "old"\n[z]\nq = 2\n'
    )
    (out / "schemes.json").write_text(json.dumps({"schemes": [{"name": "Other"}]}))
    pal = tmp_path / "pal"
    pal.mkdir()
    (pal / "demo.yaml").write_text(yaml.safe_dump({"kitty": _kitty()}))
    targets = {
        "overwrite": {"template": "full.j2", "palette_key": "kitty",
                      "outputs": [str(out / "new" / "full.conf")], "make_executable": True},
        "skipped": {"template": "full.j2", "palette_key": "kitty",
                    "skip_if_missing_parent": True, "outputs": [str(out / "no" / "f")]},
        "marked": {"template": "block.j2", "palette_key": "kitty", "mode": "patch",
                   "patch": {"marker_begin": "# BEGIN X", "marker_end": "# END X"},
                   "outputs": [str(out / "marked.conf")]},
        "unmarked": {"template": "block.j2", "palette_key": "kitty", "mode": "patch",
                     "patch": {"marker_begin": "# BEGIN X", "marker_end": "# END X"},
                     "outputs": [str(out / "unmarked.conf")]},
        "regex": {"template": "section.j2", "palette_key": "kitty", "mode": "patch",
                  "patch": {"marker_regex": r"\[palettes\.dotfiles\][^\[]*",
                            "replacements": [["q = 2", "q = 3"]],
                            "ensure_after": [{"if_missing_regex": r"(?m)^palette\s*=",
                                              "anchor": "add_newline = false\n",
                                              "insert": 'palette = "dotfiles"\n'}]},
                  "outputs": [str(out / "starship.toml")]},
        "json": {"palette_key": "kitty", "mode": "patch",
                 "patch": {"strategy": "json_scheme_upsert", "scheme_name": "H",
                           "palette_section": "kitty"},
                 "outputs": [str(out / "schemes.json")]},
    }
    cfg = tmp_path / "hueman.yaml"
    cfg.write_text(yaml.safe_dump({
        "state_file": str(tmp_path / "state"), "palette_dirs": [str(pal)],
        "template_dirs": [str(tpl)], "targets": targets,
    }))
    return Hueman(HuemanConfig(cfg)), out


def _snapshot(out):
    return {str(p.relative_to(out)): (p.read_bytes(), p.stat().st_mode)
            for p in sorted(out.rglob("*")) if p.is_file()}


def test_full_set_twice_changes_no_file(tmp_path):
    app, out = _build(tmp_path)

    assert app.set_theme("demo") == []
    first = _snapshot(out)
    assert app.set_theme("demo") == []
    second = _snapshot(out)

    assert first == second
    assert "new/full.conf" in first and "no/f" not in first
    assert first["marked.conf"][0].count(b"# BEGIN X") == 1
    assert first["unmarked.conf"][0].count(b"# BEGIN X") == 1
    assert first["starship.toml"][0].count(b"[palettes.dotfiles]") == 1
    assert json.loads(first["schemes.json"][0])["schemes"][-1]["name"] == "H"
    assert len(json.loads(first["schemes.json"][0])["schemes"]) == 2
