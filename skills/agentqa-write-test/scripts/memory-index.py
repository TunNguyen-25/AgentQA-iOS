#!/usr/bin/env python3
"""Rebuild .agentqa/memory/index.md from each note's frontmatter + verified
identifiers. Stdlib only. Deterministic (sorted) and idempotent."""
import re
import sys
from datetime import date
from pathlib import Path

_ID_VERIFIED = re.compile(
    r"^- \[identifier\]\s+(\S+).*verified-in-hierarchy(?:\s+(\d{4}-\d{2}-\d{2}))?", re.M)
STALE_DAYS = 30


def _age_days(datestr, today):
    try:
        return (today - date.fromisoformat(datestr)).days
    except (ValueError, TypeError):
        return None


def _id_label(name, datestr, today):
    age = _age_days(datestr, today)
    if age is None:
        return f"{name}✓"
    label = f"{name}✓ {age}d"
    if age >= STALE_DAYS:
        label += " ⚠stale"
    return label


def parse_front(text):
    front = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    front[k.strip()] = v.strip().strip('"')
    return front


def _notes(memory_dir, kind):
    d = memory_dir / kind
    return sorted(d.glob("*.md")) if d.is_dir() else []


def build_index(memory_dir, today=None):
    memory_dir = Path(memory_dir)
    today = today or date.today()
    out = ["# Memory index (compact — detail files loaded on demand)", ""]

    out.append("## Flows")
    for p in _notes(memory_dir, "flows"):
        f = parse_front(p.read_text(encoding="utf-8"))
        out.append(f"- {f.get('title', p.stem)} → {f.get('summary', '')} | detail: flows/{p.name}")
    out.append("")

    out.append("## Screens")
    for p in _notes(memory_dir, "screens"):
        text = p.read_text(encoding="utf-8")
        f = parse_front(text)
        seen = {}
        for name, datestr in _ID_VERIFIED.findall(text):
            seen[name] = datestr or seen.get(name)
        labels = [_id_label(n, seen[n], today) for n in sorted(seen)]
        id_str = " ids: " + ", ".join(labels) if labels else ""
        out.append(f"- {f.get('title', p.stem)}{id_str} | {f.get('summary', '')}")
    out.append("")

    out.append("## Failures")
    for p in _notes(memory_dir, "failures"):
        f = parse_front(p.read_text(encoding="utf-8"))
        out.append(f"- {f.get('title', p.stem)} → {f.get('summary', '')}")
    out.append("")

    return "\n".join(out).rstrip() + "\n"


def main():
    memory_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".agentqa/memory")
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / "index.md").write_text(build_index(memory_dir), encoding="utf-8")
    print(f"wrote {memory_dir / 'index.md'}")


if __name__ == "__main__":
    main()
