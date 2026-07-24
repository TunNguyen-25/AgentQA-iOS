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
