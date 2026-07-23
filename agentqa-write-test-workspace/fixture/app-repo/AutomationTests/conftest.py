"""Appium driver fixture for agent-driven UI tests.

Reads the bundle id from ../.agentqa/config.yml, attaches to the booted
simulator, wipes the app's data before the session when
`reset_app_data: always`, and saves page_source + a screenshot whenever a test
fails so a later run can diagnose it without re-running.
"""
import os
import subprocess
from pathlib import Path

import pytest
from appium import webdriver
from appium.options.ios import XCUITestOptions

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / ".agentqa" / "config.yml"
ARTIFACTS = Path(__file__).parent / "artifacts"
APPIUM_URL = "http://127.0.0.1:4723"


def _config(key: str, default: str = "") -> str:
    if not CONFIG.is_file():
        return default
    for line in CONFIG.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith(f"{key}:"):
            return line.split(":", 1)[1].split("#", 1)[0].strip().strip('"')
    return default


BUNDLE_ID = os.environ.get("AGENTQA_BUNDLE_ID") or _config("bundle_id")
RESET_APP_DATA = _config("reset_app_data", "always")


@pytest.fixture(scope="session", autouse=True)
def wipe_app_data():
    """reset_app_data: always -> every session starts from a clean install."""
    if RESET_APP_DATA == "always":
        subprocess.run(["xcrun", "simctl", "terminate", "booted", BUNDLE_ID],
                       check=False, capture_output=True)
        subprocess.run(["xcrun", "simctl", "privacy", "booted", "reset", "all",
                        BUNDLE_ID], check=False, capture_output=True)


@pytest.fixture(scope="session")
def driver(wipe_app_data):
    options = XCUITestOptions()
    options.bundle_id = BUNDLE_ID
    options.platform_name = "iOS"
    options.automation_name = "XCUITest"
    options.new_command_timeout = 300
    drv = webdriver.Remote(APPIUM_URL, options=options)
    drv.implicitly_wait(10)
    yield drv
    drv.quit()


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        drv = item.funcargs.get("driver")
        if drv is None:
            return
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        stem = ARTIFACTS / f"failed_{item.name}"
        try:
            stem.with_suffix(".xml").write_text(drv.page_source, encoding="utf-8")
            drv.save_screenshot(str(stem.with_suffix(".png")))
        except Exception:
            pass
