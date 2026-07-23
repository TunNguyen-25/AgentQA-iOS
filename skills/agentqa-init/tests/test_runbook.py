import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "assets" / "scaffold"))
import runbook  # noqa: E402


def test_render_lists_steps_in_order_with_pass_outcome():
    steps = [
        {"action": "find id", "target": "login_button", "status": "ok"},
        {"action": "click", "target": "", "status": "ok"},
    ]
    md = runbook.render_runbook("test_login", steps, True, "test_login-final.png", "2026-07-13 10:00:00")
    assert "**Outcome:** PASS" in md
    assert md.index("find id") < md.index("click")   # order preserved
    assert "login_button" in md
    assert "![final](test_login-final.png)" in md


def test_render_marks_failure():
    md = runbook.render_runbook("test_x", [], False, "s.png", "t")
    assert "**Outcome:** FAIL" in md
    assert "no steps recorded" in md


def test_finalize_writes_md_and_screenshot(tmp_path):
    class FakeDriver:
        def __init__(self):
            self.shot = None
        def get_screenshot_as_file(self, p):
            self.shot = p
            Path(p).write_bytes(b"\x89PNG")
            return True
    drv = FakeDriver()
    out = tmp_path / "runbook"
    path = runbook.finalize(drv, "test_login", [{"action": "click", "target": "", "status": "ok"}], True, out)
    assert path.exists()
    assert path.suffix == ".md"
    assert "PASS" in path.read_text(encoding="utf-8")
    assert drv.shot is not None and Path(drv.shot).exists()
    assert Path(drv.shot).suffix == ".png"


def test_finalize_screenshot_raises_falls_back(tmp_path):
    class RaisingDriver:
        def get_screenshot_as_file(self, p):
            raise RuntimeError("no session")
    out = tmp_path / "runbook"
    path = runbook.finalize(RaisingDriver(), "test_x", [], False, out)
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "![final]((screenshot unavailable))" in text


def test_finalize_screenshot_returns_false_falls_back(tmp_path):
    class FailingDriver:
        def get_screenshot_as_file(self, p):
            # returns falsy WITHOUT writing the file and WITHOUT raising
            return False
    out = tmp_path / "runbook"
    path = runbook.finalize(FailingDriver(), "test_x", [], True, out)
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "![final]((screenshot unavailable))" in text
    # no .png was written since the driver returned False
    assert not list(out.glob("*.png"))
