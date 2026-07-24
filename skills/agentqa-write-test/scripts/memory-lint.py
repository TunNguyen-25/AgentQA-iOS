#!/usr/bin/env python3
"""Validate a .agentqa/memory/ store. Stdlib only.

  memory-lint.py [<dir>] [--strict]

Catches the failures that leave a store looking healthy while answering nothing:
a note with no `summary:` renders as a blank index line, a mistyped category
drops the fact out of every query built on the schema, an identifier line that
doesn't parse is invisible to staleness reporting, and a literal credential in a
committed store is in git history from the moment it lands.

Errors exit 1; warnings report and exit 0 unless --strict. Only the persistent
store is checked — the generated index and the two session dotfiles are
deliberately out of scope, since one is rebuilt and the other is thrown away.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from memory_common import (  # noqa: E402
    CATEGORIES, EPHEMERAL_FILES, GENERATED_FILES, IDENTIFIER_RE, ID_STATUSES,
    NOTE_TYPES, OBS_RE, PERSISTENT_DIRS, PERSISTENT_FILES, iter_persistent_notes,
    parse_front, secret_findings, tags_of,
)

EXPECTED_TYPE = {"flows": "flow", "screens": "screen", "failures": "failure"}


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, where, msg):
        self.errors.append((where, msg))

    def warn(self, where, msg):
        self.warnings.append((where, msg))


def _check_frontmatter(report, memory_dir, path, text, indexed):
    where = str(path.relative_to(memory_dir))
    front = parse_front(text)
    if not front:
        report.error(where, "no YAML frontmatter — the index is assembled from it, "
                            "so this note is invisible to Recall")
        return
    if not front.get("title"):
        report.warn(where, "frontmatter missing `title:` — the index falls back "
                           "to the filename")
    if not front.get("type"):
        report.error(where, "frontmatter missing `type:`")
    # env.md never appears in the index, so a summary there buys nothing and a
    # warning about it would just be noise on a freshly scaffolded store.
    if indexed and not front.get("summary"):
        report.error(where, "frontmatter missing `summary:` — the index line for "
                            "this note will be blank")
    declared = front.get("type", "")
    if declared and declared not in NOTE_TYPES:
        report.error(where, f"unknown type `{declared}` — use one of: "
                            + ", ".join(sorted(NOTE_TYPES)))
    parent = path.parent.name
    expected = EXPECTED_TYPE.get(parent)
    if expected and declared and declared != expected:
        report.error(where, f"type `{declared}` in {parent}/ — expected `{expected}`")


def _check_observations(report, memory_dir, path, text, indexed):
    where = str(path.relative_to(memory_dir))
    tagged = 0
    total = 0
    for lineno, line in enumerate(text.splitlines(), 1):
        m = OBS_RE.match(line.rstrip("\n"))
        if not m:
            continue
        category, body = m.group(1), m.group(2)
        loc = f"{where}:{lineno}"
        if category not in CATEGORIES:
            if body.startswith("("):
                continue  # a markdown link, not an observation
            report.error(loc, f"unknown category [{category}] — use one of: "
                              + ", ".join(sorted(CATEGORIES)))
            continue
        total += 1
        if tags_of(body):
            tagged += 1
        if category == "identifier":
            _check_identifier(report, loc, body)
        for severity, msg in secret_findings(body):
            (report.error if severity == "error" else report.warn)(loc, msg)

    # env.md is global knowledge that every flow wants, so it is exempt: tags
    # are how a *flow-specific* note gets found, not a blanket requirement.
    if indexed and total and not tagged:
        report.warn(where, "no observation carries a #flow tag — scoped recall "
                           "(`--flow`) will never surface this note")


def _check_identifier(report, loc, body):
    m = IDENTIFIER_RE.match(body.strip())
    if not m:
        report.error(loc, "identifier must read `<name> → <file/symbol>; "
                          "<status> <YYYY-MM-DD> #<flow>` — this one does not "
                          "parse, so staleness reporting skips it")
        return
    if m.group("status") not in ID_STATUSES:
        report.error(loc, f"unknown identifier status `{m.group('status')}` — use "
                          + " or ".join(sorted(ID_STATUSES)))
    if not tags_of(m.group("tags")):
        report.warn(loc, f"identifier `{m.group('name')}` has no #flow tag")


def _check_layout(report, memory_dir):
    """Notes filed somewhere Recall will never look."""
    known_root = set(PERSISTENT_FILES) | set(GENERATED_FILES) | set(EPHEMERAL_FILES) | {"README.md"}
    for p in sorted(memory_dir.glob("*.md")):
        if p.name not in known_root:
            report.error(p.name, "stray note in the store root — persistent notes "
                                 "belong in " + "/, ".join(PERSISTENT_DIRS) + "/")
    for sub in sorted(d for d in memory_dir.iterdir() if d.is_dir()):
        if sub.name not in PERSISTENT_DIRS and not sub.name.startswith("."):
            report.warn(sub.name + "/", "unknown directory — Recall only reads "
                        + "/, ".join(PERSISTENT_DIRS) + "/")


def lint(memory_dir):
    memory_dir = Path(memory_dir).resolve()
    report = Report()
    if not memory_dir.is_dir():
        report.error(str(memory_dir), "memory store does not exist — run "
                                      "agentqa-init's scripts/scaffold-memory.sh")
        return report
    _check_layout(report, memory_dir)
    for path in iter_persistent_notes(memory_dir):
        text = path.read_text(encoding="utf-8")
        indexed = path.parent.name in PERSISTENT_DIRS
        _check_frontmatter(report, memory_dir, path, text, indexed)
        _check_observations(report, memory_dir, path, text, indexed)
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description="Validate a .agentqa/memory/ store.")
    p.add_argument("memory_dir", nargs="?", default=".agentqa/memory")
    p.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = p.parse_args(argv)

    report = lint(args.memory_dir)
    for where, msg in report.errors:
        print(f"ERROR {where}: {msg}")
    for where, msg in report.warnings:
        print(f"WARN  {where}: {msg}")

    if not report.errors and not report.warnings:
        print(f"memory lint: OK ({args.memory_dir})")
        return 0
    print(f"\nmemory lint: {len(report.errors)} error(s), "
          f"{len(report.warnings)} warning(s)")
    if report.errors or (args.strict and report.warnings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
