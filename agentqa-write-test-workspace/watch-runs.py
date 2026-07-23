#!/usr/bin/env python3
"""Poll every run's repo tree and record a file create/delete/modify timeline.

Several assertions are about *ordering*, not final state:
  - was .session-requirement.md written before the live app was driven?
  - was any .py test file created before identifiers were verified?
  - were BOTH working-layer files deleted at the end?
Final state cannot answer those — a file written at step 2 and deleted at step 9
looks identical to one that was never written. This writes fs-timeline.jsonl
next to each run's state dir.
"""
import json
import sys
import time
from pathlib import Path

IT = Path(sys.argv[1])
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0

WATCH_GLOBS = [".agentqa/memory/**/*.md", "AutomationTests/**/*.py",
               "mytvb2c/**/*.swift", ".codegraph/**/*"]
SKIP = ("/.git/", "/.venv/", "__pycache__")


def snap(repo):
    out = {}
    for g in WATCH_GLOBS:
        for p in repo.glob(g):
            s = str(p)
            if any(k in s for k in SKIP) or not p.is_file():
                continue
            try:
                st = p.stat()
                out[str(p.relative_to(repo))] = (st.st_size, int(st.st_mtime))
            except OSError:
                pass
    return out


def main():
    runs = sorted(IT.glob("*/*/run"))
    if not runs:
        print("no runs found", file=sys.stderr)
        return 1
    prev = {r: snap(r / "repo") for r in runs}
    logs = {r: (r.parent / "run" / ".." / "fs-timeline.jsonl") for r in runs}
    for r in runs:
        (r.parent / "fs-timeline.jsonl").write_text("", encoding="utf-8")
    print(f"watching {len(runs)} runs every {INTERVAL}s", flush=True)
    while True:
        time.sleep(INTERVAL)
        for r in runs:
            cur = snap(r / "repo")
            events = []
            for k in cur.keys() - prev[r].keys():
                events.append({"event": "create", "path": k})
            for k in prev[r].keys() - cur.keys():
                events.append({"event": "delete", "path": k})
            for k in cur.keys() & prev[r].keys():
                if cur[k] != prev[r][k]:
                    events.append({"event": "modify", "path": k})
            if events:
                ts = time.time()
                with (r.parent / "fs-timeline.jsonl").open("a", encoding="utf-8") as fh:
                    for e in events:
                        e["ts"] = ts
                        fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            prev[r] = cur


if __name__ == "__main__":
    sys.exit(main())
