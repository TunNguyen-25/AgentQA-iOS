import importlib.util
import sys
from datetime import date
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "memory_index", Path(__file__).resolve().parent.parent / "scripts" / "memory-index.py"
)
memory_index = importlib.util.module_from_spec(_spec)
sys.modules["memory_index"] = memory_index
_spec.loader.exec_module(memory_index)


def _note(dir_, name, front, body=""):
    dir_.mkdir(parents=True, exist_ok=True)
    (dir_ / name).write_text(f"---\n{front}\n---\n{body}", encoding="utf-8")


def test_build_index_groups_and_is_idempotent(tmp_path):
    mem = tmp_path / "memory"
    _note(mem / "flows", "login.md",
          "title: Login flow\ntype: flow\nsummary: OAuth username → HomeView id")
    _note(mem / "screens", "home.md",
          "title: Home screen\ntype: screen\nsummary: main tab, native",
          "## Observations\n- [identifier] home_item → Cell.swift; verified-in-hierarchy 2026-07-13 #home\n")
    _note(mem / "failures", "transient.md",
          "title: Transient dialog\ntype: failure\nsummary: dismiss \"Đóng\"")

    today = date(2026, 7, 13)
    idx = memory_index.build_index(mem, today=today)
    assert "## Flows" in idx and "Login flow" in idx and "OAuth username" in idx
    assert "## Screens" in idx and "home_item✓" in idx
    assert "## Failures" in idx and "dismiss" in idx
    assert memory_index.build_index(mem, today=today) == idx   # deterministic / idempotent


def test_stale_identifier_marked(tmp_path):
    mem = tmp_path / "memory"
    _note(mem / "screens", "old.md",
          "title: Old\ntype: screen\nsummary: x",
          "## Observations\n- [identifier] old_id → F.swift; verified-in-hierarchy 2026-06-01 #s\n")
    idx = memory_index.build_index(mem, today=date(2026, 7, 22))  # 51 days old
    assert "old_id✓" in idx
    assert "⚠stale" in idx


def test_fresh_identifier_shows_age_without_marker(tmp_path):
    mem = tmp_path / "memory"
    _note(mem / "screens", "new.md",
          "title: New\ntype: screen\nsummary: x",
          "## Observations\n- [identifier] new_id → F.swift; verified-in-hierarchy 2026-07-20 #s\n")
    idx = memory_index.build_index(mem, today=date(2026, 7, 22))  # 2 days old
    assert "new_id✓ 2d" in idx
    assert "⚠stale" not in idx


def test_unverified_identifier_not_marked(tmp_path):
    mem = tmp_path / "memory"
    _note(mem / "screens", "s.md",
          "title: S\ntype: screen\nsummary: x",
          "## Observations\n- [identifier] foo → F.swift; added-unverified 2026-07-13 #s\n")
    idx = memory_index.build_index(mem)
    assert "foo" not in idx
    assert "foo✓" not in idx
