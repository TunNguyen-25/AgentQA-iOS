#!/usr/bin/env python3
"""Turn a graded run into the layout the skill-creator viewer and aggregator want.

  <arm>/run-1/grading.json   with the `summary` block aggregate_benchmark reads
  <arm>/run-1/timing.json
  <arm>/run-1/outputs/       the things a human actually wants to look at
  <arm>/eval_metadata.json   the viewer looks here (run_dir.parent)

The outputs are assembled rather than copied wholesale: a reviewer wants the
agent's own account, the memory it left behind, the app-code diff, the test it
wrote, what it asked the human, and the order it did things in — not a tarball
of the fixture.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

WS = Path(__file__).resolve().parent


def jsonl(p):
    if not p.is_file():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def tool_timeline(calls, questions):
    events = [(c["ts"], "tool", f"{c['tool']} {' '.join(str(a) for a in c.get('argv', []))}")
              for c in calls]
    events += [(q["ts"], "ask", q["question"]) for q in questions]
    events.sort(key=lambda e: e[0])
    if not events:
        return "_(no tool calls logged)_\n"
    t0 = events[0][0]
    lines = ["# Tool timeline", "",
             "Every shimmed command and every question, in order. `+Ns` is seconds "
             "from the run's first logged action.", "",
             "| +s | kind | call |", "|---:|---|---|"]
    for ts, kind, text in events:
        text = text.replace("|", "\\|").replace("\n", " ")
        if len(text) > 160:
            text = text[:157] + "..."
        lines.append(f"| {ts - t0:.0f} | {kind} | `{text}`" if kind == "tool"
                     else f"| {ts - t0:.0f} | {kind} | {text}")
    return "\n".join(lines) + "\n"


def questions_md(questions):
    if not questions:
        return "# Questions asked\n\n_(the run asked the human nothing)_\n"
    out = ["# Questions asked", "",
           f"{len(questions)} question(s) put to the human reviewer, verbatim.", ""]
    for i, q in enumerate(questions, 1):
        out += [f"### {i}. {q['question']}", "", f"> {q['answer']}", ""]
    return "\n".join(out)


def memory_tree(repo):
    mem = repo / ".agentqa" / "memory"
    out = ["# Memory left behind", ""]
    if not mem.is_dir():
        return "\n".join(out + ["_(no .agentqa/memory)_"])
    working = []
    for name in (".run-checkpoint.md", ".session-requirement.md"):
        if (mem / name).exists():
            working.append(name)
    out.append("**Working-layer files still present:** "
               + (", ".join(f"`{w}`" for w in working) if working
                  else "_none — both cleaned up_"))
    out.append("")
    files = sorted(p for p in mem.rglob("*.md"))
    for p in files:
        rel = p.relative_to(mem)
        out += [f"## `{rel}`", "", "```markdown",
                p.read_text(encoding="utf-8", errors="replace").rstrip(), "```", ""]
    if not files:
        out.append("_(no notes)_")
    return "\n".join(out)


def code_diff(repo):
    d = subprocess.run(["git", "-C", str(repo), "diff"],
                       capture_output=True, text=True).stdout
    untracked = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "--others", "--exclude-standard"],
        capture_output=True, text=True).stdout.strip()
    numstat = subprocess.run(["git", "-C", str(repo), "diff", "--numstat"],
                             capture_output=True, text=True).stdout.strip()
    parts = ["# Repo changes", "", "## git diff --numstat", "",
             "```", numstat or "(no tracked changes)", "```", "",
             "## New files", "", "```", untracked or "(none)", "```", "",
             "## Full diff", "", "```diff", d.rstrip() or "(empty)", "```"]
    return "\n".join(parts)


def tests_md(repo):
    at = repo / "AutomationTests"
    out = ["# Tests and page objects written", ""]
    files = [p for p in sorted(at.rglob("*.py"))
             if ".venv" not in str(p) and "__pycache__" not in str(p)
             and p.name != "__init__.py" and p.name != "conftest.py"]
    if not files:
        return "\n".join(out + ["_(none written)_"])
    for p in files:
        out += [f"## `{p.relative_to(repo)}`", "", "```python",
                p.read_text(encoding="utf-8", errors="replace").rstrip(), "```", ""]
    return "\n".join(out)


def publish(arm_dir, timing=None):
    arm = Path(arm_dir)
    repo = arm / "run" / "repo"
    state = arm / "run" / "state"
    run1 = arm / "run-1"
    outs = run1 / "outputs"
    outs.mkdir(parents=True, exist_ok=True)

    grading_src = arm / "grading.json"
    g = json.loads(grading_src.read_text(encoding="utf-8")) if grading_src.is_file() else {}
    exps = g.get("expectations", [])
    passed = sum(1 for e in exps if e.get("passed"))
    g["summary"] = {"passed": passed, "failed": len(exps) - passed,
                    "total": len(exps),
                    "pass_rate": round(passed / len(exps), 4) if exps else 0.0}
    (run1 / "grading.json").write_text(json.dumps(g, indent=2, ensure_ascii=False),
                                       encoding="utf-8")

    if timing:
        (run1 / "timing.json").write_text(json.dumps(timing, indent=2), encoding="utf-8")

    meta = arm.parent / "eval_metadata.json"
    if meta.is_file():
        shutil.copy(meta, arm / "eval_metadata.json")

    calls, questions = jsonl(state / "calls.jsonl"), jsonl(state / "questions.jsonl")
    summary = arm / "run" / "SUMMARY.md"
    (outs / "1-agent-summary.md").write_text(
        summary.read_text(encoding="utf-8", errors="replace") if summary.is_file()
        else "# Agent summary\n\n_(the run wrote no SUMMARY.md)_\n", encoding="utf-8")
    (outs / "2-questions-asked.md").write_text(questions_md(questions), encoding="utf-8")
    (outs / "3-tool-timeline.md").write_text(tool_timeline(calls, questions),
                                             encoding="utf-8")
    (outs / "4-memory-left-behind.md").write_text(memory_tree(repo), encoding="utf-8")
    (outs / "5-tests-written.md").write_text(tests_md(repo), encoding="utf-8")
    (outs / "6-repo-changes.md").write_text(code_diff(repo), encoding="utf-8")
    print(f"published {arm.parent.name}/{arm.name}: "
          f"{g['summary']['passed']}/{g['summary']['total']}")


if __name__ == "__main__":
    publish(sys.argv[1],
            json.loads(sys.argv[2]) if len(sys.argv) > 2 else None)
