import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path_factory, monkeypatch):
    """Point HOME and XDG dirs at a throwaway dir so no test can ever read or
    write the real user home (default state_file and config live under it)."""
    home = tmp_path_factory.mktemp("home")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.delenv("HUEMAN_CONFIG", raising=False)
    return home
