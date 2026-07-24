import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
_spec = importlib.util.spec_from_file_location(
    "memory_lint", Path(__file__).resolve().parent.parent / "scripts" / "memory-lint.py"
)
memory_lint = importlib.util.module_from_spec(_spec)
sys.modules["memory_lint"] = memory_lint
_spec.loader.exec_module(memory_lint)


def _note(dir_, name, front, body=""):
    dir_.mkdir(parents=True, exist_ok=True)
    (dir_ / name).write_text(f"---\n{front}\n---\n{body}", encoding="utf-8")


def _good_store(tmp_path):
    mem = tmp_path / "memory"
    _note(mem / "flows", "login.md",
          "title: Login flow\ntype: flow\nsummary: welcome → home",
          "## Observations\n- [flow-step] welcome → login form #login\n")
    _note(mem / "screens", "login.md",
          "title: Login screen\ntype: screen\nsummary: native form",
          "## Observations\n"
          "- [identifier] login_phone_field → LoginVC.swift:42; verified-in-hierarchy 2026-07-20 #login\n")
    _note(mem, "env.md", "title: Env\ntype: env\ntags: [env]",
          "## Observations\n- [gotcha] never index during a run\n")
    return mem


def _messages(report):
    return [f"{w}: {m}" for w, m in report.errors + report.warnings]


def test_clean_store_passes(tmp_path):
    report = memory_lint.lint(_good_store(tmp_path))
    assert report.errors == []
    assert report.warnings == [], _messages(report)


def test_missing_summary_is_an_error_for_indexed_notes(tmp_path):
    """No summary means a blank index line — the note is in the store but
    effectively invisible to Recall."""
    mem = _good_store(tmp_path)
    _note(mem / "screens", "home.md", "title: Home\ntype: screen")
    report = memory_lint.lint(mem)
    assert any("summary" in m for _, m in report.errors)


def test_env_note_may_omit_summary(tmp_path):
    """env.md never appears in the index, so a summary there buys nothing —
    a freshly scaffolded store must lint clean."""
    mem = _good_store(tmp_path)
    _note(mem, "env.md", "title: Env\ntype: env", "## Observations\n- [gotcha] x\n")
    report = memory_lint.lint(mem)
    assert not any("summary" in m for _, m in report.errors + report.warnings)


def test_type_must_match_the_folder(tmp_path):
    mem = _good_store(tmp_path)
    _note(mem / "screens", "wrong.md", "title: W\ntype: flow\nsummary: x")
    report = memory_lint.lint(mem)
    assert any("expected `screen`" in m for _, m in report.errors)


def test_unknown_category_is_an_error(tmp_path):
    """A typo'd category drops the fact out of every query built on the schema."""
    mem = _good_store(tmp_path)
    _note(mem / "screens", "typo.md", "title: T\ntype: screen\nsummary: x",
          "## Observations\n- [quirck] submit under keyboard #login\n")
    report = memory_lint.lint(mem)
    assert any("unknown category [quirck]" in m for _, m in report.errors)


def test_markdown_links_are_not_flagged_as_categories(tmp_path):
    mem = _good_store(tmp_path)
    _note(mem / "screens", "linky.md", "title: L\ntype: screen\nsummary: x",
          "## Notes\n- [the runbook](../runbook.md)\n"
          "## Observations\n- [native] native #login\n")
    report = memory_lint.lint(mem)
    assert not any("unknown category" in m for _, m in report.errors)


def test_malformed_identifier_is_an_error(tmp_path):
    """An identifier that doesn't parse is skipped by staleness reporting, so
    it silently stops being re-verified."""
    mem = _good_store(tmp_path)
    _note(mem / "screens", "bad.md", "title: B\ntype: screen\nsummary: x",
          "## Observations\n- [identifier] foo → F.swift #login\n")
    report = memory_lint.lint(mem)
    assert any("does not\n" not in m and "identifier must read" in m
               for _, m in report.errors)


def test_retired_stale_status_is_rejected(tmp_path):
    mem = _good_store(tmp_path)
    _note(mem / "screens", "bad.md", "title: B\ntype: screen\nsummary: x",
          "## Observations\n- [identifier] foo → F.swift; stale 2026-07-20 #login\n")
    report = memory_lint.lint(mem)
    assert any("unknown identifier status" in m for _, m in report.errors)


def test_untagged_note_warns_about_scoped_recall(tmp_path):
    mem = _good_store(tmp_path)
    _note(mem / "screens", "untagged.md", "title: U\ntype: screen\nsummary: x",
          "## Observations\n- [native] native form\n")
    report = memory_lint.lint(mem)
    assert any("#flow tag" in m for _, m in report.warnings)
    assert report.errors == []


def test_literal_credential_is_an_error(tmp_path):
    mem = _good_store(tmp_path)
    _note(mem, "env.md", "title: Env\ntype: env",
          "## Observations\n- [credential-env] password: hunter2SuperSecret\n")
    report = memory_lint.lint(mem)
    assert any("literal value" in m for _, m in report.errors)


def test_env_var_name_is_accepted(tmp_path):
    mem = _good_store(tmp_path)
    _note(mem, "env.md", "title: Env\ntype: env",
          "## Observations\n- [credential-env] password env var: APP_TEST_PASSWORD\n")
    report = memory_lint.lint(mem)
    assert report.errors == [], _messages(report)


def test_email_address_warns(tmp_path):
    mem = _good_store(tmp_path)
    _note(mem, "env.md", "title: Env\ntype: env",
          "## Observations\n- [credential-env] test account qa@example.com\n")
    report = memory_lint.lint(mem)
    assert any("email address" in m for _, m in report.warnings)


def test_stray_root_note_is_an_error(tmp_path):
    """A note in the store root is never read by Recall."""
    mem = _good_store(tmp_path)
    (mem / "notes.md").write_text("---\ntitle: x\n---\n", encoding="utf-8")
    report = memory_lint.lint(mem)
    assert any("stray note" in m for _, m in report.errors)


def test_ephemeral_and_generated_files_are_out_of_scope(tmp_path):
    mem = _good_store(tmp_path)
    (mem / "index.md").write_text("# Memory index\n", encoding="utf-8")
    (mem / ".session-requirement.md").write_text("no frontmatter here\n", encoding="utf-8")
    (mem / ".run-checkpoint.md").write_text("nor here\n", encoding="utf-8")
    report = memory_lint.lint(mem)
    assert report.errors == [], _messages(report)


def test_exit_codes(tmp_path, capsys):
    mem = _good_store(tmp_path)
    assert memory_lint.main([str(mem)]) == 0
    _note(mem / "screens", "untagged.md", "title: U\ntype: screen\nsummary: x",
          "## Observations\n- [native] native form\n")
    assert memory_lint.main([str(mem)]) == 0            # warnings alone pass
    assert memory_lint.main([str(mem), "--strict"]) == 1
    _note(mem / "screens", "typo.md", "title: T\ntype: screen\nsummary: x",
          "## Observations\n- [nope] x #login\n")
    assert memory_lint.main([str(mem)]) == 1
    capsys.readouterr()
