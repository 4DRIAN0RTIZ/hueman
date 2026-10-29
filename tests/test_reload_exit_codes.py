import logging
import os

import pytest

import hueman.cli as hueman
from hueman.engine.config import ConfigError, HuemanConfig
from hueman.engine.reload import run_post_apply, run_reload
from hueman.cli import Hueman

LOG = logging.getLogger("hueman-tests")


def make_app(tmp_path, extra_top="", targets=None, post_apply=None):
    pal = tmp_path / "pal"
    pal.mkdir(exist_ok=True)
    (pal / "one.yaml").write_text("name: one\nkitty: {c: red}\n")
    (tmp_path / "t.j2").write_text("hello\n")
    body = ""
    for name, opts in (targets or {}).items():
        body += (
            f"  {name}:\n    template: t.j2\n    palette_key: kitty\n"
            f"    outputs: ['{tmp_path / name}.out']\n"
        )
        for k, v in opts.items():
            body += f"    {k}: \"{v}\"\n"
    cfg = tmp_path / "hueman.yaml"
    text = f"state_file: {tmp_path / 'state'}\npalette_dirs: [{pal}]\ntemplate_dirs: [{tmp_path}]\n{extra_top}"
    text += "targets:\n" + body if body else "targets: {}\n"
    if post_apply:
        text += "post_apply:\n" + "".join(f"  - \"{c}\"\n" for c in post_apply)
    cfg.write_text(text)
    return Hueman(HuemanConfig(cfg))


def test_run_reload_returns_exit_code_and_logs_it(caplog):
    caplog.set_level(logging.INFO, logger="hueman-tests")
    assert run_reload("exit 3", LOG) == 3
    assert run_reload("true", LOG) == 0
    assert run_reload("", LOG) == 0
    assert "exit 3" in caplog.text


def test_run_post_apply_runs_all_and_returns_failures(tmp_path):
    marker = tmp_path / "m"
    failed = run_post_apply(["exit 5", f"touch {marker}"], LOG)
    assert failed == [("exit 5", 5)]
    assert marker.exists()


def test_default_policy_warn_exit_zero_but_logs_failure(tmp_path, caplog):
    app = make_app(tmp_path, targets={"a": {"reload": "exit 4"}})
    assert app.set_theme("one") == []
    assert "exit 4" in caplog.text and "WARNING" in caplog.text


def test_global_error_policy_marks_target_failed_and_continues(tmp_path):
    marker = tmp_path / "later"
    app = make_app(
        tmp_path, "reload_failure: error\n",
        targets={"a": {"reload": "exit 2"}, "b": {"reload": f"touch {marker}"}},
        post_apply=[f"touch {tmp_path / 'post'}"],
    )
    failed = app.set_theme("one")
    assert failed == ["a"]
    assert marker.exists() and (tmp_path / "post").exists()
    assert (tmp_path / "state").read_text() == "one\n"


def test_per_target_override_beats_global(tmp_path):
    app = make_app(
        tmp_path, "reload_failure: error\n",
        targets={"a": {"reload": "exit 2", "reload_failure": "warn"},
                 "b": {"reload": "exit 2"}},
    )
    assert app.set_theme("one") == ["b"]


def test_per_target_error_with_global_warn(tmp_path):
    app = make_app(tmp_path, targets={"a": {"reload": "exit 2", "reload_failure": "error"}})
    assert app.set_theme("one") == ["a"]


def test_post_apply_failure_under_error_policy_is_reported(tmp_path):
    app = make_app(tmp_path, "reload_failure: error\n", post_apply=["exit 7"])
    assert app.set_theme("one") == ["post_apply"]


def test_post_apply_failure_under_warn_is_not_fatal(tmp_path):
    app = make_app(tmp_path, post_apply=["exit 7"])
    assert app.set_theme("one") == []


def test_reload_not_run_and_no_failure_when_nothing_written(tmp_path):
    app = make_app(tmp_path, "reload_failure: error\n",
                   targets={"a": {"reload": f"touch {tmp_path / 'r'}"}})
    app.set_theme("one", dry_run=True)
    assert not (tmp_path / "r").exists()


@pytest.mark.parametrize("extra", ["reload_failure: fatal\n", "reload_failure: 3\n"])
def test_invalid_global_policy_is_config_error(tmp_path, extra):
    with pytest.raises(ConfigError):
        make_app(tmp_path, extra)


def test_invalid_target_policy_is_config_error(tmp_path):
    with pytest.raises(ConfigError):
        make_app(tmp_path, targets={"a": {"reload": "true", "reload_failure": "boom"}})


def test_cli_exits_one_when_reload_fails_under_error_policy(tmp_path, monkeypatch, capsys):
    make_app(tmp_path, "reload_failure: error\n", targets={"a": {"reload": "exit 2"}})
    monkeypatch.setattr("sys.argv", ["hueman", "--config", str(tmp_path / "hueman.yaml"), "set", "one"])
    with pytest.raises(SystemExit) as exc:
        hueman.main()
    assert exc.value.code == 1
    assert "a" in capsys.readouterr().err


def test_cli_exits_zero_when_reload_fails_under_warn(tmp_path, monkeypatch):
    make_app(tmp_path, targets={"a": {"reload": "exit 2"}})
    monkeypatch.setattr("sys.argv", ["hueman", "--config", str(tmp_path / "hueman.yaml"), "set", "one"])
    hueman.main()


def test_write_oserror_is_clean_target_error_original_intact(tmp_path, monkeypatch, caplog):
    app = make_app(tmp_path, targets={"a": {"reload": f"touch {tmp_path / 'r'}"},
                                      "b": {}})
    (tmp_path / "a.out").write_text("orig\n")

    def boom(src, dst):
        if str(dst).endswith("a.out"):
            raise PermissionError(13, "Permission denied")
        return real(src, dst)

    real = os.replace
    monkeypatch.setattr(os, "replace", boom)
    failed = app.set_theme("one")
    assert failed == ["a"]
    assert (tmp_path / "a.out").read_text() == "orig\n"
    assert (tmp_path / "b.out").exists()
    assert not (tmp_path / "r").exists()
    assert "Permission denied" in caplog.text
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []


def _run_cli(tmp_path, monkeypatch, *args):
    monkeypatch.setattr(
        "sys.argv", ["hueman", "--config", str(tmp_path / "hueman.yaml"), "set", "one", *args]
    )
    with pytest.raises(SystemExit) as exc:
        hueman.main()
    return exc.value.code


def test_cli_unknown_placeholder_in_reload_fails_before_writing(tmp_path, monkeypatch, capsys):
    make_app(tmp_path, targets={"a": {}, "b": {"reload": "echo {kitty.nope}"}})
    assert _run_cli(tmp_path, monkeypatch) == 1
    err = capsys.readouterr().err
    assert "Config invalida" in err and "{kitty.nope}" in err
    assert "Traceback" not in err
    assert not (tmp_path / "a.out").exists() and not (tmp_path / "b.out").exists()
    assert not (tmp_path / "state").exists()


@pytest.mark.parametrize("extra", [[], ["--dry-run"]])
def test_cli_unknown_placeholder_in_post_apply_fails_cleanly(tmp_path, monkeypatch, capsys, extra):
    make_app(tmp_path, targets={"a": {}}, post_apply=["echo {kitty.nope}"])
    assert _run_cli(tmp_path, monkeypatch, *extra) == 1
    err = capsys.readouterr().err
    assert "Config invalida" in err and "{kitty.nope}" in err
    assert "Traceback" not in err
    assert not (tmp_path / "a.out").exists() and not (tmp_path / "state").exists()


def test_cli_valid_placeholders_still_expand(tmp_path, monkeypatch):
    marker = tmp_path / "m"
    make_app(
        tmp_path, targets={"a": {"reload": f"echo {{name}} {{kitty.c}} > {marker}"}},
        post_apply=["true {kitty.c}"],
    )
    monkeypatch.setattr("sys.argv", ["hueman", "--config", str(tmp_path / "hueman.yaml"), "set", "one"])
    hueman.main()
    assert marker.read_text() == "one red\n"
    assert (tmp_path / "state").read_text() == "one\n"


def test_cli_only_validates_just_selected_targets(tmp_path, monkeypatch):
    make_app(tmp_path, targets={"a": {"reload": "true {kitty.c}"}, "b": {"reload": "echo {kitty.nope}"}})
    monkeypatch.setattr(
        "sys.argv", ["hueman", "--config", str(tmp_path / "hueman.yaml"), "set", "one", "--only", "a"]
    )
    hueman.main()
    assert (tmp_path / "a.out").exists() and not (tmp_path / "b.out").exists()
    assert not (tmp_path / "state").exists()
    assert _run_cli(tmp_path, monkeypatch, "--only", "b") == 1


# --- sync: mismo error limpio que `set` ---------------------------------------

def _sync_app(tmp_path, revision=3, **kw):
    from hueman.engine.statesource import FileSource, State
    shared = tmp_path / "shared"
    shared.mkdir(exist_ok=True)
    FileSource(shared / "s.yaml").write(State("one", revision))
    cfg = f"state_sync:\n  type: file\n  path: {shared}/s.yaml\n"
    return make_app(tmp_path, extra_top=cfg, **kw)


@pytest.mark.parametrize("where", ["reload", "post_apply"])
def test_sync_unknown_placeholder_fails_cleanly(tmp_path, capsys, where):
    if where == "reload":
        a = _sync_app(tmp_path, targets={"k": {"reload": "echo {kitty.nope}"}})
    else:
        a = _sync_app(tmp_path, targets={"k": {}}, post_apply=["echo {kitty.nope}"])
    assert a.sync() == (1, "failed")
    err = capsys.readouterr().err
    assert "Config invalida" in err and "{kitty.nope}" in err
    assert "Traceback" not in err
    assert not (tmp_path / "k.out").exists() and not (tmp_path / "state").exists()
    assert a.local_revision() is None


def test_sync_cli_quiet_unknown_placeholder_no_traceback(tmp_path, monkeypatch, capsys):
    _sync_app(tmp_path, targets={"k": {"reload": "echo {kitty.nope}"}})
    monkeypatch.setattr("sys.argv", ["hueman", "--config", str(tmp_path / "hueman.yaml"), "sync", "-q"])
    with pytest.raises(SystemExit) as exc:
        hueman.main()
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "Config invalida" in err and "Traceback" not in err


def test_sync_valid_placeholders_still_apply(tmp_path):
    marker = tmp_path / "m"
    a = _sync_app(tmp_path, targets={"k": {"reload": f"echo {{kitty.c}} > {marker}"}})
    assert a.sync() == (0, "applied")
    assert marker.read_text() == "red\n"
    assert a.local_revision() == 3
