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
