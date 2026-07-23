"""Appium driver fixture for agent-driven UI tests.

Reads the bundle id from ../.agentqa/config.yml (or AGENTQA_BUNDLE_ID env),
auto-detects the booted simulator, attaches without reinstalling (noReset),
wipes the app's local data unless reset_app_data is `never`, cold-starts the app
for deterministic sessions, and saves page_source + screenshot automatically when
a test fails.
"""
import json
import os
import shutil
import socket
import subprocess
from pathlib import Path

import pytest
from appium import webdriver
from appium.options.ios import XCUITestOptions
from selenium.webdriver.support.events import AbstractEventListener, EventFiringWebDriver

import runbook

_RUNBOOK_STEPS: list = []


class _RunbookListener(AbstractEventListener):
    def before_find(self, by, value, driver):
        _RUNBOOK_STEPS.append({"action": f"find {by}", "target": str(value), "status": "ok"})

    def after_click(self, element, driver):
        _RUNBOOK_STEPS.append({"action": "click", "target": "", "status": "ok"})

    def before_change_value_of(self, element, driver):
        _RUNBOOK_STEPS.append({"action": "send_keys", "target": "", "status": "ok"})


APPIUM_HOST = "127.0.0.1"
APPIUM_PORT = 4723
APPIUM_URL = f"http://{APPIUM_HOST}:{APPIUM_PORT}"
ARTIFACTS_DIR = Path(__file__).parent / "artifacts"


def config_value(key: str) -> str:
    """Read a top-level scalar from .agentqa/config.yml; "" when absent."""
    config = Path(__file__).resolve().parent.parent / ".agentqa" / "config.yml"
    if config.is_file():
        for line in config.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith(f"{key}:"):
                return line.split(":", 1)[1].split("#", 1)[0].strip().strip('"')
    return ""


def bundle_id() -> str:
    value = os.environ.get("AGENTQA_BUNDLE_ID") or config_value("bundle_id")
    if not value:
        raise RuntimeError(
            "Bundle id not configured — set it in .agentqa/config.yml or AGENTQA_BUNDLE_ID"
        )
    return value


def reset_app_data_enabled() -> bool:
    """Wipe the app's local data before the session? Defaults to yes."""
    policy = os.environ.get("AGENTQA_RESET_APP_DATA") or config_value("reset_app_data")
    return (policy or "always").lower() != "never"


BUNDLE_ID = bundle_id()


def booted_simulator_udid() -> str:
    out = subprocess.run(
        ["xcrun", "simctl", "list", "devices", "booted", "-j"],
        capture_output=True, text=True, check=True,
    ).stdout
    for devices in json.loads(out)["devices"].values():
        for device in devices:
            if device.get("state") == "Booted":
                return device["udid"]
    raise RuntimeError("No booted simulator. Boot one in Simulator.app first.")


def reset_app_data(udid: str) -> None:
    """Empty the app's data container so the session starts from a clean state.

    Deliberately not a simctl uninstall: removing the binary would force a
    reinstall, which is wrong when a human installed the build (build.policy:
    human). The simulator-wide keychain is shared across apps and is NOT wiped.
    """
    subprocess.run(["xcrun", "simctl", "terminate", udid, BUNDLE_ID],
                   capture_output=True, text=True, check=False)
    probe = subprocess.run(
        ["xcrun", "simctl", "get_app_container", udid, BUNDLE_ID, "data"],
        capture_output=True, text=True, check=False,
    )
    container = Path(probe.stdout.strip())
    if probe.returncode != 0 or "/Containers/Data/Application/" not in str(container):
        raise RuntimeError(
            f"Cannot reset {BUNDLE_ID}: no data container on the booted simulator "
            "(is the app installed?). Set reset_app_data: never to skip this."
        )
    for child in container.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child, ignore_errors=True)
        else:
            child.unlink(missing_ok=True)
    subprocess.run(["xcrun", "simctl", "privacy", udid, "reset", "all", BUNDLE_ID],
                   capture_output=True, text=True, check=False)


def assert_appium_reachable() -> None:
    try:
        with socket.create_connection((APPIUM_HOST, APPIUM_PORT), timeout=2):
            pass
    except OSError as exc:
        raise RuntimeError(
            f"Appium server not reachable at {APPIUM_URL}. Start it with: appium"
        ) from exc


@pytest.fixture(scope="session")
def driver():
    assert_appium_reachable()
    udid = booted_simulator_udid()
    if reset_app_data_enabled():
        reset_app_data(udid)
    options = XCUITestOptions()
    options.udid = udid
    options.bundle_id = BUNDLE_ID
    options.no_reset = True
    options.set_capability("appium:wdaLaunchTimeout", 120000)
    drv = webdriver.Remote(APPIUM_URL, options=options)
    # Cold-start the app so every session begins from a deterministic state.
    drv.terminate_app(BUNDLE_ID)
    drv.activate_app(BUNDLE_ID)
    yield EventFiringWebDriver(drv, _RunbookListener())
    drv.quit()


@pytest.fixture()
def page_source_dump(driver):
    def dump(name: str) -> Path:
        ARTIFACTS_DIR.mkdir(exist_ok=True)
        path = ARTIFACTS_DIR / f"{name}.xml"
        path.write_text(driver.page_source, encoding="utf-8")
        return path
    return dump


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """On failure, save page_source + screenshot so debugging starts with evidence."""
    outcome = yield
    report = outcome.get_result()
    if report.when != "call":
        return
    drv = item.funcargs.get("driver")
    if drv is None:
        return
    raw = getattr(drv, "wrapped_driver", drv)
    ARTIFACTS_DIR.mkdir(exist_ok=True)
    if report.failed:
        try:
            (ARTIFACTS_DIR / f"failed_{item.name}.xml").write_text(raw.page_source, encoding="utf-8")
            raw.get_screenshot_as_file(str(ARTIFACTS_DIR / f"failed_{item.name}.png"))
        except Exception:
            pass
    try:
        runbook.finalize(raw, item.name, list(_RUNBOOK_STEPS), report.passed, ARTIFACTS_DIR / "runbook")
    finally:
        _RUNBOOK_STEPS.clear()
