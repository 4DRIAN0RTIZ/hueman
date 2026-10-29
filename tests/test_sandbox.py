"""Templates run in a Jinja sandbox; a hostile one is a clean per-target failure."""

import logging
import sys

import jinja2
import jinja2.sandbox
import pytest

import hueman.cli as hueman
from hueman.engine.render import TargetRenderError, make_jinja_env, render_target
from hueman.engine.targets import Target
from test_reload_exit_codes import make_app

LOG = logging.getLogger("hueman-tests")

HOSTILE = [
    "{{ ''.__class__.__mro__[1].__subclasses__() }}",
    "{{ cycler.__init__.__globals__ }}",
    "{{ ''.__class__.__mro__ }}",
]


def env_for(tmp_path, delimiters=None):
    d = tmp_path / "templates"
    d.mkdir(exist_ok=True)
    return make_jinja_env([], d, delimiters)


def test_env_is_sandboxed(tmp_path):
    assert isinstance(env_for(tmp_path), jinja2.sandbox.SandboxedEnvironment)
    assert isinstance(env_for(tmp_path, ("<<", ">>")), jinja2.sandbox.SandboxedEnvironment)


def test_custom_delimiters_and_filters_still_work(tmp_path):
    from hueman.engine.colors import contrast_text, is_dark
    env = env_for(tmp_path, ("<<", ">>"))
    (tmp_path / "templates" / "t.j2").write_text("<< c|contrast >> << c|is_dark >> {{ raw }}\n")
    out = tmp_path / "o"
    t = Target(name="t", template="t.j2", outputs=[out], palette_key="kitty")
    render_target(env, t, "n", {"kitty": {"c": "#101010"}}, False, LOG)
    assert out.read_text() == f"{contrast_text('#101010')} {is_dark('#101010')} {{{{ raw }}}}\n"


@pytest.mark.parametrize("src", HOSTILE)
def test_hostile_template_is_a_clean_target_error(tmp_path, src):
    env = env_for(tmp_path)
    (tmp_path / "templates" / "t.j2").write_text(src)
    out = tmp_path / "o"
    t = Target(name="t", template="t.j2", outputs=[out])
    with pytest.raises(TargetRenderError):
        render_target(env, t, "n", {}, False, LOG)
    assert not out.exists()


def test_set_skips_hostile_target_and_exits_one(tmp_path, monkeypatch, capsys):
    make_app(tmp_path, targets={"k": {}, "evil": {}})
    (tmp_path / "t.j2").write_text("ok\n")
    (tmp_path / "bad.j2").write_text("{{ ''.__class__.__mro__ }}")
    cfg = tmp_path / "hueman.yaml"
    cfg.write_text(cfg.read_text().replace(
        f"  evil:\n    template: t.j2", "  evil:\n    template: bad.j2"))
    monkeypatch.setattr(sys, "argv", ["hueman", "--config", str(cfg), "set", "one"])
    with pytest.raises(SystemExit) as exc:
        hueman.main()
    assert exc.value.code == 1
    cap = capsys.readouterr()
    assert "Traceback" not in cap.err
    assert "evil" in cap.err
    assert (tmp_path / "k.out").exists()
    assert not (tmp_path / "evil.out").exists()
