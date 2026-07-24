# AgentQA Studio — M1 (Dashboard daemon + viewer) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `agentqa-studio` — a local web dashboard that shows the test rig's readiness, runs the pytest suite with live output, and browses the behavioral-memory store — all without any agent attached.

**Architecture:** A single-process Python daemon built on the stdlib `http.server` (threaded, for SSE) serves a vanilla-JS single-page UI plus a small JSON/SSE API. The daemon reads `.agentqa/config.yml` and drives four focused modules (config, rig, runner, memory-view). No web framework, no npm, no build step. This is "Half A" of the Studio design — the always-on viewer. The agent bridge ("Half B") is a separate later plan.

**Tech Stack:** Python 3.9 stdlib (`http.server`, `subprocess`, `socket`, `json`, `pathlib`), vanilla HTML/CSS/JS, pytest for tests.

## Global Constraints

- **No new runtime dependencies.** Config is parsed with a small dependency-free
  reader, matching the repo's existing `sed`-based `config_get` approach — do
  **not** add pyyaml or any package. (verbatim house rule)
- **Python 3.9.6** — no 3.10+ syntax (no `match`, no `X | Y` unions in
  annotations; use `Optional[...]`, `Dict[...]`).
- **Stdlib `http.server` only** — no Flask, no npm, no build step.
- **Studio port: 7332** (Appium owns 4723; keep them distinct).
- **Credential values are never stored or logged** — only the env-var *names*
  from the config are shown; values are passed through for a single run.
- **No commits or pushes without the user's say-so.** Each task below ends with a
  `git commit` *only after the user has approved that task's diff*; never push.
- **Command name is `agentqa-studio`** (hyphen), realizing the design's
  "`agentqa studio`" as a single hyphenated command consistent with the repo's
  skill-naming convention.

---

## File Structure

All new code lives in a repo-root `studio/` package (the daemon is machine-level,
not a skill — the connector skill in M2 will shell out to it):

- `studio/config.py` — load `.agentqa/config.yml`, produce a flat summary. One responsibility: config.
- `studio/rig.py` — precondition checks (simulator, app installed, Appium, CodeGraph). Shells out; mockable.
- `studio/runner.py` — list tests, build the pytest command, run it streaming, locate failure artifacts.
- `studio/memory_view.py` — list/read memory notes; optionally run `--stale` and `lint` via the write-test scripts.
- `studio/server.py` — HTTP routing, JSON endpoints, SSE, static file serving, `main()`.
- `studio/static/index.html` — the single page.
- `studio/static/app.js` — fetches the API, renders the four panels, tails SSE.
- `studio/static/style.css` — minimal styling, light/dark aware.
- `studio/tests/test_config.py`, `test_rig.py`, `test_runner.py`, `test_memory_view.py`, `test_server.py` — unit/integration tests.
- `bin/agentqa-studio` — launcher: resolve repo root + script paths, exec the server.

**Test venv:** the project's `.devvenv` already has `pytest` (Python 3.9.6). Run
tests with `.devvenv/bin/pytest` from the repo root.

---

### Task 1: Config loader (`studio/config.py`)

Parse the project's `.agentqa/config.yml` into a nested dict with a tiny
dependency-free reader, then flatten it into the summary the UI needs.

**Files:**
- Create: `studio/config.py`
- Create: `studio/__init__.py` (empty package marker)
- Test: `studio/tests/test_config.py`
- Create: `studio/tests/__init__.py` (empty)

**Interfaces:**
- Produces:
  - `load_config(repo_root: pathlib.Path) -> Dict[str, Any]` — nested dict; raises `FileNotFoundError` if `.agentqa/config.yml` is absent.
  - `config_summary(cfg: Dict[str, Any]) -> Dict[str, Any]` — returns keys: `platform` (str), `app_id` (str; `bundle_id` on iOS else `app_package`), `test_dir` (str), `build_policy` (str), `reset_app_data` (str), `appium_port` (int, default 4723), `cred_env` (dict `{username, password}`), `identifier_convention` (str).

- [ ] **Step 1: Write the failing tests**

```python
# studio/tests/test_config.py
import textwrap
from pathlib import Path

from studio.config import load_config, config_summary


def _write_cfg(tmp_path: Path, body: str) -> Path:
    d = tmp_path / ".agentqa"
    d.mkdir(parents=True)
    (d / "config.yml").write_text(textwrap.dedent(body))
    return tmp_path


IOS_CFG = """\
    platform: ios
    bundle_id: com.vnpt.media.mobileb2c
    test_dir: AutomationTests
    build:
      policy: human
      note: "Manual builds required"
    reset_app_data: always
    credentials:
      username_env: APP_TEST_USERNAME
      password_env: APP_TEST_PASSWORD
    identifier_convention: screen_element_type
    appium:
      port: 4723
"""


def test_load_config_reads_nested_scalars(tmp_path):
    root = _write_cfg(tmp_path, IOS_CFG)
    cfg = load_config(root)
    assert cfg["platform"] == "ios"
    assert cfg["bundle_id"] == "com.vnpt.media.mobileb2c"
    assert cfg["build"]["policy"] == "human"
    assert cfg["credentials"]["username_env"] == "APP_TEST_USERNAME"
    assert cfg["appium"]["port"] == 4723


def test_load_config_missing_raises(tmp_path):
    try:
        load_config(tmp_path)
        assert False, "expected FileNotFoundError"
    except FileNotFoundError:
        pass


def test_summary_ios(tmp_path):
    root = _write_cfg(tmp_path, IOS_CFG)
    s = config_summary(load_config(root))
    assert s["platform"] == "ios"
    assert s["app_id"] == "com.vnpt.media.mobileb2c"
    assert s["test_dir"] == "AutomationTests"
    assert s["build_policy"] == "human"
    assert s["appium_port"] == 4723
    assert s["cred_env"] == {"username": "APP_TEST_USERNAME", "password": "APP_TEST_PASSWORD"}


def test_summary_android_uses_app_package(tmp_path):
    root = _write_cfg(tmp_path, """\
        platform: android
        app_package: com.example.app
        app_activity: .MainActivity
        test_dir: AutomationTests
        build:
          policy: agent
        reset_app_data: always
        identifier_convention: screen_element_type
    """)
    s = config_summary(load_config(root))
    assert s["platform"] == "android"
    assert s["app_id"] == "com.example.app"
    assert s["appium_port"] == 4723  # default when appium block absent
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.devvenv/bin/pytest studio/tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'studio.config'`

- [ ] **Step 3: Write the minimal implementation**

```python
# studio/config.py
"""Read .agentqa/config.yml without a YAML dependency.

Matches the repo's existing sed-based `config_get` approach: the config is a
small, flat-ish document (top-level scalars plus a few one-level-nested blocks),
so a purpose-built reader is simpler and dependency-free.
"""
from pathlib import Path
from typing import Any, Dict, Optional


def _strip(value: str) -> str:
    # drop trailing inline comment, surrounding quotes, whitespace
    cut = value.split("#", 1)[0].strip()
    if len(cut) >= 2 and cut[0] in "\"'" and cut[-1] == cut[0]:
        cut = cut[1:-1]
    return cut


def _coerce(value: str) -> Any:
    if value.isdigit():
        return int(value)
    return value


def load_config(repo_root: Path) -> Dict[str, Any]:
    path = Path(repo_root) / ".agentqa" / "config.yml"
    if not path.is_file():
        raise FileNotFoundError(str(path))

    result: Dict[str, Any] = {}
    current: Optional[str] = None  # key of the open nested block, if any
    for raw in path.read_text().splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indented = raw[0] in " \t"
        line = raw.strip()
        if ":" not in line:
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        if indented and current is not None:
            block = result.setdefault(current, {})
            if isinstance(block, dict):
                block[key] = _coerce(_strip(rest)) if rest else {}
            continue
        # top level
        if rest == "":
            current = key
            result.setdefault(key, {})
        else:
            current = None
            result[key] = _coerce(_strip(rest))
    return result


def config_summary(cfg: Dict[str, Any]) -> Dict[str, Any]:
    platform = cfg.get("platform", "ios")
    app_id = cfg.get("bundle_id") if platform == "ios" else cfg.get("app_package")
    build = cfg.get("build") or {}
    creds = cfg.get("credentials") or {}
    appium = cfg.get("appium") or {}
    return {
        "platform": platform,
        "app_id": app_id or "",
        "test_dir": cfg.get("test_dir", ""),
        "build_policy": build.get("policy", "human"),
        "reset_app_data": cfg.get("reset_app_data", "always"),
        "appium_port": int(appium.get("port", 4723)),
        "cred_env": {
            "username": creds.get("username_env", ""),
            "password": creds.get("password_env", ""),
        },
        "identifier_convention": cfg.get("identifier_convention", ""),
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.devvenv/bin/pytest studio/tests/test_config.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit (only after the user approves this task's diff)**

```bash
git add studio/config.py studio/__init__.py studio/tests/__init__.py studio/tests/test_config.py
git commit -m "feat(studio): config loader for .agentqa/config.yml"
```

---

### Task 2: Rig precondition checks (`studio/rig.py`)

Report whether the machine is ready to run tests: simulator/emulator booted, app
installed, Appium up, CodeGraph indexed. Shell commands are isolated behind one
helper so tests can mock them.

**Files:**
- Create: `studio/rig.py`
- Test: `studio/tests/test_rig.py`

**Interfaces:**
- Consumes: `config_summary(...)` output (Task 1) — reads `platform`, `app_id`, `appium_port`.
- Produces:
  - `check_rig(summary: Dict[str, Any], repo_root: pathlib.Path) -> Dict[str, Any]` — returns `{"simulator": bool, "app_installed": bool, "appium": bool, "codegraph": bool}`.
  - Internal, patchable: `_run(cmd: List[str]) -> Tuple[int, str]` (returncode, stdout+stderr).

- [ ] **Step 1: Write the failing tests**

```python
# studio/tests/test_rig.py
from pathlib import Path
from unittest import mock

from studio import rig

IOS = {"platform": "ios", "app_id": "com.acme.app", "appium_port": 4723}


def test_ios_all_green(tmp_path):
    (tmp_path / ".codegraph").mkdir()
    def fake_run(cmd):
        joined = " ".join(cmd)
        if "list" in cmd and "devices" in cmd:
            return (0, "iPhone 15 (ABC) (Booted)")
        if "listapps" in cmd:
            return (0, "com.acme.app = { ... }")
        if cmd[0] == "nc":
            return (0, "")
        return (1, "")
    with mock.patch.object(rig, "_run", side_effect=fake_run):
        out = rig.check_rig(IOS, tmp_path)
    assert out == {"simulator": True, "app_installed": True, "appium": True, "codegraph": True}


def test_ios_appium_down_and_no_codegraph(tmp_path):
    def fake_run(cmd):
        if "list" in cmd and "devices" in cmd:
            return (0, "iPhone 15 (ABC) (Booted)")
        if "listapps" in cmd:
            return (0, "com.acme.app = { ... }")
        if cmd[0] == "nc":
            return (1, "")  # appium down
        return (1, "")
    with mock.patch.object(rig, "_run", side_effect=fake_run):
        out = rig.check_rig(IOS, tmp_path)
    assert out["simulator"] is True
    assert out["app_installed"] is True
    assert out["appium"] is False
    assert out["codegraph"] is False  # no .codegraph dir


def test_app_not_installed(tmp_path):
    (tmp_path / ".codegraph").mkdir()
    def fake_run(cmd):
        if "list" in cmd and "devices" in cmd:
            return (0, "Booted")
        if "listapps" in cmd:
            return (0, "com.other.app = {}")  # ours absent
        if cmd[0] == "nc":
            return (0, "")
        return (1, "")
    with mock.patch.object(rig, "_run", side_effect=fake_run):
        out = rig.check_rig(IOS, tmp_path)
    assert out["app_installed"] is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.devvenv/bin/pytest studio/tests/test_rig.py -v`
Expected: FAIL — `AttributeError: module 'studio.rig' has no attribute 'check_rig'`

- [ ] **Step 3: Write the minimal implementation**

```python
# studio/rig.py
"""Rig readiness checks. All shell calls funnel through _run so tests mock once."""
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _run(cmd: List[str]) -> Tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return 1, ""


def _appium_up(port: int) -> bool:
    rc, _ = _run(["nc", "-z", "127.0.0.1", str(port)])
    return rc == 0


def _codegraph_indexed(repo_root: Path) -> bool:
    return (Path(repo_root) / ".codegraph").is_dir()


def _ios(summary: Dict[str, Any]) -> Tuple[bool, bool]:
    rc, out = _run(["xcrun", "simctl", "list", "devices", "booted"])
    booted = rc == 0 and "Booted" in out
    installed = False
    if booted:
        rc2, out2 = _run(["xcrun", "simctl", "listapps", "booted"])
        installed = rc2 == 0 and summary["app_id"] in out2
    return booted, installed


def _android(summary: Dict[str, Any]) -> Tuple[bool, bool]:
    rc, out = _run(["adb", "devices"])
    booted = rc == 0 and any(
        line.strip().endswith("device") for line in out.splitlines()[1:]
    )
    installed = False
    if booted:
        rc2, out2 = _run(["adb", "shell", "pm", "list", "packages"])
        installed = rc2 == 0 and ("package:" + summary["app_id"]) in out2
    return booted, installed


def check_rig(summary: Dict[str, Any], repo_root: Path) -> Dict[str, Any]:
    if summary.get("platform") == "android":
        simulator, app_installed = _android(summary)
    else:
        simulator, app_installed = _ios(summary)
    return {
        "simulator": simulator,
        "app_installed": app_installed,
        "appium": _appium_up(int(summary.get("appium_port", 4723))),
        "codegraph": _codegraph_indexed(repo_root),
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.devvenv/bin/pytest studio/tests/test_rig.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit (only after the user approves this task's diff)**

```bash
git add studio/rig.py studio/tests/test_rig.py
git commit -m "feat(studio): rig precondition checks (sim/app/appium/codegraph)"
```

---

### Task 3: Test runner (`studio/runner.py`)

List tests, build the pytest command, run it while streaming output, and locate
failure artifacts. Streaming is line-buffered through an in-memory registry keyed
by run id; one run at a time is fine for v1.

**Files:**
- Create: `studio/runner.py`
- Test: `studio/tests/test_runner.py`

**Interfaces:**
- Consumes: `summary["test_dir"]` (Task 1), `repo_root`.
- Produces:
  - `list_tests(repo_root: Path, test_dir: str) -> List[str]` — `test_*.py` filenames under `<test_dir>/tests`, sorted.
  - `build_command(repo_root: Path, test_dir: str, target: str) -> List[str]` — pytest argv; `target == "all"` runs `tests`, otherwise runs `tests/<target>`.
  - `RunManager` — `start(repo_root, test_dir, target, env: Dict[str,str]) -> str` (run_id); `lines(run_id) -> Iterator[str]` yields output lines until the process ends then a final `"__END__:<rc>"`; `status(run_id) -> str` in `{"running","done","error"}`.
  - `find_artifacts(repo_root: Path, test_dir: str) -> List[Dict[str,str]]` — one entry per `failed_*.xml` in `<test_dir>/artifacts`, each `{"name","xml","png"}` (png key present only if the sibling image exists).

- [ ] **Step 1: Write the failing tests**

```python
# studio/tests/test_runner.py
import sys
from pathlib import Path

from studio import runner


def _mk_tests(tmp_path: Path):
    tdir = tmp_path / "AutomationTests" / "tests"
    tdir.mkdir(parents=True)
    (tdir / "test_login.py").write_text("def test_ok():\n    assert True\n")
    (tdir / "test_checkout.py").write_text("def test_ok():\n    assert True\n")
    (tdir / "helper.py").write_text("# not a test\n")
    return tmp_path


def test_list_tests_only_test_files_sorted(tmp_path):
    _mk_tests(tmp_path)
    assert runner.list_tests(tmp_path, "AutomationTests") == [
        "test_checkout.py",
        "test_login.py",
    ]


def test_build_command_all(tmp_path):
    cmd = runner.build_command(tmp_path, "AutomationTests", "all")
    assert cmd[-2:] == ["tests", "-v"]


def test_build_command_single_file(tmp_path):
    cmd = runner.build_command(tmp_path, "AutomationTests", "test_login.py")
    assert cmd[-2:] == ["tests/test_login.py", "-v"]


def test_run_streams_lines_and_end_marker(tmp_path):
    _mk_tests(tmp_path)
    mgr = runner.RunManager()
    # run a trivial python instead of pytest to keep the test hermetic
    mgr._cmd_override = [sys.executable, "-c", "print('hello'); print('world')"]
    rid = mgr.start(tmp_path, "AutomationTests", "all", {})
    collected = list(mgr.lines(rid))
    assert "hello" in collected
    assert "world" in collected
    assert collected[-1].startswith("__END__:")
    assert mgr.status(rid) == "done"


def test_find_artifacts(tmp_path):
    adir = tmp_path / "AutomationTests" / "artifacts"
    adir.mkdir(parents=True)
    (adir / "failed_test_login.xml").write_text("<testsuite/>")
    (adir / "failed_test_login.png").write_bytes(b"\x89PNG")
    (adir / "failed_test_checkout.xml").write_text("<testsuite/>")
    arts = runner.find_artifacts(tmp_path, "AutomationTests")
    by_name = {a["name"]: a for a in arts}
    assert "failed_test_login" in by_name
    assert by_name["failed_test_login"]["png"].endswith("failed_test_login.png")
    assert "png" not in by_name["failed_test_checkout"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.devvenv/bin/pytest studio/tests/test_runner.py -v`
Expected: FAIL — `AttributeError: module 'studio.runner' has no attribute 'list_tests'`

- [ ] **Step 3: Write the minimal implementation**

```python
# studio/runner.py
"""List and run the pytest suite, streaming output; find failure artifacts."""
import os
import subprocess
import threading
import uuid
from pathlib import Path
from queue import Queue
from typing import Dict, Iterator, List, Optional


def list_tests(repo_root: Path, test_dir: str) -> List[str]:
    tdir = Path(repo_root) / test_dir / "tests"
    if not tdir.is_dir():
        return []
    return sorted(p.name for p in tdir.glob("test_*.py"))


def build_command(repo_root: Path, test_dir: str, target: str) -> List[str]:
    venv_pytest = Path(repo_root) / test_dir / ".venv" / "bin" / "pytest"
    pytest = str(venv_pytest) if venv_pytest.exists() else "pytest"
    sub = "tests" if target == "all" else "tests/" + target
    return [pytest, sub, "-v"]


class RunManager:
    def __init__(self) -> None:
        self._queues: Dict[str, "Queue[str]"] = {}
        self._status: Dict[str, str] = {}
        self._cmd_override: Optional[List[str]] = None  # tests inject a hermetic cmd

    def start(self, repo_root: Path, test_dir: str, target: str, env: Dict[str, str]) -> str:
        run_id = uuid.uuid4().hex
        q: "Queue[str]" = Queue()
        self._queues[run_id] = q
        self._status[run_id] = "running"
        cmd = self._cmd_override or build_command(repo_root, test_dir, target)
        cwd = str(Path(repo_root) / test_dir)
        full_env = {**os.environ, **{k: v for k, v in env.items() if v is not None}}
        threading.Thread(
            target=self._pump, args=(run_id, cmd, cwd, full_env, q), daemon=True
        ).start()
        return run_id

    def _pump(self, run_id, cmd, cwd, env, q) -> None:
        try:
            p = subprocess.Popen(
                cmd, cwd=cwd, env=env, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, bufsize=1,
            )
            for line in iter(p.stdout.readline, ""):
                q.put(line.rstrip("\n"))
            p.stdout.close()
            rc = p.wait()
            self._status[run_id] = "done"
            q.put("__END__:%d" % rc)
        except Exception as exc:  # noqa: BLE001 - surface any launch failure to the UI
            self._status[run_id] = "error"
            q.put("studio: failed to run: %s" % exc)
            q.put("__END__:1")

    def lines(self, run_id: str) -> Iterator[str]:
        q = self._queues[run_id]
        while True:
            item = q.get()
            yield item
            if item.startswith("__END__:"):
                return

    def status(self, run_id: str) -> str:
        return self._status.get(run_id, "unknown")


def find_artifacts(repo_root: Path, test_dir: str) -> List[Dict[str, str]]:
    adir = Path(repo_root) / test_dir / "artifacts"
    if not adir.is_dir():
        return []
    out: List[Dict[str, str]] = []
    for xml in sorted(adir.glob("failed_*.xml")):
        name = xml.stem
        entry = {"name": name, "xml": str(xml)}
        png = xml.with_suffix(".png")
        if png.exists():
            entry["png"] = str(png)
        out.append(entry)
    return out
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.devvenv/bin/pytest studio/tests/test_runner.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit (only after the user approves this task's diff)**

```bash
git add studio/runner.py studio/tests/test_runner.py
git commit -m "feat(studio): pytest runner with streamed output + artifact lookup"
```

---

### Task 4: Memory view (`studio/memory_view.py`)

List and read the behavioral-memory notes, and — when the write-test skill's
scripts are reachable — run `--stale` and `memory-lint`. Those two degrade
gracefully to `None` when the scripts dir isn't provided.

**Files:**
- Create: `studio/memory_view.py`
- Test: `studio/tests/test_memory_view.py`

**Interfaces:**
- Consumes: `repo_root`; optional `memory_scripts_dir: Optional[Path]` (the installed `agentqa-write-test/scripts` dir).
- Produces:
  - `list_notes(repo_root: Path) -> Dict[str, Any]` — `{"flows": [names], "screens": [names], "failures": [names], "env": bool}` (names are filenames without `.md`).
  - `read_note(repo_root: Path, rel_path: str) -> str` — raw markdown; `rel_path` is validated to stay within `.agentqa/memory` (raises `ValueError` otherwise).
  - `stale(repo_root: Path, scripts: Optional[Path]) -> Optional[str]` — stdout of `memory-index.py --stale`, or `None` if `scripts` is falsy/missing.
  - `lint(repo_root: Path, scripts: Optional[Path]) -> Optional[Dict[str, Any]]` — `{"ok": bool, "output": str}` or `None`.

- [ ] **Step 1: Write the failing tests**

```python
# studio/tests/test_memory_view.py
from pathlib import Path

import pytest

from studio import memory_view


def _mk_mem(tmp_path: Path):
    mem = tmp_path / ".agentqa" / "memory"
    (mem / "flows").mkdir(parents=True)
    (mem / "screens").mkdir()
    (mem / "failures").mkdir()
    (mem / "flows" / "login.md").write_text("# login flow\n")
    (mem / "screens" / "login.md").write_text("# login screen\n")
    (mem / "env.md").write_text("env notes\n")
    return tmp_path


def test_list_notes(tmp_path):
    _mk_mem(tmp_path)
    notes = memory_view.list_notes(tmp_path)
    assert notes["flows"] == ["login"]
    assert notes["screens"] == ["login"]
    assert notes["failures"] == []
    assert notes["env"] is True


def test_read_note_ok(tmp_path):
    _mk_mem(tmp_path)
    assert "login flow" in memory_view.read_note(tmp_path, "flows/login.md")


def test_read_note_rejects_traversal(tmp_path):
    _mk_mem(tmp_path)
    with pytest.raises(ValueError):
        memory_view.read_note(tmp_path, "../../etc/passwd")


def test_stale_and_lint_none_without_scripts(tmp_path):
    _mk_mem(tmp_path)
    assert memory_view.stale(tmp_path, None) is None
    assert memory_view.lint(tmp_path, None) is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.devvenv/bin/pytest studio/tests/test_memory_view.py -v`
Expected: FAIL — `AttributeError: module 'studio.memory_view' has no attribute 'list_notes'`

- [ ] **Step 3: Write the minimal implementation**

```python
# studio/memory_view.py
"""Read the .agentqa/memory store; optionally run stale/lint via write-test scripts."""
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


def _mem(repo_root: Path) -> Path:
    return Path(repo_root) / ".agentqa" / "memory"


def _names(d: Path) -> List[str]:
    if not d.is_dir():
        return []
    return sorted(p.stem for p in d.glob("*.md"))


def list_notes(repo_root: Path) -> Dict[str, Any]:
    mem = _mem(repo_root)
    return {
        "flows": _names(mem / "flows"),
        "screens": _names(mem / "screens"),
        "failures": _names(mem / "failures"),
        "env": (mem / "env.md").is_file(),
    }


def read_note(repo_root: Path, rel_path: str) -> str:
    mem = _mem(repo_root).resolve()
    target = (mem / rel_path).resolve()
    if mem not in target.parents and target != mem:
        raise ValueError("path escapes memory store: %s" % rel_path)
    return target.read_text()


def _run_script(repo_root: Path, scripts: Optional[Path], name: str, *args: str):
    if not scripts:
        return None
    script = Path(scripts) / name
    if not script.is_file():
        return None
    cmd = ["python3", str(script), str(_mem(repo_root)), *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60)


def stale(repo_root: Path, scripts: Optional[Path]) -> Optional[str]:
    p = _run_script(repo_root, scripts, "memory-index.py", "--stale")
    return None if p is None else (p.stdout or "")


def lint(repo_root: Path, scripts: Optional[Path]) -> Optional[Dict[str, Any]]:
    p = _run_script(repo_root, scripts, "memory-lint.py")
    if p is None:
        return None
    return {"ok": p.returncode == 0, "output": (p.stdout or "") + (p.stderr or "")}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.devvenv/bin/pytest studio/tests/test_memory_view.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit (only after the user approves this task's diff)**

```bash
git add studio/memory_view.py studio/tests/test_memory_view.py
git commit -m "feat(studio): memory store viewer with optional stale/lint"
```

---

### Task 5: HTTP server (`studio/server.py`)

Wire the four modules behind a threaded stdlib HTTP server: JSON endpoints, an
SSE stream for run output, static file serving, and `main()`.

**Files:**
- Create: `studio/server.py`
- Test: `studio/tests/test_server.py`

**Interfaces:**
- Consumes: `config` (Task 1), `rig` (Task 2), `runner.RunManager` (Task 3), `memory_view` (Task 4).
- Produces:
  - `make_server(repo_root: Path, memory_scripts: Optional[Path]=None, port: int=7332) -> http.server.ThreadingHTTPServer`.
  - Routes: `GET /api/config`, `GET /api/rig`, `GET /api/tests`, `POST /api/run` (body `{"target","env"}` → `{"run_id"}`), `GET /api/run/stream?id=` (SSE), `GET /api/memory`, `GET /api/memory/note?path=`, `GET /api/memory/stale`, `GET /api/memory/lint`, `GET /` and `GET /static/*`.
  - `main(argv=None)` — flags `--repo`, `--memory-scripts`, `--port`, `--open`.

- [ ] **Step 1: Write the failing tests**

```python
# studio/tests/test_server.py
import json
import textwrap
import urllib.request
from pathlib import Path
from threading import Thread

import pytest

from studio.server import make_server


@pytest.fixture
def live_server(tmp_path):
    cfgdir = tmp_path / ".agentqa"
    cfgdir.mkdir()
    (cfgdir / "config.yml").write_text(textwrap.dedent("""\
        platform: ios
        bundle_id: com.acme.app
        test_dir: AutomationTests
        build:
          policy: human
        reset_app_data: always
        appium:
          port: 4723
    """))
    (tmp_path / ".agentqa" / "memory" / "flows").mkdir(parents=True)
    (tmp_path / ".agentqa" / "memory" / "flows" / "login.md").write_text("# login\n")
    srv = make_server(tmp_path, memory_scripts=None, port=0)
    Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    yield "http://127.0.0.1:%d" % port
    srv.shutdown()


def _get(base, path):
    with urllib.request.urlopen(base + path, timeout=5) as r:
        return r.status, r.read().decode()


def test_config_endpoint(live_server):
    status, body = _get(live_server, "/api/config")
    assert status == 200
    data = json.loads(body)
    assert data["app_id"] == "com.acme.app"
    assert data["build_policy"] == "human"


def test_memory_endpoint_lists_flow(live_server):
    status, body = _get(live_server, "/api/memory")
    assert status == 200
    assert "login" in json.loads(body)["flows"]


def test_index_served(live_server):
    status, body = _get(live_server, "/")
    assert status == 200
    assert "AgentQA Studio" in body


def test_unknown_route_404(live_server):
    with pytest.raises(urllib.error.HTTPError) as exc:
        _get(live_server, "/api/nope")
    assert exc.value.code == 404
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.devvenv/bin/pytest studio/tests/test_server.py -v`
Expected: FAIL — `ImportError: cannot import name 'make_server' from 'studio.server'`

- [ ] **Step 3: Write the minimal implementation**

```python
# studio/server.py
"""AgentQA Studio daemon: stdlib HTTP + SSE over the four studio modules."""
import argparse
import json
import mimetypes
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse

from studio import config as cfgmod
from studio import memory_view, rig, runner

STATIC = Path(__file__).parent / "static"


def make_server(repo_root: Path, memory_scripts: Optional[Path] = None,
                port: int = 7332) -> ThreadingHTTPServer:
    repo_root = Path(repo_root)
    run_mgr = runner.RunManager()

    def summary():
        return cfgmod.config_summary(cfgmod.load_config(repo_root))

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # quiet
            pass

        def _json(self, obj, code=200):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _static(self, rel):
            path = (STATIC / rel).resolve()
            if STATIC.resolve() not in path.parents or not path.is_file():
                return self._json({"error": "not found"}, 404)
            ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            u = urlparse(self.path)
            q = parse_qs(u.query)
            try:
                if u.path == "/":
                    return self._static("index.html")
                if u.path.startswith("/static/"):
                    return self._static(u.path[len("/static/"):])
                if u.path == "/api/config":
                    return self._json(summary())
                if u.path == "/api/rig":
                    return self._json(rig.check_rig(summary(), repo_root))
                if u.path == "/api/tests":
                    s = summary()
                    return self._json({
                        "tests": runner.list_tests(repo_root, s["test_dir"]),
                        "artifacts": runner.find_artifacts(repo_root, s["test_dir"]),
                    })
                if u.path == "/api/memory":
                    return self._json(memory_view.list_notes(repo_root))
                if u.path == "/api/memory/note":
                    rel = (q.get("path") or [""])[0]
                    return self._json({"content": memory_view.read_note(repo_root, rel)})
                if u.path == "/api/memory/stale":
                    return self._json({"stale": memory_view.stale(repo_root, memory_scripts)})
                if u.path == "/api/memory/lint":
                    return self._json({"lint": memory_view.lint(repo_root, memory_scripts)})
                if u.path == "/api/run/stream":
                    return self._sse(q.get("id", [""])[0])
                return self._json({"error": "not found"}, 404)
            except FileNotFoundError as e:
                return self._json({"error": "config missing: %s" % e}, 500)
            except ValueError as e:
                return self._json({"error": str(e)}, 400)

        def do_POST(self):
            u = urlparse(self.path)
            if u.path == "/api/run":
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length) or b"{}")
                s = summary()
                rid = run_mgr.start(
                    repo_root, s["test_dir"],
                    payload.get("target", "all"), payload.get("env", {}),
                )
                return self._json({"run_id": rid})
            return self._json({"error": "not found"}, 404)

        def _sse(self, run_id):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            try:
                for line in run_mgr.lines(run_id):
                    self.wfile.write(("data: %s\n\n" % line).encode())
                    self.wfile.flush()
            except (BrokenPipeError, KeyError):
                return

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="agentqa-studio")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--memory-scripts", default=None)
    ap.add_argument("--port", type=int, default=7332)
    ap.add_argument("--open", action="store_true")
    args = ap.parse_args(argv)
    scripts = Path(args.memory_scripts) if args.memory_scripts else None
    srv = make_server(Path(args.repo).resolve(), scripts, args.port)
    url = "http://127.0.0.1:%d/" % srv.server_address[1]
    print("AgentQA Studio on %s  (Ctrl-C to stop)" % url)
    if args.open:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.devvenv/bin/pytest studio/tests/test_server.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit (only after the user approves this task's diff)**

```bash
git add studio/server.py studio/tests/test_server.py
git commit -m "feat(studio): stdlib HTTP + SSE server wiring the studio modules"
```

---

### Task 6: Frontend single-page UI (`studio/static/*`)

A minimal vanilla-JS SPA with the three M1 panels: Status bar, Test runner (with
live SSE output), and Memory browser. No framework, no build. The server test
from Task 5 already asserts `index.html` contains "AgentQA Studio"; here we add a
smoke test that the JS/CSS assets are served, then build the UI.

**Files:**
- Create: `studio/static/index.html`
- Create: `studio/static/app.js`
- Create: `studio/static/style.css`
- Test: `studio/tests/test_server.py` (append one asset-serving test)

- [ ] **Step 1: Add a failing asset test**

Append to `studio/tests/test_server.py`:

```python
def test_static_assets_served(live_server):
    for asset, needle in [("/static/app.js", "fetchJSON"), ("/static/style.css", "--bg")]:
        status, body = _get(live_server, asset)
        assert status == 200, asset
        assert needle in body, asset
```

- [ ] **Step 2: Run to verify it fails**

Run: `.devvenv/bin/pytest studio/tests/test_server.py::test_static_assets_served -v`
Expected: FAIL — 404 (assets don't exist yet)

- [ ] **Step 3: Create `index.html`**

```html
<!doctype html>
<meta charset="utf-8">
<title>AgentQA Studio</title>
<link rel="stylesheet" href="/static/style.css">
<header>
  <h1>AgentQA Studio</h1>
  <div id="config" class="muted">loading config…</div>
</header>
<main>
  <section id="rig-panel">
    <h2>Rig <button data-refresh="rig">↻</button></h2>
    <div id="rig" class="dots">checking…</div>
  </section>
  <section id="runner-panel">
    <h2>Tests</h2>
    <div id="tests"></div>
    <pre id="run-output" class="output"></pre>
  </section>
  <section id="memory-panel">
    <h2>Memory <button data-refresh="memory">↻</button></h2>
    <div id="memory"></div>
    <pre id="note-view" class="output"></pre>
  </section>
</main>
<script src="/static/app.js"></script>
```

- [ ] **Step 4: Create `app.js`**

```javascript
// studio/static/app.js — vanilla, no build. Renders the three M1 panels.
async function fetchJSON(path, opts) {
  const r = await fetch(path, opts);
  return r.json();
}

function el(html) {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}

async function loadConfig() {
  const c = await fetchJSON("/api/config");
  document.getElementById("config").textContent =
    `${c.platform} · ${c.app_id} · build:${c.build_policy} · appium:${c.appium_port}`;
}

async function loadRig() {
  const r = await fetchJSON("/api/rig");
  const box = document.getElementById("rig");
  box.innerHTML = "";
  const labels = { simulator: "Simulator", app_installed: "App", appium: "Appium", codegraph: "CodeGraph" };
  for (const key of Object.keys(labels)) {
    const ok = r[key];
    box.appendChild(el(`<span class="dot ${ok ? "ok" : "bad"}">${ok ? "●" : "○"} ${labels[key]}</span>`));
  }
}

async function loadTests() {
  const data = await fetchJSON("/api/tests");
  const box = document.getElementById("tests");
  box.innerHTML = "";
  box.appendChild(el(`<button id="run-all">Run all</button>`));
  document.getElementById("run-all").onclick = () => runTests("all");
  for (const t of data.tests) {
    const row = el(`<div class="test-row"><span>${t}</span></div>`);
    const btn = el(`<button>Run</button>`);
    btn.onclick = () => runTests(t);
    row.appendChild(btn);
    box.appendChild(row);
  }
  if (data.artifacts.length) {
    box.appendChild(el(`<div class="muted">Last failures: ${data.artifacts.map(a => a.name).join(", ")}</div>`));
  }
}

async function runTests(target) {
  const out = document.getElementById("run-output");
  out.textContent = `$ pytest ${target}\n`;
  const { run_id } = await fetchJSON("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target, env: {} }),
  });
  const es = new EventSource(`/api/run/stream?id=${run_id}`);
  es.onmessage = (e) => {
    if (e.data.startsWith("__END__:")) {
      out.textContent += `\n[exit ${e.data.split(":")[1]}]\n`;
      es.close();
      loadTests();
      return;
    }
    out.textContent += e.data + "\n";
    out.scrollTop = out.scrollHeight;
  };
}

async function loadMemory() {
  const m = await fetchJSON("/api/memory");
  const box = document.getElementById("memory");
  box.innerHTML = "";
  for (const kind of ["flows", "screens", "failures"]) {
    const group = el(`<div class="mem-group"><strong>${kind}</strong></div>`);
    for (const name of m[kind]) {
      const a = el(`<a href="#">${name}</a>`);
      a.onclick = async (ev) => {
        ev.preventDefault();
        const note = await fetchJSON(`/api/memory/note?path=${kind}/${name}.md`);
        document.getElementById("note-view").textContent = note.content;
      };
      group.appendChild(a);
    }
    box.appendChild(group);
  }
}

document.querySelectorAll("[data-refresh]").forEach((b) => {
  b.onclick = () => ({ rig: loadRig, memory: loadMemory }[b.dataset.refresh]());
});

loadConfig();
loadRig();
loadTests();
loadMemory();
```

- [ ] **Step 5: Create `style.css`**

```css
/* studio/static/style.css — minimal, light/dark aware */
:root { --bg: #fff; --fg: #1a1a1a; --muted: #777; --line: #e2e2e2; --ok: #1a7f37; --bad: #b00; --panel: #f7f7f7; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #14161a; --fg: #e6e6e6; --muted: #999; --line: #2a2e35; --ok: #3fb950; --bad: #f85149; --panel: #1b1e24; }
}
* { box-sizing: border-box; }
body { margin: 0; font: 14px/1.5 system-ui, sans-serif; background: var(--bg); color: var(--fg); }
header { padding: 12px 20px; border-bottom: 1px solid var(--line); }
h1 { margin: 0; font-size: 18px; }
h2 { font-size: 14px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }
main { display: grid; gap: 16px; padding: 20px; grid-template-columns: 1fr 1fr; }
section { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }
#runner-panel { grid-column: 1 / -1; }
.muted { color: var(--muted); }
.dots { display: flex; gap: 14px; flex-wrap: wrap; }
.dot.ok { color: var(--ok); } .dot.bad { color: var(--bad); }
button { font: inherit; padding: 3px 10px; border: 1px solid var(--line); border-radius: 6px; background: var(--bg); color: var(--fg); cursor: pointer; }
.test-row { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; border-bottom: 1px solid var(--line); }
.output { background: #0c0d10; color: #d6d6d6; padding: 10px; border-radius: 6px; max-height: 320px; overflow: auto; white-space: pre-wrap; }
.mem-group { margin-bottom: 8px; } .mem-group a { display: inline-block; margin: 0 8px 4px 0; }
```

- [ ] **Step 6: Run the full server test file to verify all pass**

Run: `.devvenv/bin/pytest studio/tests/test_server.py -v`
Expected: PASS (all, including `test_static_assets_served`)

- [ ] **Step 7: Manual smoke check**

Run: `.devvenv/bin/python -m studio.server --repo <a repo with .agentqa/> --port 7332 --open`
Expected: browser opens; config line, rig dots, test list, and memory groups render; clicking "Run all" streams output into the black panel.

- [ ] **Step 8: Commit (only after the user approves this task's diff)**

```bash
git add studio/static/index.html studio/static/app.js studio/static/style.css studio/tests/test_server.py
git commit -m "feat(studio): vanilla-JS UI — rig, runner (SSE), memory panels"
```

---

### Task 7: Launcher + PATH install (`bin/agentqa-studio`)

A shell launcher that resolves the app-repo root and the installed write-test
scripts dir, then execs the server. Make it discoverable on `PATH`.

**Files:**
- Create: `bin/agentqa-studio`
- Test: `studio/tests/test_launcher.py`

- [ ] **Step 1: Write a failing test for repo-root resolution**

```python
# studio/tests/test_launcher.py
import subprocess
from pathlib import Path

LAUNCHER = Path(__file__).resolve().parents[2] / "bin" / "agentqa-studio"


def test_launcher_prints_resolved_repo(tmp_path):
    (tmp_path / ".agentqa").mkdir()
    (tmp_path / ".agentqa" / "config.yml").write_text("platform: ios\n")
    # --dry-run resolves paths and prints the server command without starting it
    out = subprocess.run(
        [str(LAUNCHER), "--dry-run"], cwd=tmp_path,
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    assert "server.py" in out.stdout
    assert str(tmp_path) in out.stdout
```

- [ ] **Step 2: Run to verify it fails**

Run: `.devvenv/bin/pytest studio/tests/test_launcher.py -v`
Expected: FAIL — launcher file does not exist / not executable

- [ ] **Step 3: Write the launcher**

```bash
#!/usr/bin/env bash
# agentqa-studio — launch the AgentQA Studio dashboard against the current app repo.
set -euo pipefail

# Resolve this script's real location (studio/ lives one level up from bin/).
SELF="$(cd "$(dirname "$0")" && pwd)"
STUDIO_ROOT="$(cd "$SELF/.." && pwd)"
SERVER="$STUDIO_ROOT/studio/server.py"

# App repo = nearest git toplevel, else the current directory.
REPO="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Locate the installed write-test scripts for stale/lint (best effort).
MEM_SCRIPTS=""
for cand in \
  "$STUDIO_ROOT/skills/agentqa-write-test/scripts" \
  "$HOME/.claude/skills/agentqa-write-test/scripts" \
  "$REPO/.claude/skills/agentqa-write-test/scripts"; do
  if [ -f "$cand/memory-index.py" ]; then MEM_SCRIPTS="$cand"; break; fi
done

PY="$(command -v python3)"
ARGS=(--repo "$REPO" --port "${AGENTQA_STUDIO_PORT:-7332}" --open)
[ -n "$MEM_SCRIPTS" ] && ARGS+=(--memory-scripts "$MEM_SCRIPTS")

if [ "${1:-}" = "--dry-run" ]; then
  echo "$PY $SERVER ${ARGS[*]}"
  exit 0
fi

cd "$STUDIO_ROOT"          # so `python3 -m`-style `studio` package import resolves
exec "$PY" -c "import sys; sys.path.insert(0, '$STUDIO_ROOT'); from studio.server import main; main()" "${ARGS[@]}"
```

- [ ] **Step 4: Make it executable and run the test**

```bash
chmod +x bin/agentqa-studio
.devvenv/bin/pytest studio/tests/test_launcher.py -v
```
Expected: PASS (1 passed)

- [ ] **Step 5: Document PATH install in the launcher header comment + verify**

Add a symlink for discoverability (idempotent), then confirm:

```bash
mkdir -p "$HOME/.local/bin"
ln -sf "$(pwd)/bin/agentqa-studio" "$HOME/.local/bin/agentqa-studio"
command -v agentqa-studio   # should print the ~/.local/bin path if it's on PATH
```
Expected: prints the symlink path. If nothing prints, `~/.local/bin` isn't on
`PATH` — tell the user to add it; do not edit their shell profile without asking.

- [ ] **Step 6: Run the whole studio test suite**

Run: `.devvenv/bin/pytest studio/tests -v`
Expected: PASS (all tasks' tests green)

- [ ] **Step 7: Commit (only after the user approves this task's diff)**

```bash
git add bin/agentqa-studio studio/tests/test_launcher.py
git commit -m "feat(studio): agentqa-studio launcher + PATH install"
```

---

## Self-Review

**Spec coverage (M1 scope only):**
- Daemon (stdlib http.server + vanilla JS, no framework/build) → Tasks 5, 6. ✅
- Reads `.agentqa/config.yml` → Task 1. ✅
- Status bar (sim/app/appium/codegraph + config summary) → Tasks 2, 6. ✅
- Test runner (run suite/file, streamed output, failure artifact) → Tasks 3, 6. ✅
- Memory browser (flows/screens/failures, `--stale`, `lint`, read-only) → Tasks 4, 6. ✅
- Credential values never stored (names only, per-run passthrough) → Task 3 env passthrough + Task 1 `cred_env` names; UI wiring of a credential prompt is deferred to M2 when a real run needs it (M1 runs pass `env: {}`). ✅ (noted limitation)
- Command name / "type it and the dashboard appears" → Task 7. ✅
- **Out of M1 by design:** mailbox, connector skill, agent-conversation panel, session inspector → **M2 plan.**

**Placeholder scan:** No TBD/TODO; every code step contains complete code. ✅

**Type consistency:** `config_summary` keys (`app_id`, `test_dir`, `appium_port`,
`build_policy`, `cred_env`) are produced in Task 1 and consumed unchanged in
Tasks 2, 3, 5. `RunManager.start/lines/status` signatures match between Task 3
definition and Task 5 usage. `memory_view.list_notes/read_note/stale/lint`
signatures match between Task 4 and Task 5. Endpoint paths in Task 5 match the
`fetch` calls in Task 6. ✅

## What comes after M1

**M2 — Agent bridge (separate plan, written once M1 is green):** the
`.agentqa/studio/` mailbox (`inbox.jsonl`/`outbox.jsonl`/`state.json`, gitignored),
the `/agentqa-studio` connector skill **created via the `skill-creator` skill**,
the agent-conversation panel, and the three checkpoint cards (clarify / build /
review). Deferring it keeps M1 shippable and lets the bridge be designed against a
real, running server.
