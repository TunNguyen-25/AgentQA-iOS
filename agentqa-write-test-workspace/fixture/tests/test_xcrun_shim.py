"""The part of simctl's contract that `reset-app-data.sh` actually depends on.

The shim used to answer `get_app_container` with `<state>/app-container` and exit
0 for any bundle at all. Both halves were wrong, and together they hid a real
bug: the script decided whether the app was installed by matching the path
against `*/Containers/Data/Application/*`, so against this shim every run took
the "not installed" branch, skipped the wipe, and said so in a way that read like
success. Exploration then started from whatever state the previous run left.

So the shim owes callers two things a made-up path cannot give them: a container
path shaped the way simctl shapes it, and a non-zero exit when the app is not
installed.

Run with: python3 -m pytest fixture/tests
"""
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURE = Path(__file__).resolve().parent.parent
XCRUN = FIXTURE / "bin" / "xcrun"
RESET = (Path(__file__).resolve().parents[3]
         / "skills" / "agentqa-init" / "scripts" / "reset-app-data.sh")
BUNDLE = "com.vnpt.media.mobileb2c"


@pytest.fixture()
def state(tmp_path):
    return {"AGENTQA_EVAL_STATE": str(tmp_path / "state"),
            "AGENTQA_EVAL_REPO": str(tmp_path / "repo"),
            "PATH": f"{FIXTURE / 'bin'}:/usr/bin:/bin"}


def xcrun(state, *args):
    return subprocess.run([sys.executable, str(XCRUN), *args],
                          capture_output=True, text=True, env=state)


def test_get_app_container_returns_a_real_simctl_shaped_path(state):
    result = xcrun(state, "simctl", "get_app_container", "booted", BUNDLE, "data")

    assert result.returncode == 0, result.stderr
    container = Path(result.stdout.strip())
    assert "/Containers/Data/Application/" in str(container)
    assert container.is_dir()


def test_get_app_container_fails_for_an_app_that_is_not_installed(state):
    result = xcrun(state, "simctl", "get_app_container", "booted", "com.nope.app", "data")

    assert result.returncode != 0
    assert result.stdout.strip() == ""
    assert "com.nope.app" in result.stderr


def test_the_container_sits_outside_the_shim_state_files(state, tmp_path):
    """reset-app-data.sh empties everything inside the container; state.json and
    calls.jsonl live in the same state dir and must survive that."""
    xcrun(state, "simctl", "list", "devices", "booted")   # writes calls.jsonl
    result = xcrun(state, "simctl", "get_app_container", "booted", BUNDLE, "data")

    container = Path(result.stdout.strip())
    state_dir = Path(state["AGENTQA_EVAL_STATE"])
    assert container.is_relative_to(state_dir)
    assert not any(p.is_relative_to(container) for p in state_dir.glob("*.json*"))


# ----------------------------------------------------- the two used together
def test_reset_app_data_actually_wipes_against_this_shim(state, tmp_path):
    """The regression: this combination used to skip the wipe and exit 0."""
    repo = Path(state["AGENTQA_EVAL_REPO"])
    (repo / ".agentqa").mkdir(parents=True)
    (repo / ".agentqa" / "config.yml").write_text(
        f"platform: ios\nbundle_id: {BUNDLE}\n", encoding="utf-8")
    container = Path(xcrun(state, "simctl", "get_app_container", "booted",
                           BUNDLE, "data").stdout.strip())
    (container / "Documents").mkdir(parents=True)
    (container / "Documents" / "cache.db").write_text("stale", encoding="utf-8")

    result = subprocess.run(["bash", str(RESET)], capture_output=True, text=True,
                            env={**state, "AGENTQA_PROJECT_ROOT": str(repo)})

    assert result.returncode == 0, result.stderr
    assert "wiped data container" in result.stdout
    assert list(container.iterdir()) == []


def test_reset_app_data_refuses_an_app_that_is_not_installed(state, tmp_path):
    repo = Path(state["AGENTQA_EVAL_REPO"])
    (repo / ".agentqa").mkdir(parents=True)
    (repo / ".agentqa" / "config.yml").write_text(
        "platform: ios\nbundle_id: com.nope.app\n", encoding="utf-8")

    result = subprocess.run(["bash", str(RESET)], capture_output=True, text=True,
                            env={**state, "AGENTQA_PROJECT_ROOT": str(repo)})

    assert result.returncode != 0
    assert "not installed" in result.stderr
