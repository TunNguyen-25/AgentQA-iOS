import sys
from pathlib import Path

from studio import runner


def _mk_tests(tmp_path: Path):
    tdir = tmp_path / "AutomationTests" / "tests"
    tdir.mkdir(parents=True)
    (tdir / "test_login.py").write_text("def test_ok():\n    assert True\n")
    (tdir / "test_checkout.py").write_text("def test_ok():\n    assert True\n")
    (tdir / "helper.py").write_text("# not a test\n")
    return tmp_path


def test_list_tests_only_test_files_sorted(tmp_path):
    _mk_tests(tmp_path)
    assert runner.list_tests(tmp_path, "AutomationTests") == [
        "test_checkout.py",
        "test_login.py",
    ]


def test_build_command_all(tmp_path):
    cmd = runner.build_command(tmp_path, "AutomationTests", "all")
    assert cmd[-2:] == ["tests", "-v"]


def test_build_command_single_file(tmp_path):
    cmd = runner.build_command(tmp_path, "AutomationTests", "test_login.py")
    assert cmd[-2:] == ["tests/test_login.py", "-v"]


def test_run_streams_lines_and_end_marker(tmp_path):
    _mk_tests(tmp_path)
    mgr = runner.RunManager()
    # run a trivial python instead of pytest to keep the test hermetic
    mgr._cmd_override = [sys.executable, "-c", "print('hello'); print('world')"]
    rid = mgr.start(tmp_path, "AutomationTests", "all", {})
    collected = list(mgr.lines(rid))
    assert "hello" in collected
    assert "world" in collected
    assert collected[-1].startswith("__END__:")
    assert mgr.status(rid) == "done"


def test_find_artifacts(tmp_path):
    adir = tmp_path / "AutomationTests" / "artifacts"
    adir.mkdir(parents=True)
    (adir / "failed_test_login.xml").write_text("<testsuite/>")
    (adir / "failed_test_login.png").write_bytes(b"\x89PNG")
    (adir / "failed_test_checkout.xml").write_text("<testsuite/>")
    arts = runner.find_artifacts(tmp_path, "AutomationTests")
    by_name = {a["name"]: a for a in arts}
    assert "failed_test_login" in by_name
    assert by_name["failed_test_login"]["png"].endswith("failed_test_login.png")
    assert "png" not in by_name["failed_test_checkout"]


def test_env_passthrough(tmp_path):
    _mk_tests(tmp_path)
    mgr = runner.RunManager()
    mgr._cmd_override = [sys.executable, "-c",
                         "import os; print(os.environ.get('STUDIO_FOO', 'MISSING'))"]
    rid = mgr.start(tmp_path, "AutomationTests", "all", {"STUDIO_FOO": "bar123"})
    collected = list(mgr.lines(rid))
    assert "bar123" in collected


def test_lines_second_consumer_does_not_hang(tmp_path):
    _mk_tests(tmp_path)
    mgr = runner.RunManager()
    mgr._cmd_override = [sys.executable, "-c", "print('once')"]
    rid = mgr.start(tmp_path, "AutomationTests", "all", {})
    first = list(mgr.lines(rid))
    assert first[-1].startswith("__END__:")
    second = list(mgr.lines(rid))          # must return promptly, not hang
    assert second and second[-1].startswith("__END__:")


def test_lines_unknown_run_id():
    mgr = runner.RunManager()
    assert list(mgr.lines("nope")) == ["__END__:unknown"]
