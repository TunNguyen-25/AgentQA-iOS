"""Tests for scripts/reset-app-data.sh — the standalone wipe helper.

conftest.py does the same job inside a pytest session and is covered by
test_conftest_reset.py; this script is what a person or an agent runs by hand
before exploring, so it has to fail the same way for the same reasons.

The script shells out to `xcrun` and `adb`, so each test puts a fake one first on
PATH. The fakes record their argv, which is how "did it refuse to delete
anything?" gets checked rather than assumed.

The case that motivated this file: the script used to decide whether the app was
installed by pattern-matching the container path, so any path simctl phrased
unexpectedly was reported as "not installed" and the wipe was skipped — exit 0,
reassuring message, stale data. Installed-ness is the exit code's job; the path
shape is only a guard on `rm -rf`.
"""
import os
import subprocess
import textwrap
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "reset-app-data.sh"

IOS_CONFIG = "platform: ios\nbundle_id: com.example.app\n"
ANDROID_CONFIG = "platform: android\napp_package: com.example.app\n"


@pytest.fixture()
def project(tmp_path):
    """A repo root with .agentqa/config.yml and an empty bin/ ahead of PATH."""
    class Project:
        def __init__(self):
            self.root = tmp_path / "repo"
            self.bin = tmp_path / "bin"
            (self.root / ".agentqa").mkdir(parents=True)
            self.bin.mkdir()

        def config(self, body):
            (self.root / ".agentqa" / "config.yml").write_text(body, encoding="utf-8")

        def fake(self, name, body):
            """Install a fake CLI that appends its argv to <name>.log."""
            path = self.bin / name
            path.write_text(
                "#!/usr/bin/env bash\n"
                f'printf "%s\\n" "$*" >> "{self.bin}/{name}.log"\n' + body,
                encoding="utf-8")
            path.chmod(0o755)

        def calls(self, name):
            log = self.bin / f"{name}.log"
            return log.read_text(encoding="utf-8").splitlines() if log.exists() else []

        def run(self, *args, **env):
            environ = dict(os.environ)
            environ.pop("AGENTQA_PLATFORM", None)
            environ.pop("AGENTQA_BUNDLE_ID", None)
            environ.pop("AGENTQA_APP_PACKAGE", None)
            environ.update(AGENTQA_PROJECT_ROOT=str(self.root),
                           PATH=f"{self.bin}:{environ['PATH']}")
            environ.update(env)
            return subprocess.run(["bash", str(SCRIPT), *args],
                                  capture_output=True, text=True, env=environ)

    return Project()


def _simctl(container_line, get_container_status=0, booted=True):
    """A fake xcrun whose `get_app_container` behaviour the test controls."""
    devices = ('echo "    iPhone 16 Pro (UDID) (Booted)"' if booted
               else 'echo "-- no devices --"')
    emit = 'echo "%s"' % container_line if container_line else ":"
    return textwrap.dedent(f"""
        case "$2" in
          list)
            {devices}
            ;;
          get_app_container)
            {emit}
            if [ {get_container_status} -ne 0 ]; then
              echo "No installed application with bundle identifier was found." >&2
            fi
            exit {get_container_status}
            ;;
        esac
        exit 0
    """)


def _container(tmp_path, *, files=("Library/Preferences/app.plist", "Documents/db.sqlite")):
    container = tmp_path / "Containers" / "Data" / "Application" / "ABC-123"
    for rel in files:
        path = container / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("data", encoding="utf-8")
    return container


# ------------------------------------------------------------------- iOS, happy
def test_wipes_the_container_contents_and_keeps_the_container(project, tmp_path):
    project.config(IOS_CONFIG)
    container = _container(tmp_path)
    project.fake("xcrun", _simctl(container))

    result = project.run()

    assert result.returncode == 0, result.stderr
    assert container.is_dir() and list(container.iterdir()) == []
    assert "wiped data container" in result.stdout
    joined = " | ".join(project.calls("xcrun"))
    assert "simctl terminate booted com.example.app" in joined
    assert "simctl privacy booted reset all com.example.app" in joined


def test_an_explicit_bundle_argument_beats_the_config(project, tmp_path):
    project.config(IOS_CONFIG)
    project.fake("xcrun", _simctl(_container(tmp_path)))

    result = project.run("com.other.app")

    assert result.returncode == 0, result.stderr
    assert "com.other.app" in " | ".join(project.calls("xcrun"))


# ------------------------------------------------------- iOS, the hardened paths
def test_not_installed_is_decided_by_the_exit_code_not_the_path(project, tmp_path):
    """simctl says so itself; nothing about the printed text is consulted."""
    project.config(IOS_CONFIG)
    project.fake("xcrun", _simctl("", get_container_status=2))

    result = project.run()

    assert result.returncode != 0
    assert "not installed" in result.stderr
    assert "simctl:" in result.stderr, "simctl's own message should be passed through"


def test_a_silent_simctl_failure_still_reports_and_cleans_up(project):
    """simctl exiting non-zero with nothing on stderr must not swallow the report
    or leave the scratch file behind."""
    project.config(IOS_CONFIG)
    project.fake("xcrun", textwrap.dedent("""
        case "$2" in
          list) echo "  iPhone 16 Pro (UDID) (Booted)" ;;
          get_app_container) exit 4 ;;
        esac
        exit 0
    """))
    tmpdir = Path(os.environ.get("TMPDIR", "/tmp"))
    before = set(tmpdir.glob("reset-app-data.*"))

    result = project.run()

    assert result.returncode != 0
    assert "exited 4" in result.stderr
    assert set(tmpdir.glob("reset-app-data.*")) == before


def test_an_unexpected_container_path_fails_loudly_instead_of_skipping_the_wipe(
        project, tmp_path):
    """The regression this file exists for.

    simctl exited 0, so the app IS installed — but the path is not one this
    script recognises. Reporting "not installed" and exiting 0 there is the worst
    of both worlds: nothing is wiped and the caller is told everything is fine.
    """
    stray = tmp_path / "somewhere" / "else"
    stray.mkdir(parents=True)
    (stray / "precious.txt").write_text("keep me", encoding="utf-8")
    project.config(IOS_CONFIG)
    project.fake("xcrun", _simctl(stray))

    result = project.run()

    assert result.returncode != 0
    assert (stray / "precious.txt").exists(), "must not delete under a path it cannot vouch for"
    assert "unexpected data container" in result.stderr
    assert str(stray) in result.stderr, "the path it refused to touch must be in the log"
    assert "not installed" not in result.stderr, "the app IS installed; do not say otherwise"


def test_a_container_that_looks_right_but_is_missing_is_reported(project, tmp_path):
    project.config(IOS_CONFIG)
    project.fake("xcrun", _simctl(tmp_path / "Containers" / "Data" / "Application" / "GONE"))

    result = project.run()

    assert result.returncode != 0
    assert "does not exist" in result.stderr


def test_empty_output_with_a_zero_exit_is_not_treated_as_a_container(project):
    project.config(IOS_CONFIG)
    project.fake("xcrun", _simctl(""))

    result = project.run()

    assert result.returncode != 0
    assert "no data container path" in result.stderr


def test_privacy_is_not_reset_when_the_wipe_did_not_happen(project, tmp_path):
    """Resetting privacy grants after a failed wipe half-does the job and hides it."""
    project.config(IOS_CONFIG)
    project.fake("xcrun", _simctl(tmp_path / "not" / "a" / "container"))

    project.run()

    assert not any("privacy" in call for call in project.calls("xcrun"))


def test_no_booted_simulator_is_an_error(project):
    project.config(IOS_CONFIG)
    project.fake("xcrun", _simctl("", booted=False))

    result = project.run()

    assert result.returncode != 0
    assert "no booted simulator" in result.stderr


def test_a_missing_bundle_id_is_an_error(project):
    project.config("platform: ios\n")
    project.fake("xcrun", _simctl(""))

    result = project.run()

    assert result.returncode != 0
    assert "no bundle id" in result.stderr


# --------------------------------------------------------------------- Android
ADB_INSTALLED = textwrap.dedent("""
    case "$*" in
      *"get-state"*) echo device ;;
      *"pm list packages"*) echo "package:com.example.app" ;;
      *"pm clear"*) echo "Success" ;;
    esac
    exit 0
""")


def test_android_clears_the_package(project):
    project.config(ANDROID_CONFIG)
    project.fake("adb", ADB_INSTALLED)

    result = project.run()

    assert result.returncode == 0, result.stderr
    assert "cleared data + permissions" in result.stdout
    assert any("pm clear com.example.app" in call for call in project.calls("adb"))


def test_android_reports_a_pm_clear_that_did_not_succeed(project):
    """`adb shell` exits 0 whatever the command inside did, so pm's own output is
    the only evidence the clear actually happened."""
    project.config(ANDROID_CONFIG)
    project.fake("adb", ADB_INSTALLED.replace('echo "Success"',
                                              'echo "Failed"'))

    result = project.run()

    assert result.returncode != 0
    assert "did not report success" in result.stderr


def test_android_not_installed_is_an_error_and_clears_nothing(project):
    project.config(ANDROID_CONFIG)
    project.fake("adb", ADB_INSTALLED.replace('echo "package:com.example.app"', ":"))

    result = project.run()

    assert result.returncode != 0
    assert "not installed" in result.stderr
    assert not any("pm clear" in call for call in project.calls("adb"))


def test_android_does_not_clear_a_lookalike_package(project):
    """`pm list packages` prefix-matches; com.example.app2 is a different app."""
    project.config(ANDROID_CONFIG)
    project.fake("adb", ADB_INSTALLED.replace("package:com.example.app",
                                              "package:com.example.app2"))

    result = project.run()

    assert result.returncode != 0
    assert not any("pm clear" in call for call in project.calls("adb"))


def test_android_with_no_device_connected_is_an_error(project):
    project.config(ANDROID_CONFIG)
    project.fake("adb", 'if [ "$1" = "get-state" ]; then exit 1; fi\nexit 0\n')

    result = project.run()

    assert result.returncode != 0
    assert "no Android device" in result.stderr


# -------------------------------------------------------------------- dispatch
def test_env_platform_overrides_the_config(project):
    project.config(IOS_CONFIG)
    project.fake("adb", ADB_INSTALLED)

    result = project.run(AGENTQA_PLATFORM="android",
                         AGENTQA_APP_PACKAGE="com.example.app")

    assert result.returncode == 0, result.stderr
    assert any("pm clear com.example.app" in call for call in project.calls("adb"))


def test_an_unknown_platform_is_an_error(project):
    project.config("platform: windows\nbundle_id: com.example.app\n")

    result = project.run()

    assert result.returncode != 0
    assert "unknown platform" in result.stderr
