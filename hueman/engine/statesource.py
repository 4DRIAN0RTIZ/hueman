"""Shared palette state behind a small `StateSource` interface.

The engine only ever talks to `StateSource` (see its docstring for the
contract) and obtains one through `build_source(settings)`; the backend is
chosen declaratively by `state_sync.type` and looked up in a registry.
Backends: `git` (default) and `file` (a state file in a synced folder).

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
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, ClassVar, Optional

import yaml

from .fsutil import atomic_write_text
from .palettes import is_valid_palette_name

STATE_FILE_NAME = "hueman.state.yaml"
DEFAULT_BRANCH = "hueman-state"
GIT_TIMEOUT = 15  # seconds per git call; keeps shell-startup sync bounded
_REMOTE_REF = "refs/hueman/remote"
_IDENTITY = ["-c", "user.name=hueman", "-c", "user.email=hueman@localhost",
             "-c", "commit.gpgsign=false"]


@dataclass(frozen=True)
class State:
    palette: str
    revision: int


@dataclass(frozen=True)
class ReadResult:
    """Outcome of a read. `remote` is True only when the state was just
    fetched from the remote (an empty remote is still remote=True, state=None);
    False means the remote was unreachable and `state` is the local cache."""
    state: Optional[State]
    remote: bool


@dataclass(frozen=True)
class StateSyncSettings:
    """Settings of the `git` backend (`state_sync.type: git`, the default)."""
    type: ClassVar[str] = "git"
    repo: Path
    remote: str = "origin"
    branch: str = DEFAULT_BRANCH
    workdir: Optional[Path] = None
    timeout: int = GIT_TIMEOUT


class StateSource(ABC):
    """Backend holding the shared palette state.

    Contract every backend must honour (checked by
    tests/test_state_source_contract.py):

    * Never raise: every failure (missing tool, unreachable store, corrupt
      data, I/O error, timeout) degrades to the "unreachable"/False results
      below so callers can keep applying palettes locally.
    * Bounded time: every blocking operation has a timeout; a backend must
      not hang shell startup.
    * `revision` is a monotonic integer. Higher revision wins; on a tie the
      accepted write wins (last writer), mirroring the git push rule.
    """

    @abstractmethod
    def read_result(self) -> ReadResult:
        """Read the shared state.

        `ReadResult(state, remote=True)`: the store was reached; `state` is
        None when it is empty or its content is unparseable.
        `ReadResult(state, remote=False)`: the store was unreachable; `state`
        is a possibly stale local cache or None, and callers must not apply it.
        """

    def read(self) -> Optional[State]:
        """Convenience: just the state of `read_result()`."""
        return self.read_result().state

    @abstractmethod
    def write(self, state: State) -> bool:
        """Publish `state`; True only if it is now the shared state.

        Returns True when the store already holds exactly `state`. Returns
        False, without overwriting, when the store holds a strictly higher
        revision, and False when the store is unreachable or the write fails.
        """


def dump_state(state: State) -> str:
    return yaml.safe_dump({"palette": state.palette, "revision": state.revision},
                          sort_keys=False)


def parse_state(text: str) -> Optional[State]:
    try:
        raw = yaml.safe_load(text)
        state = State(str(raw["palette"]), int(raw["revision"]))
    except (yaml.YAMLError, KeyError, TypeError, ValueError):
        return None
    # el nombre viene del remoto: uno invalido (ruta, '..') es dato inutilizable
    return state if is_valid_palette_name(state.palette) else None


class GitBranchSource(StateSource):
    def __init__(self, repo, remote="origin", branch=DEFAULT_BRANCH, workdir=None,
                 max_retries=3, logger=None, timeout=GIT_TIMEOUT):
        self.timeout = timeout
        self.repo = Path(repo).expanduser()
        self.remote = remote
        self.branch = branch
        self.max_retries = max_retries
        self.log = logger or logging.getLogger("hueman")
        self._workdir = Path(workdir).expanduser() if workdir else None
        self._url = None

    @classmethod
    def from_settings(cls, s: StateSyncSettings, logger=None):
        return cls(s.repo, s.remote, s.branch, s.workdir, logger=logger, timeout=s.timeout)

    # -- git plumbing -------------------------------------------------------

    def _run(self, args, git_dir=True, input=None, cwd=None):
        cmd = ["git"]
        if git_dir:
            cmd += ["--git-dir", str(self._workdir)]
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env["GIT_TERMINAL_PROMPT"] = "0"
        for keep in ("GIT_SSH", "GIT_SSH_COMMAND"):  # user's transport choice
            if keep in os.environ:
                env[keep] = os.environ[keep]
        if "GIT_SSH" not in env:
            env.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")  # never prompt
        try:
            return subprocess.run(cmd + args, input=input, cwd=cwd, env=env,
                                  capture_output=True, text=True, timeout=self.timeout)
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

    def read_result(self) -> ReadResult:
        if not self._prepare():
            return ReadResult(None, False)
        ok, sha = self._fetch()
        if ok:
            return ReadResult(self._state_at(sha) if sha else None, True)
        # remote unreachable: last known local copy, flagged as such
        # (last fetched tip; readers never write refs/heads, only publishers do)
        cached = self._state_at(_REMOTE_REF) or self._state_at(f"refs/heads/{self.branch}")
        return ReadResult(cached, False)

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


class FileSource(StateSource):
    """State file in a folder synced by something else (Syncthing, Dropbox...).

    Same YAML format as the git backend. The write is atomic (temp file +
    rename via `engine.fsutil`), so the sync tool never uploads a partial file.
    There is no cross-node lock: simultaneous writers are reconciled by the
    sync tool (e.g. conflict copies) and by the higher-revision-wins rule on
    the next read/write. A missing parent folder means the synced folder is
    not mounted: unreachable, and it is never created.
    """

    def __init__(self, path, logger=None):
        self.path = Path(path).expanduser()
        self.log = logger or logging.getLogger("hueman")

    @classmethod
    def from_settings(cls, s: "FileSettings", logger=None):
        return cls(s.path, logger=logger)

    def read_result(self) -> ReadResult:
        try:
            if not self.path.parent.is_dir():
                return ReadResult(None, False)
            try:
                text = self.path.read_text(encoding="utf-8")
            except FileNotFoundError:
                return ReadResult(None, True)
            return ReadResult(parse_state(text), True)
        except (OSError, UnicodeDecodeError) as exc:
            self.log.debug(f"{self.path}: {exc}")
            return ReadResult(None, False)

    def write(self, state: State) -> bool:
        res = self.read_result()
        if not res.remote:
            self.log.warning(f"carpeta de estado no disponible: {self.path.parent}")
            return False
        current = res.state
        if current is not None:
            if current.revision > state.revision:
                self.log.warning(
                    f"estado compartido mas nuevo (r{current.revision} > r{state.revision}, "
                    f"paleta {current.palette}); no se publica")
                return False
            if current == state:
                return True
        try:
            atomic_write_text(self.path, dump_state(state))
        except OSError as exc:
            self.log.warning(f"no se pudo escribir {self.path}: {exc}")
            return False
        return self.read() == state


@dataclass(frozen=True)
class FileSettings:
    """Settings of the `file` backend (`state_sync.type: file`)."""
    type: ClassVar[str] = "file"
    path: Path


# -- registry -----------------------------------------------------------------

class StateSyncConfigError(ValueError):
    """Invalid `state_sync` mapping (caller adds file context)."""


def _parse_git(raw: dict) -> StateSyncSettings:
    if not isinstance(raw.get("repo"), str) or not raw["repo"]:
        raise StateSyncConfigError("'state_sync' (type git) debe ser un mapeo con 'repo'")
    for key in ("remote", "branch", "workdir"):
        if key in raw and not isinstance(raw[key], str):
            raise StateSyncConfigError(f"state_sync.{key} debe ser texto")
    timeout = raw.get("timeout", GIT_TIMEOUT)
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
        raise StateSyncConfigError("state_sync.timeout debe ser un entero > 0 (segundos)")
    workdir = raw.get("workdir")
    return StateSyncSettings(
        repo=Path(raw["repo"]).expanduser(),
        remote=raw.get("remote", "origin"),
        branch=raw.get("branch", DEFAULT_BRANCH),
        workdir=Path(workdir).expanduser() if workdir else None,
        timeout=timeout,
    )


def _parse_file(raw: dict) -> FileSettings:
    if not isinstance(raw.get("path"), str) or not raw["path"]:
        raise StateSyncConfigError("'state_sync' (type file) debe ser un mapeo con 'path'")
    return FileSettings(path=Path(raw["path"]).expanduser())


# type name -> (parse raw mapping into settings, build source from settings)
SOURCE_TYPES: dict = {
    "git": (_parse_git, GitBranchSource.from_settings),
    "file": (_parse_file, FileSource.from_settings),
}
DEFAULT_TYPE = "git"


def parse_settings(raw):
    """Validate a `state_sync` mapping and return the backend's settings."""
    if not isinstance(raw, dict):
        raise StateSyncConfigError("'state_sync' debe ser un mapeo")
    kind = raw.get("type", DEFAULT_TYPE)
    if not isinstance(kind, str) or kind not in SOURCE_TYPES:
        raise StateSyncConfigError(
            f"state_sync.type desconocido: {kind!r} (validos: {', '.join(sorted(SOURCE_TYPES))})")
    return SOURCE_TYPES[kind][0](raw)


def build_source(settings, logger=None) -> StateSource:
    """Instantiate the backend that `settings` belongs to."""
    return SOURCE_TYPES[settings.type][1](settings, logger)
