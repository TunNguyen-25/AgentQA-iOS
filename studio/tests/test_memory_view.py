from pathlib import Path

import pytest

from studio import memory_view


def _mk_mem(tmp_path: Path):
    mem = tmp_path / ".agentqa" / "memory"
    (mem / "flows").mkdir(parents=True)
    (mem / "screens").mkdir()
    (mem / "failures").mkdir()
    (mem / "flows" / "login.md").write_text("# login flow\n")
    (mem / "screens" / "login.md").write_text("# login screen\n")
    (mem / "env.md").write_text("env notes\n")
    return tmp_path


def test_list_notes(tmp_path):
    _mk_mem(tmp_path)
    notes = memory_view.list_notes(tmp_path)
    assert notes["flows"] == ["login"]
    assert notes["screens"] == ["login"]
    assert notes["failures"] == []
    assert notes["env"] is True


def test_read_note_ok(tmp_path):
    _mk_mem(tmp_path)
    assert "login flow" in memory_view.read_note(tmp_path, "flows/login.md")


def test_read_note_rejects_traversal(tmp_path):
    _mk_mem(tmp_path)
    with pytest.raises(ValueError):
        memory_view.read_note(tmp_path, "../../etc/passwd")


def test_stale_and_lint_none_without_scripts(tmp_path):
    _mk_mem(tmp_path)
    assert memory_view.stale(tmp_path, None) is None
    assert memory_view.lint(tmp_path, None) is None


def _fake_script(dirpath, name, body):
    dirpath.mkdir(parents=True, exist_ok=True)
    (dirpath / name).write_text(body)
    return dirpath


def test_stale_with_script(tmp_path):
    _mk_mem(tmp_path)
    scripts = tmp_path / "scripts"
    _fake_script(scripts, "memory-index.py", "print('stale-note: x')\n")
    out = memory_view.stale(tmp_path, scripts)
    assert "stale-note: x" in out


def test_stale_script_failure_surfaces_stderr(tmp_path):
    _mk_mem(tmp_path)
    scripts = tmp_path / "scripts"
    _fake_script(scripts, "memory-index.py",
                 "import sys\nsys.stderr.write('boom\\n')\nsys.exit(2)\n")
    out = memory_view.stale(tmp_path, scripts)
    assert "boom" in out


def test_lint_with_script_ok(tmp_path):
    _mk_mem(tmp_path)
    scripts = tmp_path / "scripts"
    _fake_script(scripts, "memory-lint.py", "print('clean')\n")
    result = memory_view.lint(tmp_path, scripts)
    assert result["ok"] is True
    assert "clean" in result["output"]


def test_lint_with_script_failure(tmp_path):
    _mk_mem(tmp_path)
    scripts = tmp_path / "scripts"
    _fake_script(scripts, "memory-lint.py",
                 "import sys\nsys.stderr.write('bad note\\n')\nsys.exit(1)\n")
    result = memory_view.lint(tmp_path, scripts)
    assert result["ok"] is False
    assert "bad note" in result["output"]


def test_read_note_rejects_directory(tmp_path):
    _mk_mem(tmp_path)
    with pytest.raises(ValueError):
        memory_view.read_note(tmp_path, "flows")
