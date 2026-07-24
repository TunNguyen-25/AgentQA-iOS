import importlib.util
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
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


# --- scoped recall ----------------------------------------------------------

def _two_flow_store(tmp_path):
    mem = tmp_path / "memory"
    _note(mem / "flows", "login.md", "title: Login flow\ntype: flow\nsummary: welcome → home")
    _note(mem / "flows", "checkout.md", "title: Checkout flow\ntype: flow\nsummary: cart → paid")
    _note(mem / "screens", "phone-entry.md",
          "title: Phone entry\ntype: screen\nsummary: native form",
          "## Observations\n- [native] native form #login\n")
    _note(mem / "screens", "cart.md",
          "title: Cart\ntype: screen\nsummary: web view",
          "## Observations\n- [web] web view #checkout\n")
    _note(mem / "failures", "wda.md",
          "title: WDA timeout\ntype: failure\nsummary: CPU load times out the session")
    return mem


def test_flow_scope_excludes_other_flows(tmp_path):
    """The whole point of scoping: an unrelated flow's screens stay out of
    context, so the store can grow without every run paying for it."""
    mem = _two_flow_store(tmp_path)
    out = memory_index.build_index(mem, flow="login")
    assert "Login flow" in out and "Phone entry" in out
    assert "Checkout flow" not in out and "Cart" not in out


def test_flow_scope_matches_by_tag_not_just_filename(tmp_path):
    """A screen note is tied to its flows by #tag — the filename usually says
    nothing about which flows traverse it."""
    mem = _two_flow_store(tmp_path)
    out = memory_index.build_index(mem, flow="login")
    assert "Phone entry" in out          # filename has no "login" in it


def test_flow_scope_keeps_all_failures(tmp_path):
    """Phantom signatures are cross-flow: one earned on checkout is exactly
    what you want when login fails the same way."""
    mem = _two_flow_store(tmp_path)
    out = memory_index.build_index(mem, flow="login")
    assert "WDA timeout" in out


def test_unknown_flow_says_unexplored(tmp_path):
    mem = _two_flow_store(tmp_path)
    out = memory_index.build_index(mem, flow="onboarding")
    assert "unexplored" in out


# --- actionable staleness ---------------------------------------------------

def test_stale_items_reports_location_and_age(tmp_path):
    mem = tmp_path / "memory"
    _note(mem / "screens", "login.md",
          "title: Login\ntype: screen\nsummary: x",
          "## Observations\n"
          "- [identifier] old_id → F.swift; verified-in-hierarchy 2026-06-01 #login\n"
          "- [identifier] new_id → F.swift; verified-in-hierarchy 2026-07-20 #login\n")
    items = memory_index.stale_items(mem, today=date(2026, 7, 22))
    assert len(items) == 1
    relpath, lineno, name, age, datestr, tags = items[0]
    assert (relpath, lineno, name, age) == ("screens/login.md", 7, "old_id", 51)
    report = memory_index.stale_report(mem, today=date(2026, 7, 22))
    assert "screens/login.md:7" in report        # pasteable straight into --target


def test_stale_threshold_is_configurable(tmp_path):
    mem = tmp_path / "memory"
    _note(mem / "screens", "login.md",
          "title: Login\ntype: screen\nsummary: x",
          "## Observations\n"
          "- [identifier] id → F.swift; verified-in-hierarchy 2026-07-20 #login\n")
    assert memory_index.stale_items(mem, today=date(2026, 7, 22), days=1)
    assert not memory_index.stale_items(mem, today=date(2026, 7, 22), days=30)


def test_clean_store_reports_nothing_stale(tmp_path):
    mem = tmp_path / "memory"
    _note(mem / "screens", "login.md", "title: Login\ntype: screen\nsummary: x")
    assert "every verification is current" in memory_index.stale_report(mem)


def test_flow_and_stale_do_not_write_the_index(tmp_path):
    """Both are read-only views; only the bare invocation rebuilds index.md."""
    mem = _two_flow_store(tmp_path)
    memory_index.main([str(mem), "--flow", "login"])
    memory_index.main([str(mem), "--stale"])
    assert not (mem / "index.md").exists()
    memory_index.main([str(mem)])
    assert (mem / "index.md").exists()
