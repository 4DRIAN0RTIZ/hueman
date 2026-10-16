"""Shared palette state behind a small `StateSource` interface.

`GitBranchSource` keeps the state in an orphan branch (`hueman-state`) holding
a single parentless commit with `hueman.state.yaml`. All git work happens in a
hueman-owned bare repository (default: XDG state dir), built with plumbing
commands, so the user's dotfiles repo and working tree are never touched; the
dotfiles repo is only consulted to resolve the remote URL.

Rewriting the single commit with `commit-tree` (no parent) is the plumbing
equivalent of `commit --amend`; it is published with `push --force-with-lease`.
Every failure mode (no git, no remote, no network) degrades to None / False
and never raises, so callers can keep applying palettes locally.
"""

import hashlib
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

STATE_FILE_NAME = "hueman.state.yaml"
DEFAULT_BRANCH = "hueman-state"
GIT_TIMEOUT = 30
_REMOTE_REF = "refs/hueman/remote"
_IDENTITY = ["-c", "user.name=hueman", "-c", "user.email=hueman@localhost",
             "-c", "commit.gpgsign=false"]


@dataclass(frozen=True)
class State:
    palette: str
    revision: int


@dataclass(frozen=True)
class StateSyncSettings:
    repo: Path
    remote: str = "origin"
    branch: str = DEFAULT_BRANCH
    workdir: Optional[Path] = None


class StateSource:
    """Backend holding the shared palette state."""

    def read(self) -> Optional[State]:
        raise NotImplementedError

    def write(self, state: State) -> bool:
        """Publish `state`; True only if it is now the shared state."""
        raise NotImplementedError


def dump_state(state: State) -> str:
    return yaml.safe_dump({"palette": state.palette, "revision": state.revision},
                          sort_keys=False)


def parse_state(text: str) -> Optional[State]:
    try:
        raw = yaml.safe_load(text)
        return State(str(raw["palette"]), int(raw["revision"]))
    except (yaml.YAMLError, KeyError, TypeError, ValueError):
        return None


class GitBranchSource(StateSource):
    def __init__(self, repo, remote="origin", branch=DEFAULT_BRANCH, workdir=None,
                 max_retries=3, logger=None):
        self.repo = Path(repo).expanduser()
        self.remote = remote
        self.branch = branch
        self.max_retries = max_retries
        self.log = logger or logging.getLogger("hueman")
        self._workdir = Path(workdir).expanduser() if workdir else None
        self._url = None

    @classmethod
    def from_settings(cls, s: StateSyncSettings, logger=None):
        return cls(s.repo, s.remote, s.branch, s.workdir, logger=logger)

    # -- git plumbing -------------------------------------------------------

    def _run(self, args, git_dir=True, input=None, cwd=None):
        cmd = ["git"]
        if git_dir:
            cmd += ["--git-dir", str(self._workdir)]
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env["GIT_TERMINAL_PROMPT"] = "0"
        try:
            return subprocess.run(cmd + args, input=input, cwd=cwd, env=env,
                                  capture_output=True, text=True, timeout=GIT_TIMEOUT)
        except (OSError, subprocess.SubprocessError) as exc:
            self.log.debug(f"git {' '.join(args)}: {exc}")
            return None

    def _ok(self, args, **kw):
        res = self._run(args, **kw)
        return res.stdout.strip() if res is not None and res.returncode == 0 else None

    def _prepare(self) -> bool:
        """Resolve the remote URL and make sure the private repo exists."""
        if shutil.which("git") is None:
            self.log.warning("git no disponible: estado compartido deshabilitado")
            return False
        url = self._ok(["-C", str(self.repo), "remote", "get-url", self.remote],
                       git_dir=False) if self.repo.is_dir() else None
        if not url:
            self.log.warning(f"remoto '{self.remote}' no disponible en {self.repo}")
            return False
        self._url = url
        if self._workdir is None:
            base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
            digest = hashlib.sha1(f"{url}\0{self.branch}".encode()).hexdigest()[:12]
            self._workdir = base / "hueman" / "state-sync" / f"{digest}.git"
        if not (self._workdir / "HEAD").exists():
            self._workdir.parent.mkdir(parents=True, exist_ok=True)
            if self._ok(["init", "--bare", "-q", str(self._workdir)], git_dir=False) is None:
                self.log.warning(f"no se pudo crear el repo de estado en {self._workdir}")
                return False
        return True

    def _fetch(self):
        """Refresh the remote tip. Returns (ok, sha-or-None)."""
        ls = self._ok(["ls-remote", self._url, f"refs/heads/{self.branch}"])
        if ls is None:
            self.log.warning(f"remoto inalcanzable: {self._url}")
            return False, None
        if not ls:
            self._run(["update-ref", "-d", _REMOTE_REF])
            return True, None
        spec = f"+refs/heads/{self.branch}:{_REMOTE_REF}"
        if self._ok(["fetch", "-q", "--no-tags", self._url, spec]) is None:
            self.log.warning(f"fetch fallo desde {self._url}")
            return False, None
        return True, self._ok(["rev-parse", _REMOTE_REF])

    def _state_at(self, ref) -> Optional[State]:
        text = self._ok(["cat-file", "-p", f"{ref}:{STATE_FILE_NAME}"])
        return parse_state(text) if text else None

    def _commit(self, state: State) -> Optional[str]:
        blob = self._ok(["hash-object", "-w", "--stdin"], input=dump_state(state))
        tree = self._ok(["mktree"], input=f"100644 blob {blob}\t{STATE_FILE_NAME}\n") if blob else None
        if not tree:
            return None
        return self._ok(_IDENTITY + ["commit-tree", tree, "-m", f"hueman state r{state.revision}"])

    def _push(self, sha: str, expected: Optional[str]) -> bool:
        ref = f"refs/heads/{self.branch}"
        res = self._run(["push", "-q", f"--force-with-lease={ref}:{expected or ''}",
                         self._url, f"{sha}:{ref}"])
        return res is not None and res.returncode == 0

    # -- StateSource --------------------------------------------------------

    def read(self) -> Optional[State]:
        if not self._prepare():
            return None
        ok, sha = self._fetch()
        if ok:
            return self._state_at(sha) if sha else None
        return self._state_at(f"refs/heads/{self.branch}")  # last known local copy

    def write(self, state: State) -> bool:
        if not self._prepare():
            return False
        for _ in range(self.max_retries + 1):
            ok, remote_sha = self._fetch()
            if not ok:
                return False
            remote = self._state_at(remote_sha) if remote_sha else None
            if remote is not None:
                if remote.revision > state.revision:
                    self.log.warning(
                        f"estado remoto mas nuevo (r{remote.revision} > r{state.revision}, "
                        f"paleta {remote.palette}); no se publica")
                    return False
                if remote == state:
                    return True
            sha = self._commit(state)
            if sha is None:
                self.log.warning("no se pudo construir el commit de estado")
                return False
            if self._push(sha, remote_sha):
                self._run(["update-ref", f"refs/heads/{self.branch}", sha])
                return True
        self.log.warning("push de estado rechazado repetidamente; se desiste")
        return False
