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
