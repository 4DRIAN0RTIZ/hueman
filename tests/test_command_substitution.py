import pytest

from hueman.engine.reload import expand_command


PALETTE = {"kitty": {"color4": "#112233"}, "polybar": {"primary": "#abcdef"}}


def test_expands_name_and_palette_alias():
    assert expand_command("x {name} {palette}", "dracula", PALETTE) == "x dracula dracula"


def test_expands_dotted_lookup_with_shell_quoting():
    out = expand_command("x --c {kitty.color4}", "demo", PALETTE)
    assert out == "x --c '#112233'"


def test_quotes_unsafe_values():
    out = expand_command("echo {name}", "a b; rm", PALETTE)
    assert out == "echo 'a b; rm'"


def test_commands_without_braces_unchanged():
    cmd = 'echo "${HOME}" $(hostname) || true'
    assert expand_command(cmd, "demo", PALETTE) == cmd


def test_dollar_brace_and_unknown_plain_braces_left_alone():
    cmd = "echo ${name} ${kitty.color4}; find . -exec ls {} +; awk '{print $1}'"
    assert expand_command(cmd, "demo", PALETTE) == cmd


def test_unknown_dotted_key_fails_clearly():
    with pytest.raises(ValueError, match="kitty.nope"):
        expand_command("x {kitty.nope}", "demo", PALETTE)


def test_set_theme_expands_post_apply_placeholders(tmp_path, monkeypatch):
    from hueman.engine.config import HuemanConfig
    from hueman.cli import Hueman

    (tmp_path / "pal.yaml").write_text("kitty:\n  color4: '#112233'\n")
    cfg = tmp_path / "h.yaml"
    cfg.write_text(
        f"state_file: {tmp_path / 'state'}\npalette_dirs: [{tmp_path}]\n"
        "targets: {}\npost_apply: ['run {name} {kitty.color4} ${HOME}']\n"
    )
    calls = []
    monkeypatch.setattr("hueman.cli.run_post_apply", lambda commands, logger: calls.append(commands))
    Hueman(HuemanConfig(cfg)).set_theme("pal")
    assert calls == [["run pal '#112233' ${HOME}"]]
