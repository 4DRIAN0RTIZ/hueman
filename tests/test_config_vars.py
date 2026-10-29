import sys

import pytest

import hueman.cli as hueman
from hueman.engine.config import ConfigError, HuemanConfig, substitute_vars


def write_cfg(tmp_path, body):
    cfg = tmp_path / "c.yaml"
    cfg.write_text(body)
    return cfg


def run_cli(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["hueman", *argv])
    hueman.main()


# --- pure helper -----------------------------------------------------------

def test_substitute_replaces_known_names():
    assert substitute_vars("${repo}/k/${name}.conf", {"repo": "/r", "name": "x"}, "t") == "/r/k/x.conf"


def test_substitute_leaves_bare_dollar_untouched():
    text = "$HOME/a/$repo/${ }/$ {repo}/${1x}"
    assert substitute_vars(text, {"repo": "/r"}, "t") == text


def test_substitute_undefined_names_variable_and_location():
    with pytest.raises(ConfigError) as exc:
        substitute_vars("${nope}/x", {}, "targets.kitty.outputs")
    assert "nope" in str(exc.value)
    assert "targets.kitty.outputs" in str(exc.value)


def test_substitute_is_not_recursive():
    # the replacement text is inserted verbatim
    assert substitute_vars("${a}", {"a": "x"}, "t") == "x"


# --- config loading --------------------------------------------------------

def test_vars_substituted_in_outputs_and_guards(tmp_path):
    cfg = write_cfg(tmp_path, f"""
vars:
  repo: "{tmp_path}/dot"
  guard: "{tmp_path}/g"
targets:
  kitty:
    template: kitty.conf.j2
    outputs: ["${{repo}}/kitty/theme.conf"]
    skip_unless_path_exists: "${{guard}}"
  other:
    outputs: ["${{repo}}/o"]
    skip_unless_path_exists: ["${{guard}}/a", "${{repo}}"]
""")
    c = HuemanConfig(cfg)
    kitty, other = c.targets
    assert kitty.outputs == [tmp_path / "dot/kitty/theme.conf"]
    assert kitty.skip_unless_path_exists == [tmp_path / "g"]
    assert other.skip_unless_path_exists == [tmp_path / "g/a", tmp_path / "dot"]


def test_vars_substituted_in_state_palette_template_dirs(tmp_path):
    cfg = write_cfg(tmp_path, f"""
vars: {{base: "{tmp_path}"}}
state_file: "${{base}}/state/current"
palette_dirs: ["${{base}}/pal"]
template_dirs: ["${{base}}/tpl"]
""")
    c = HuemanConfig(cfg)
    assert c.state_file == tmp_path / "state/current"
    assert c.palette_dirs == [tmp_path / "pal"]
    assert c.template_dirs == [tmp_path / "tpl"]


def test_var_value_tilde_expanded_after_substitution(tmp_path, isolated_home):
    cfg = write_cfg(tmp_path, 'vars: {repo: "~/dotfiles"}\ntargets:\n  t:\n    outputs: ["${repo}/x"]\n')
    assert HuemanConfig(cfg).targets[0].outputs == [isolated_home / "dotfiles/x"]


def test_undefined_var_in_path_key_is_config_error(tmp_path):
    cfg = write_cfg(tmp_path, 'targets:\n  kitty:\n    outputs: ["${repo}/x"]\n')
    with pytest.raises(ConfigError) as exc:
        HuemanConfig(cfg)
    assert "repo" in str(exc.value) and "kitty" in str(exc.value)


def test_undefined_var_in_top_level_key_is_config_error(tmp_path):
    cfg = write_cfg(tmp_path, 'state_file: "${gone}/s"\n')
    with pytest.raises(ConfigError, match="gone"):
        HuemanConfig(cfg)


@pytest.mark.parametrize("body", [
    "vars: [a]\n",
    "vars: {repo: 3}\n",
    "vars: {repo: [x]}\n",
    'vars: {"bad-name": x}\n',
    'vars: {"1abc": x}\n',
    'vars: {repo: "${other}/x"}\n',
])
def test_invalid_vars_is_config_error(tmp_path, body):
    with pytest.raises(ConfigError):
        HuemanConfig(write_cfg(tmp_path, body))


def test_var_value_with_placeholder_message_is_clear(tmp_path):
    with pytest.raises(ConfigError, match="repo"):
        HuemanConfig(write_cfg(tmp_path, 'vars: {repo: "${x}"}\n'))


def test_empty_var_value_is_allowed(tmp_path):
    cfg = write_cfg(tmp_path, 'vars: {p: ""}\ntargets:\n  t:\n    outputs: ["a${p}b"]\n')
    assert [str(o) for o in HuemanConfig(cfg).targets[0].outputs] == ["ab"]


def test_non_path_keys_are_not_substituted(tmp_path):
    cfg = write_cfg(tmp_path, """
vars: {repo: /r}
post_apply: ["echo ${HOME} ${repo}"]
targets:
  t:
    mode: patch
    outputs: ["/o"]
    reload: "echo ${HOME} ${repo}"
    extra_vars: {k: "${repo}"}
    patch:
      marker_regex: "a${repo}b"
      marker_begin: "# ${repo}"
      marker_end: "# ${repo}"
""")
    c = HuemanConfig(cfg)
    t = c.targets[0]
    assert t.reload == "echo ${HOME} ${repo}"
    assert c.post_apply == ["echo ${HOME} ${repo}"]
    assert t.extra_vars == {"k": "${repo}"}
    assert t.patch.marker_regex == "a${repo}b"
    assert t.patch.marker_begin == "# ${repo}"


def test_config_without_vars_unchanged(tmp_path):
    cfg = write_cfg(tmp_path, 'targets:\n  t:\n    outputs: ["$HOME/x", "/p/y"]\n')
    assert HuemanConfig(cfg).targets[0].outputs[0].parts[-2:] == ("$HOME", "x")


def test_overrides_override_and_add(tmp_path):
    cfg = write_cfg(tmp_path, 'vars: {repo: /file}\ntargets:\n  t:\n    outputs: ["${repo}/${extra}/x"]\n')
    c = HuemanConfig(cfg, var_overrides={"repo": "/cli", "extra": "e"})
    assert str(c.targets[0].outputs[0]) == "/cli/e/x"


def test_overrides_work_without_vars_section(tmp_path):
    cfg = write_cfg(tmp_path, 'targets:\n  t:\n    outputs: ["${repo}/x"]\n')
    assert str(HuemanConfig(cfg, var_overrides={"repo": "/c"}).targets[0].outputs[0]) == "/c/x"


# --- CLI -------------------------------------------------------------------

def test_cli_undefined_var_exits_one_without_traceback(tmp_path, monkeypatch, capsys):
    cfg = write_cfg(tmp_path, 'targets:\n  kitty:\n    outputs: ["${repo}/x"]\n')
    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, "--config", str(cfg), "list")
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "Config invalida" in err and "repo" in err and "Traceback" not in err


@pytest.mark.parametrize("bad", ["novalue", "=x", "bad-name=1", "1a=2", ""])
def test_cli_invalid_var_exits_two(tmp_path, monkeypatch, capsys, bad):
    cfg = write_cfg(tmp_path, "targets: {}\n")
    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, "--config", str(cfg), "--var", bad, "list")
    assert exc.value.code == 2
    assert "--var" in capsys.readouterr().err


def test_cli_help_mentions_var(monkeypatch, capsys):
    with pytest.raises(SystemExit):
        run_cli(monkeypatch, "--help")
    assert "--var" in capsys.readouterr().out


def test_cli_var_value_may_contain_equals(tmp_path, monkeypatch, capsys):
    cfg = write_cfg(tmp_path, 'targets:\n  t:\n    outputs: ["${p}"]\n')
    run_cli(monkeypatch, "--config", str(cfg), "--var", "p=/a=b", "list")


def _set_cfg(tmp_path):
    (tmp_path / "pal").mkdir()
    (tmp_path / "pal/mine.yaml").write_text("name: mine\nbase: {bg: '#000000'}\nkitty: {bg: '#000000'}\n")
    (tmp_path / "tpl").mkdir()
    (tmp_path / "tpl/t.j2").write_text("hello\n")
    return write_cfg(tmp_path, f"""
state_file: "{tmp_path}/state"
palette_dirs: ["{tmp_path}/pal"]
template_dirs: ["{tmp_path}/tpl"]
vars: {{repo: "{tmp_path}/file_repo"}}
targets:
  t:
    template: t.j2
    outputs: ["${{repo}}/out/t.conf"]
""")


def test_cli_set_with_var_writes_under_overridden_dir(tmp_path, monkeypatch):
    cfg = _set_cfg(tmp_path)
    other = tmp_path / "cli_repo"
    run_cli(monkeypatch, "--config", str(cfg), "--var", f"repo={other}", "set", "mine")
    assert (other / "out/t.conf").read_text() == "hello\n"
    assert not (tmp_path / "file_repo").exists()


def test_cli_set_without_var_uses_file_value(tmp_path, monkeypatch):
    cfg = _set_cfg(tmp_path)
    run_cli(monkeypatch, "--config", str(cfg), "set", "mine")
    assert (tmp_path / "file_repo/out/t.conf").exists()


def test_cli_dry_run_prints_overridden_paths(tmp_path, monkeypatch, capsys):
    cfg = _set_cfg(tmp_path)
    other = tmp_path / "cli_repo"
    run_cli(monkeypatch, "--config", str(cfg), "--var", f"repo={other}", "set", "mine", "--dry-run")
    captured = capsys.readouterr()
    assert str(other / "out/t.conf") in captured.out + captured.err
    assert not other.exists()
