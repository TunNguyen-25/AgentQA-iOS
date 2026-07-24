import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
_spec = importlib.util.spec_from_file_location(
    "memory_write", Path(__file__).resolve().parent.parent / "scripts" / "memory-write.py"
)
memory_write = importlib.util.module_from_spec(_spec)
sys.modules["memory_write"] = memory_write
_spec.loader.exec_module(memory_write)

from memory_common import MemoryPathError  # noqa: E402


def _note(dir_, name, front, body=""):
    dir_.mkdir(parents=True, exist_ok=True)
    (dir_ / name).write_text(f"---\n{front}\n---\n{body}", encoding="utf-8")


def _screen(mem, name="login.md", body="## Observations\n"):
    _note(mem / "screens", name, "title: Login\ntype: screen\nsummary: x", body)
    return mem / "screens" / name


def test_rank_similar_orders_by_similarity(tmp_path):
    mem = tmp_path / "memory"
    _screen(mem, body=(
        "## Observations\n"
        "- [identifier] login_phone_field → LoginVC.swift:42; verified-in-hierarchy 2026-07-15 #login\n"
        "- [native] login screen is native\n"
    ))
    top = memory_write.rank_similar(
        mem, "identifier",
        "login_phone_field → LoginVC.swift:42; added-unverified 2026-07-22 #login")
    assert top, "should find candidates"
    assert "login_phone_field" in top[0][4]   # the near-identical line ranks first
    assert top[0][0] > 0.6


def test_apply_add_appends_observation(tmp_path, capsys):
    mem = tmp_path / "memory"
    note = _screen(mem)
    rc = memory_write.main([
        "apply", "--op", "ADD", "--memory-dir", str(mem),
        "--note", "screens/login", "--category", "native", "--text", "login screen is native",
    ])
    assert rc == 0
    assert "- [native] login screen is native" in note.read_text()
    assert "ADDED" in capsys.readouterr().out


def test_apply_add_missing_note_errors(tmp_path):
    mem = tmp_path / "memory"
    (mem / "screens").mkdir(parents=True)
    with pytest.raises(FileNotFoundError):
        memory_write.main([
            "apply", "--op", "ADD", "--memory-dir", str(mem),
            "--note", "screens/nope", "--category", "native", "--text", "x",
        ])


def test_apply_update_replaces_target_line(tmp_path):
    mem = tmp_path / "memory"
    note = _screen(mem, body=(
        "## Observations\n"
        "- [identifier] foo → F.swift; added-unverified 2026-07-22 #login\n"
    ))
    rc = memory_write.main([
        "apply", "--op", "UPDATE", "--memory-dir", str(mem),
        "--target", "screens/login.md:7",
        "--category", "identifier",
        "--text", "foo → F.swift; verified-in-hierarchy 2026-07-22 #login",
    ])
    assert rc == 0
    text = note.read_text()
    assert "verified-in-hierarchy" in text
    assert "added-unverified" not in text


def test_apply_delete_removes_target_line(tmp_path):
    mem = tmp_path / "memory"
    note = _screen(mem, body="## Observations\n- [quirk] submit sits under keyboard\n")
    rc = memory_write.main([
        "apply", "--op", "DELETE", "--memory-dir", str(mem),
        "--target", "screens/login.md:7",
    ])
    assert rc == 0
    assert "submit sits under keyboard" not in note.read_text()


def test_apply_noop_writes_nothing(tmp_path, capsys):
    mem = tmp_path / "memory"
    note = _screen(mem, body="## Observations\n- [native] x\n")
    before = note.read_text()
    rc = memory_write.main(["apply", "--op", "NOOP", "--memory-dir", str(mem)])
    assert rc == 0
    assert note.read_text() == before
    assert "NOOP" in capsys.readouterr().out


def test_missing_op_errors(tmp_path):
    with pytest.raises(SystemExit):
        memory_write.main(["apply", "--memory-dir", str(tmp_path)])


def _git_repo(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "init"], cwd=tmp_path, check=True)


def test_batch_refresh_survives_its_own_edits(tmp_path):
    """Step 6 refreshes every identifier it verified, so the guard must not
    treat the batch's own earlier writes as a reason to stop."""
    mem = tmp_path / "memory"
    _screen(mem, body=(
        "## Observations\n"
        "- [identifier] foo → F.swift; added-unverified 2026-07-22 #login\n"
        "- [identifier] bar → B.swift; added-unverified 2026-07-22 #login\n"))
    _git_repo(tmp_path)
    for lineno, name in ((7, "foo → F.swift"), (8, "bar → B.swift")):
        rc = memory_write.main([
            "apply", "--op", "UPDATE", "--memory-dir", str(mem),
            "--target", f"screens/login.md:{lineno}", "--category", "identifier",
            "--text", f"{name}; verified-in-hierarchy 2026-07-22 #login",
        ])
        assert rc == 0
    text = (mem / "screens" / "login.md").read_text(encoding="utf-8")
    assert text.count("verified-in-hierarchy") == 2
    assert "added-unverified" not in text


def test_dirty_status_is_detected_with_a_relative_memory_dir(tmp_path, monkeypatch):
    """`git status -- <pathspec>` resolves against cwd, and cwd is the memory
    dir — a relative pathspec used to match nothing and read as clean."""
    mem = tmp_path / "memory"
    note = _screen(mem, body="## Observations\n- [quirk] a\n")
    _git_repo(tmp_path)
    note.write_text(note.read_text() + "- [quirk] scratch\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert memory_write.memory_dir_dirty("memory") is True


def test_guard_blocks_update_on_merge_conflict(tmp_path):
    """A revert would discard conflict markers that were never committed."""
    mem = tmp_path / "memory"
    _screen(mem, body=(
        "## Observations\n- [identifier] foo → F.swift; added-unverified 2026-07-22 #login\n"))
    _git_repo(tmp_path)
    conflicted = []

    def fake_status(_memory_dir):
        return ["UU memory/screens/login.md"] if not conflicted else []

    original = memory_write.memory_status
    memory_write.memory_status = fake_status
    try:
        with pytest.raises(SystemExit):
            memory_write.main([
                "apply", "--op", "UPDATE", "--memory-dir", str(mem),
                "--target", "screens/login.md:7", "--category", "identifier",
                "--text", "foo → F.swift; verified-in-hierarchy 2026-07-22 #login",
            ])
        rc = memory_write.main([
            "apply", "--op", "UPDATE", "--memory-dir", str(mem), "--force",
            "--target", "screens/login.md:7", "--category", "identifier",
            "--text", "foo → F.swift; verified-in-hierarchy 2026-07-22 #login",
        ])
        assert rc == 0
    finally:
        memory_write.memory_status = original


def test_add_writes_only_the_note(tmp_path):
    mem = tmp_path / "memory"
    _screen(mem)
    memory_write.main([
        "apply", "--op", "ADD", "--memory-dir", str(mem),
        "--note", "screens/login", "--category", "native", "--text", "login screen is native",
    ])
    assert "login screen is native" in (mem / "screens" / "login.md").read_text()
    assert not (tmp_path / "metrics").exists()


# --- the persistent-store boundary ------------------------------------------

def test_refuses_to_write_the_generated_index(tmp_path):
    """index.md is rebuilt from the notes — an edit here is erased silently."""
    mem = tmp_path / "memory"
    _screen(mem)
    (mem / "index.md").write_text("# Memory index\n", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        memory_write.main([
            "apply", "--op", "ADD", "--memory-dir", str(mem),
            "--note", "index", "--category", "quirk", "--text", "x",
        ])
    assert "generated" in str(e.value)


def test_refuses_to_write_session_state(tmp_path):
    """The requirement note holds claims nobody has verified live — letting a
    Capture land there is how an unverified spec claim reaches the store."""
    mem = tmp_path / "memory"
    _screen(mem)
    (mem / ".session-requirement.md").write_text("## Success\nx\n", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        memory_write.main([
            "apply", "--op", "UPDATE", "--memory-dir", str(mem),
            "--target", ".session-requirement.md:2",
            "--category", "assertion", "--text", "x",
        ])
    assert "session state" in str(e.value)


def test_refuses_paths_outside_the_store(tmp_path):
    mem = tmp_path / "memory"
    _screen(mem)
    with pytest.raises(SystemExit) as e:
        memory_write.main([
            "apply", "--op", "ADD", "--memory-dir", str(mem),
            "--note", "../../escape", "--category", "quirk", "--text", "x",
        ])
    assert "outside the memory store" in str(e.value)


def test_dedup_scan_ignores_ephemeral_and_generated_files(tmp_path):
    """A session-scoped claim must not surface as a dedup candidate — it would
    invite an UPDATE into a file that is about to be deleted."""
    mem = tmp_path / "memory"
    _screen(mem, body="## Observations\n- [native] login screen is native #login\n")
    (mem / ".session-requirement.md").write_text(
        "## Success\n- [assertion] spec says it lands on home #login\n", encoding="utf-8")
    (mem / "index.md").write_text(
        "- [assertion] generated line #login\n", encoding="utf-8")
    hits = list(memory_write.iter_observations(mem))
    assert hits, "the real note should still be scanned"
    assert all("screens" in str(p) for p, *_ in hits)


def test_markdown_link_bullets_are_not_observations(tmp_path):
    """`- [text](url)` matches the observation shape but is a link."""
    mem = tmp_path / "memory"
    _screen(mem, body="## Notes\n- [see the runbook](../runbook.md)\n")
    assert list(memory_write.iter_observations(mem)) == []


# --- schema + secret validation ---------------------------------------------

def test_rejects_unknown_category(tmp_path):
    mem = tmp_path / "memory"
    _screen(mem)
    with pytest.raises(SystemExit) as e:
        memory_write.main([
            "apply", "--op", "ADD", "--memory-dir", str(mem),
            "--note", "screens/login", "--category", "identifer", "--text", "x",
        ])
    assert "unknown category" in str(e.value)


def test_rejects_malformed_identifier(tmp_path):
    mem = tmp_path / "memory"
    _screen(mem)
    with pytest.raises(SystemExit) as e:
        memory_write.main([
            "apply", "--op", "ADD", "--memory-dir", str(mem),
            "--note", "screens/login", "--category", "identifier",
            "--text", "login_pw → V.swift #login",     # no status, no date
        ])
    assert "identifier observations must read" in str(e.value)


def test_rejects_retired_stale_status(tmp_path):
    """Staleness is computed from the date; a declared `stale` status could
    disagree with the calendar, so it is no longer part of the schema."""
    mem = tmp_path / "memory"
    _screen(mem)
    with pytest.raises(SystemExit) as e:
        memory_write.main([
            "apply", "--op", "ADD", "--memory-dir", str(mem),
            "--note", "screens/login", "--category", "identifier",
            "--text", "foo → F.swift; stale 2026-07-22 #login",
        ])
    assert "unknown identifier status" in str(e.value)


@pytest.mark.parametrize("text", [
    "password: hunter2SuperSecret",
    "token=ghp_abcdefghijklmnopqrstuvwxyz012345",
    "api_key: AIzaSyA1234567890abcdefghijklmnopqrst",
])
def test_rejects_literal_credentials(tmp_path, text):
    mem = tmp_path / "memory"
    _screen(mem)
    with pytest.raises(SystemExit):
        memory_write.main([
            "apply", "--op", "ADD", "--memory-dir", str(mem),
            "--note", "screens/login", "--category", "credential-env", "--text", text,
        ])


@pytest.mark.parametrize("text", [
    "password env var is APP_TEST_PASSWORD",
    "password: APP_TEST_PASSWORD",
    "password: <fill from config.yml>",
])
def test_accepts_credential_references(tmp_path, text):
    """Naming the env var is the documented way to reference a credential."""
    mem = tmp_path / "memory"
    _screen(mem)
    assert memory_write.main([
        "apply", "--op", "ADD", "--memory-dir", str(mem),
        "--note", "screens/login", "--category", "credential-env", "--text", text,
    ]) == 0


def test_out_of_range_target_gets_an_actionable_error(tmp_path):
    """Line numbers shift as a batch deletes lines, so a stale --target is a
    realistic mid-session failure — it should point back at propose, not
    traceback."""
    mem = tmp_path / "memory"
    _screen(mem, body="## Observations\n- [native] x #login\n")
    with pytest.raises(SystemExit) as e:
        memory_write.main([
            "apply", "--op", "UPDATE", "--memory-dir", str(mem),
            "--target", "screens/login.md:99", "--category", "native",
            "--text", "y #login",
        ])
    assert "out of range" in str(e.value) and "propose" in str(e.value)


def test_resolve_persistent_accepts_the_four_locations(tmp_path):
    mem = tmp_path / "memory"
    for note in ("flows/login", "screens/login", "failures/wda", "env"):
        assert memory_write.resolve_note(mem, note).is_relative_to(mem.resolve())
    with pytest.raises(MemoryPathError):
        memory_write.resolve_note(mem, "README")
