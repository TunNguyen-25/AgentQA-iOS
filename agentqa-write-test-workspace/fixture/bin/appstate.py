"""Shared state machine for the agentqa-write-test eval fixture.

Every shim (agent-device, xcrun, page-source, pytest) imports this module so they
all agree on what the "live app" currently looks like. State lives in
$AGENTQA_EVAL_STATE/state.json; every shim call is appended to calls.jsonl so
grading can replay exactly what the agent did and in what order.

The mock app is a cut-down MyTV: a notification permission prompt on first
launch, an intro screen, a login form with a terms checkbox and a web terms
sheet, and a home tab bar.
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

STATE_DIR = Path(os.environ.get("AGENTQA_EVAL_STATE", "/tmp/agentqa-eval-state"))
REPO = Path(os.environ.get("AGENTQA_EVAL_REPO", Path.cwd()))
SOURCES = REPO / "mytvb2c" / "Sources"

# --------------------------------------------------------------------------
# call log
# --------------------------------------------------------------------------


def log(tool, argv, extra=None):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    rec = {"ts": time.time(), "tool": tool, "argv": argv}
    if extra:
        rec.update(extra)
    with (STATE_DIR / "calls.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------
# persisted state
# --------------------------------------------------------------------------

DEFAULT_STATE = {
    "screen": "closed",
    "permission_seen": False,
    "opened": False,
    "username": "",
    "password": "",
    "terms_checked": False,
}


def load() -> dict:
    f = STATE_DIR / "state.json"
    if not f.is_file():
        return dict(DEFAULT_STATE)
    try:
        s = dict(DEFAULT_STATE)
        s.update(json.loads(f.read_text(encoding="utf-8")))
        return s
    except Exception:
        return dict(DEFAULT_STATE)


def save(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / "state.json").write_text(
        json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def reset() -> None:
    save(dict(DEFAULT_STATE))


# --------------------------------------------------------------------------
# accessibility identifiers are resolved from the Swift sources
# --------------------------------------------------------------------------
#
# The mock app's "build" is implicit: whatever accessibilityIdentifier a Swift
# file assigns to a symbol is what shows up in the live hierarchy. This is what
# makes "add identifier -> verify in hierarchy" a real loop instead of a mime.

_ID_RE = re.compile(
    r"(?P<sym>\w+)\s*\.\s*accessibilityIdentifier\s*=\s*\"(?P<id>[^\"]+)\""
)
_TYPE_RE = re.compile(r"^\s*(?:final\s+|public\s+|private\s+)*"
                      r"(?:class|struct|extension|enum)\s+(\w+)", re.M)


def swift_identifiers() -> dict:
    """'Type.symbol' -> accessibility identifier, from the Swift sources.

    Scoped by enclosing type on purpose: `btnLogin` exists on both
    IntroductionContentViewController and LoginView, and a flat symbol map
    silently loses one of them.
    """
    found = {}
    if not SOURCES.is_dir():
        return found
    for path in SOURCES.rglob("*.swift"):
        text = path.read_text(encoding="utf-8", errors="replace")
        types = [(m.start(), m.group(1)) for m in _TYPE_RE.finditer(text)]
        for m in _ID_RE.finditer(text):
            enclosing = ""
            for pos, name in types:
                if pos < m.start():
                    enclosing = name
                else:
                    break
            found[f"{enclosing}.{m.group('sym')}"] = m.group("id")
    return found


def all_live_ids() -> set:
    return set(swift_identifiers().values())


# --------------------------------------------------------------------------
# the screen graph
# --------------------------------------------------------------------------
#
# Each element: (ref, role, label, swift_symbol, extra)
# swift_symbol is None for system UI (outside the app's own hierarchy) and for
# elements the app never labels.

SCREENS = {
    "sys_permission": {
        "kind": "system",
        "title": "Notifications permission (SpringBoard)",
        "elements": [
            ("@e1", "staticText", '"MyTV" Would Like to Send You Notifications', None, ""),
            ("@e2", "staticText",
             "Notifications may include alerts, sounds and icon badges.", None, ""),
            ("@e3", "button", "Don't Allow", None, "enabled hittable"),
            ("@e4", "button", "Allow", None, "enabled hittable"),
        ],
    },
    "intro": {
        "kind": "native",
        "title": "IntroductionContentViewController",
        "elements": [
            ("@e5", "staticText", "Đăng nhập MyTV", None, ""),
            ("@e6", "staticText", "Xem phim, truyền hình mọi lúc mọi nơi", None, ""),
            ("@e7", "button", "Đăng nhập ngay", "IntroductionContentViewController.btnLogin", "enabled hittable"),
            ("@e8", "button", "Xem miễn phí", "IntroductionContentViewController.btnFree", "enabled hittable"),
        ],
    },
    "login": {
        "kind": "native",
        "title": "LoginViewController / LoginView",
        "elements": [
            ("@e9", "staticText", "Đăng nhập", None, ""),
            ("@e10", "textinput", "Tên đăng nhập", "LoginView.usernameTextField", "enabled hittable"),
            ("@e11", "textinput", "Mật khẩu", "LoginView.passwordTextField", "secure enabled hittable"),
            ("@e12", "checkbox", "Tôi đồng ý với điều khoản sử dụng",
             "LoginView.checkBoxTermImgView", "enabled hittable"),
            ("@e13", "button", "Điều khoản sử dụng", "LoginView.termsLink", "enabled hittable"),
            ("@e14", "button", "Đăng nhập", "LoginView.btnLogin", "enabled hittable"),
        ],
    },
    "login_error": {
        "kind": "native",
        "title": "LoginViewController / LoginView (error)",
        "elements": [
            ("@e9", "staticText", "Đăng nhập", None, ""),
            ("@e10", "textinput", "Tên đăng nhập", "LoginView.usernameTextField", "enabled hittable"),
            ("@e11", "textinput", "Mật khẩu", "LoginView.passwordTextField", "secure enabled hittable"),
            ("@e12", "checkbox", "Tôi đồng ý với điều khoản sử dụng",
             "LoginView.checkBoxTermImgView", "enabled hittable"),
            ("@e13", "button", "Điều khoản sử dụng", "LoginView.termsLink", "enabled hittable"),
            ("@e14", "button", "Đăng nhập", "LoginView.btnLogin", "enabled hittable"),
            ("@e15", "staticText", "Sai tên đăng nhập hoặc mật khẩu",
             "LoginView.errorLabel", ""),
        ],
    },
    "login_terms_required": {
        "kind": "native",
        "title": "LoginViewController / LoginView (terms not accepted)",
        "elements": [
            ("@e9", "staticText", "Đăng nhập", None, ""),
            ("@e10", "textinput", "Tên đăng nhập", "LoginView.usernameTextField", "enabled hittable"),
            ("@e11", "textinput", "Mật khẩu", "LoginView.passwordTextField", "secure enabled hittable"),
            ("@e12", "checkbox", "Tôi đồng ý với điều khoản sử dụng",
             "LoginView.checkBoxTermImgView", "enabled hittable"),
            ("@e13", "button", "Điều khoản sử dụng", "LoginView.termsLink", "enabled hittable"),
            ("@e14", "button", "Đăng nhập", "LoginView.btnLogin", "enabled hittable"),
            ("@e15", "staticText", "Vui lòng đồng ý với điều khoản sử dụng",
             "LoginView.errorLabel", ""),
        ],
    },
    # Deliberately sparse: this is a WKWebView sheet. snapshot sees almost
    # nothing, so the only way to understand it is `agent-device screenshot`.
    "terms_web": {
        "kind": "web",
        "title": "Terms sheet (WKWebView)",
        "elements": [
            ("@e16", "webview", "", None, ""),
            ("@e17", "button", "Xong", None, "enabled hittable"),
        ],
    },
    "home": {
        "kind": "native",
        "title": "MainTabBarController",
        "elements": [
            ("@e18", "staticText", "Xin chào", None, ""),
            ("@e19", "button", "Trang chủ", "MainTabBarController.homeTab", "enabled hittable selected"),
            ("@e20", "button", "Truyền hình", "MainTabBarController.liveTab", "enabled hittable"),
            ("@e21", "button", "Cá nhân", "MainTabBarController.profileTab", "enabled hittable"),
        ],
    },
    "guest_home": {
        "kind": "native",
        "title": "MainTabBarController (guest)",
        "elements": [
            ("@e18", "staticText", "Nội dung miễn phí", None, ""),
            ("@e19", "button", "Trang chủ", "MainTabBarController.homeTab", "enabled hittable selected"),
            ("@e21", "button", "Cá nhân", "MainTabBarController.profileTab", "enabled hittable"),
        ],
    },
    # Second entry point into the same login flow: a guest who taps the profile
    # tab is prompted to sign in. Same LoginViewController, different route.
    "guest_profile": {
        "kind": "native",
        "title": "ProfileViewController (guest)",
        "elements": [
            ("@e22", "staticText", "Bạn chưa đăng nhập", None, ""),
            ("@e23", "button", "Đăng nhập để tiếp tục",
             "ProfileViewController.btnSignIn", "enabled hittable"),
        ],
    },
}

VALID_USER = "mytv_qa"
VALID_PASS = "Qa!2026pass"


def render_snapshot(state: dict, interactive_only: bool = False) -> str:
    screen = state["screen"]
    if screen == "closed":
        return "No active session. Run `agent-device open <app>` first."
    spec = SCREENS[screen]
    ids = swift_identifiers()
    lines = [f"# {spec['title']}  [{spec['kind']}]"]
    for ref, role, label, sym, extra in spec["elements"]:
        if interactive_only and role in ("staticText",):
            continue
        parts = [ref, f"[{role}]"]
        if label:
            parts.append(f'label="{label}"')
        aid = ids.get(sym) if sym else None
        if aid:
            parts.append(f'id="{aid}"')
        if extra:
            parts.append(extra)
        lines.append("  " + " ".join(parts))
    if spec["kind"] == "web":
        lines.append(
            "  [note] web content is not exposed to the accessibility tree; "
            "use `agent-device screenshot` to read it."
        )
    if spec["kind"] == "system":
        lines.append(
            "  [note] this alert is owned by SpringBoard, not by the app under test."
        )
    return "\n".join(lines)


def match(target, state):
    """Resolve @ref, id="..", label=".." or bare text against the current screen.

    Labels are not unique — a screen heading and its submit button can both read
    "Đăng nhập". The real CLI auto-resolves deepest-node-then-smallest-area
    rather than failing, which in practice picks the control over the heading, so
    interactive roles win ties here too.
    """
    screen = state["screen"]
    if screen == "closed":
        return None
    ids = swift_identifiers()
    target = target.strip()
    m = re.match(r'^(?:id|label|text)\s*=\s*"?([^"]+)"?$', target)
    key = (m.group(1) if m else target).strip("'\"")

    exact, by_label = [], []
    for el in SCREENS[screen]["elements"]:
        ref, role, label, sym, extra = el
        aid = ids.get(sym) if sym else None
        if key in (ref, ref.lstrip("@")) or (aid and key == aid):
            exact.append(el)
        elif label and key.lower() == label.lower():
            by_label.append(el)
    if exact:
        return exact[0]
    if by_label:
        interactive = [e for e in by_label if e[1] != "staticText"]
        return (interactive or by_label)[0]
    return None


def backend_state() -> str:
    """'ok' or 'error_404' — set per-variant via a marker file."""
    f = REPO / ".agentqa" / ".eval-backend"
    if f.is_file():
        return f.read_text(encoding="utf-8").strip()
    return "ok"
