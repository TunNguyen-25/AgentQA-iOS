"""Per-run execution runbook: a markdown trace of Appium steps plus a final
screenshot on pass OR fail. Stdlib only — the pytest/selenium wiring lives in
conftest.py so this module stays unit-testable without a driver."""
from datetime import datetime
from pathlib import Path


def _fmt_step(i, step):
    mark = "✓" if step.get("status", "ok") == "ok" else "✗"
    target = step.get("target", "")
    tail = f" — `{target}`" if target else ""
    return f"{i}. {mark} {step['action']}{tail}"


def render_runbook(test_name, steps, passed, screenshot_rel, when):
    outcome = "PASS" if passed else "FAIL"
    lines = [
        f"# Runbook — {test_name}",
        "",
        f"**Outcome:** {outcome}  ",
        f"**When:** {when}",
        "",
        "## Steps",
        "",
    ]
    if steps:
        lines += [_fmt_step(i, s) for i, s in enumerate(steps, 1)]
    else:
        lines.append("_(no steps recorded)_")
    lines += ["", "## Final screenshot", "", f"![final]({screenshot_rel})", ""]
    return "\n".join(lines)


def finalize(driver, test_name, steps, passed, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    shot = out_dir / f"{test_name}-{ts}-final.png"
    try:
        ok = driver.get_screenshot_as_file(str(shot))
        shot_rel = shot.name if ok else "(screenshot unavailable)"
    except Exception:
        shot_rel = "(screenshot unavailable)"
    md = render_runbook(test_name, steps, passed, shot_rel, ts)
    path = out_dir / f"{test_name}-{ts}.md"
    path.write_text(md, encoding="utf-8")
    return path
