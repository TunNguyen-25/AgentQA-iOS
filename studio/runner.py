"""List and run the pytest suite, streaming output; find failure artifacts."""
import os
import subprocess
import threading
import uuid
from pathlib import Path
from queue import Empty, Queue
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
        self._final: Dict[str, str] = {}      # run_id -> stored end marker
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
            end = "__END__:%d" % rc
            self._final[run_id] = end
            self._status[run_id] = "done"
            q.put(end)
        except Exception as exc:  # noqa: BLE001 - surface any launch failure to the UI
            self._final[run_id] = "__END__:1"
            self._status[run_id] = "error"
            q.put("studio: failed to run: %s" % exc)
            q.put("__END__:1")

    def lines(self, run_id: str) -> Iterator[str]:
        q = self._queues.get(run_id)
        if q is None:
            yield "__END__:unknown"
            return
        while True:
            if q.empty() and self._status.get(run_id) != "running":
                # Producer finished and the queue is drained. Replay the stored
                # end marker so a second consumer (e.g. a browser reconnect)
                # returns promptly instead of blocking forever on an empty queue.
                yield self._final.get(run_id, "__END__:0")
                return
            try:
                item = q.get(timeout=0.5)
            except Empty:
                continue
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
