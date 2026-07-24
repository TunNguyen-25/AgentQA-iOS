#!/usr/bin/env python3
"""Views over .agentqa/memory/. Stdlib only. Deterministic (sorted) and idempotent.

  memory-index.py <dir>                 rebuild <dir>/index.md (the full compact index)
  memory-index.py <dir> --flow login    print just this flow's slice (no write)
  memory-index.py <dir> --stale         print identifiers whose verification has aged out

`index.md` is generated, not committed: it is derived from the notes and rebuilt
in milliseconds, so keeping it in git would only buy merge conflicts on a file
nobody edits by hand. Recall rebuilds it, then reads the `--flow` slice — the
whole index grows with the store, and a run only needs the part touching its flow.
"""
import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from memory_common import (  # noqa: E402
    IDENTIFIER_RE, PERSISTENT_DIRS, STALE_DAYS, age_days, parse_front,
    parse_obs, tags_of,
)


def _id_label(name, datestr, today):
    age = age_days(datestr, today)
    if age is None:
        return f"{name}✓"
    label = f"{name}✓ {age}d"
    if age >= STALE_DAYS:
        label += " ⚠stale"
    return label


def _notes(memory_dir, kind):
    d = Path(memory_dir) / kind
    return sorted(d.glob("*.md")) if d.is_dir() else []


def _identifiers(text):
    """(name, placement, status, date, tags) for each identifier observation."""
    out = []
    for line in text.splitlines():
        parsed = parse_obs(line)
        if not parsed or parsed[0] != "identifier":
            continue
        m = IDENTIFIER_RE.match(parsed[1].strip())
        if m:
            out.append((m.group("name"), m.group("placement"), m.group("status"),
                        m.group("date"), tags_of(m.group("tags"))))
    return out


def _verified_labels(text, today):
    seen = {}
    for name, _placement, status, datestr, _tags in _identifiers(text):
        if status == "verified-in-hierarchy":
            seen[name] = datestr or seen.get(name)
    return [_id_label(n, seen[n], today) for n in sorted(seen)]


def _screen_line(path, today):
    text = path.read_text(encoding="utf-8")
    front = parse_front(text)
    labels = _verified_labels(text, today)
    ids = " ids: " + ", ".join(labels) if labels else ""
    return f"- {front.get('title', path.stem)}{ids} | {front.get('summary', '')}"


def _matches_flow(path, text, flow):
    """Does this note belong to `flow`?

    A note is in scope if it is tagged with the flow, or simply named after it.
    Matching generously is the right bias: a false positive costs one extra note
    in context, a false negative costs re-exploring a screen already in memory.
    """
    slug = flow.lower().lstrip("#")
    if slug in path.stem.lower():
        return True
    front = parse_front(text)
    if slug in front.get("title", "").lower() or slug in front.get("tags", "").lower():
        return True
    return any(slug == t.lower() for t in tags_of(text))


def build_index(memory_dir, today=None, flow=None):
    memory_dir = Path(memory_dir)
    today = today or date.today()
    if flow:
        return _build_scoped(memory_dir, today, flow)

    out = ["# Memory index (compact — detail files loaded on demand)", ""]
    out.append("## Flows")
    for p in _notes(memory_dir, "flows"):
        f = parse_front(p.read_text(encoding="utf-8"))
        out.append(f"- {f.get('title', p.stem)} → {f.get('summary', '')} | detail: flows/{p.name}")
    out.append("")

    out.append("## Screens")
    for p in _notes(memory_dir, "screens"):
        out.append(_screen_line(p, today))
    out.append("")

    out.append("## Failures")
    for p in _notes(memory_dir, "failures"):
        f = parse_front(p.read_text(encoding="utf-8"))
        out.append(f"- {f.get('title', p.stem)} → {f.get('summary', '')}")
    out.append("")

    return "\n".join(out).rstrip() + "\n"


def _build_scoped(memory_dir, today, flow):
    slug = flow.lower().lstrip("#")
    out = [f"# Memory index — flow: {slug}", ""]

    matched = 0
    out.append(f'## Flows matching "{slug}"')
    for p in _notes(memory_dir, "flows"):
        text = p.read_text(encoding="utf-8")
        if _matches_flow(p, text, slug):
            matched += 1
            f = parse_front(text)
            out.append(f"- {f.get('title', p.stem)} → {f.get('summary', '')} | detail: flows/{p.name}")
    out.append("")

    out.append(f"## Screens tagged #{slug}")
    for p in _notes(memory_dir, "screens"):
        text = p.read_text(encoding="utf-8")
        if _matches_flow(p, text, slug):
            matched += 1
            out.append(_screen_line(p, today) + f" | detail: screens/{p.name}")
    out.append("")

    # Failures stay unscoped: a phantom signature earned on checkout is exactly
    # what you want when login times out the same way.
    out.append("## Failures (all — the signature library is cross-flow)")
    for p in _notes(memory_dir, "failures"):
        f = parse_front(p.read_text(encoding="utf-8"))
        out.append(f"- {f.get('title', p.stem)} → {f.get('summary', '')}")
    out.append("")

    if not matched:
        out.append(f"_No notes for '{slug}' yet — this flow is unexplored. "
                   f"Nothing to verify-delta against; explore it from scratch._")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def stale_items(memory_dir, today=None, days=STALE_DAYS):
    """[(relpath, lineno, name, age, datestr, tags)] for aged-out verifications."""
    memory_dir = Path(memory_dir)
    today = today or date.today()
    found = []
    for kind in PERSISTENT_DIRS:
        for p in _notes(memory_dir, kind):
            for lineno, line in enumerate(
                    p.read_text(encoding="utf-8").splitlines(), 1):
                parsed = parse_obs(line)
                if not parsed or parsed[0] != "identifier":
                    continue
                m = IDENTIFIER_RE.match(parsed[1].strip())
                if not m or m.group("status") != "verified-in-hierarchy":
                    continue
                age = age_days(m.group("date"), today)
                if age is not None and age >= days:
                    found.append((str(p.relative_to(memory_dir)), lineno,
                                  m.group("name"), age, m.group("date"),
                                  m.group("tags").strip()))
    found.sort(key=lambda t: (-t[3], t[0], t[1]))
    return found


def stale_report(memory_dir, today=None, days=STALE_DAYS):
    items = stale_items(memory_dir, today, days)
    if not items:
        return f"No identifiers older than {days}d — every verification is current.\n"
    width = max(len(f"{f}:{ln}") for f, ln, *_ in items)
    out = [f"{len(items)} identifier(s) verified more than {days}d ago:", ""]
    for relpath, lineno, name, age, datestr, tags in items:
        loc = f"{relpath}:{lineno}"
        out.append(f"  {loc:<{width}}  {name}  — verified {age}d ago ({datestr}) {tags}".rstrip())
    out += [
        "",
        "These are prompts to look, not deletions: the identifier is probably still",
        "there, but nobody has checked lately. Confirm them in the live hierarchy",
        "while exploring, then refresh each one in place:",
        "",
        '  memory-write.py apply --op UPDATE --target <file:line> \\',
        '      --category identifier \\',
        '      --text "<name> → <file/symbol>; verified-in-hierarchy <today> #<flow>"',
    ]
    return "\n".join(out) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(description="Views over .agentqa/memory/.")
    p.add_argument("memory_dir", nargs="?", default=".agentqa/memory")
    p.add_argument("--flow", help="print only this flow's slice (no write)")
    p.add_argument("--stale", action="store_true",
                   help="report verified identifiers that have aged out (no write)")
    p.add_argument("--days", type=int, default=STALE_DAYS,
                   help=f"staleness threshold in days (default {STALE_DAYS})")
    args = p.parse_args(argv)
    memory_dir = Path(args.memory_dir)

    if args.stale:
        print(stale_report(memory_dir, days=args.days), end="")
        return 0
    if args.flow:
        print(build_index(memory_dir, flow=args.flow), end="")
        return 0

    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / "index.md").write_text(build_index(memory_dir), encoding="utf-8")
    print(f"wrote {memory_dir / 'index.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
