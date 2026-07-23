"""Appium driver fixture for agent-driven UI tests (iOS + Android).

Reads the target platform and app id from ../.agentqa/config.yml (or the
AGENTQA_* env overrides), attaches to the booted device without reinstalling
(noReset), wipes the app's local data unless reset_app_data is `never`,
cold-starts the app for deterministic sessions, and saves page_source + a
screenshot automatically when a test fails.

Platform is selected by `platform:` in the config:
  ios      -> XCUITest driver, `xcrun simctl` for device + data reset
  android  -> UiAutomator2 driver, `adb` for device + `adb shell pm clear` reset

The Appium option classes are imported lazily (inside the driver builders) so
loading this module never requires the driver for a platform you don't use.
"""
import json
import os
import shutil
import socket
import subprocess
from pathlib import Path

import pytest
from appium import webdriver
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


def platform() -> str:
    """`ios` (default) or `android` — env override wins over the config."""
    return (os.environ.get("AGENTQA_PLATFORM") or config_value("platform") or "ios").lower()


def app_id() -> str:
    """The app under test: bundle id on iOS, package name on Android."""
    if platform() == "android":
        value = os.environ.get("AGENTQA_APP_PACKAGE") or config_value("app_package")
        if not value:
            raise RuntimeError(
                "App package not configured — set app_package in .agentqa/config.yml "
                "or AGENTQA_APP_PACKAGE"
            )
        return value
    value = os.environ.get("AGENTQA_BUNDLE_ID") or config_value("bundle_id")
    if not value:
        raise RuntimeError(
            "Bundle id not configured — set it in .agentqa/config.yml or AGENTQA_BUNDLE_ID"
        )
    return value


def app_activity() -> str:
    """Android launcher activity (optional; Appium auto-resolves when absent)."""
    return os.environ.get("AGENTQA_APP_ACTIVITY") or config_value("app_activity")


def reset_app_data_enabled() -> bool:
    """Wipe the app's local data before the session? Defaults to yes."""
    policy = os.environ.get("AGENTQA_RESET_APP_DATA") or config_value("reset_app_data")
    return (policy or "always").lower() != "never"


PLATFORM = platform()
APP_ID = app_id()
# Back-compat alias: on iOS this is the bundle id; kept so anything referencing
# BUNDLE_ID keeps working. Prefer APP_ID in new code.
BUNDLE_ID = APP_ID


# --------------------------------------------------------------------------- iOS
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


def _reset_app_data_ios(udid: str) -> None:
    """Empty the app's data container so the session starts from a clean state.

    Deliberately not a simctl uninstall: removing the binary would force a
    reinstall, which is wrong when a human installed the build (build.policy:
    human). The simulator-wide keychain is shared across apps and is NOT wiped.
    """
    subprocess.run(["xcrun", "simctl", "terminate", udid, APP_ID],
                   capture_output=True, text=True, check=False)
    probe = subprocess.run(
        ["xcrun", "simctl", "get_app_container", udid, APP_ID, "data"],
        capture_output=True, text=True, check=False,
    )
    container = Path(probe.stdout.strip())
    if probe.returncode != 0 or "/Containers/Data/Application/" not in str(container):
        raise RuntimeError(
            f"Cannot reset {APP_ID}: no data container on the booted simulator "
            "(is the app installed?). Set reset_app_data: never to skip this."
        )
    for child in container.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child, ignore_errors=True)
        else:
            child.unlink(missing_ok=True)
    subprocess.run(["xcrun", "simctl", "privacy", udid, "reset", "all", APP_ID],
                   capture_output=True, text=True, check=False)


def _build_ios_driver(udid: str):
    from appium.options.ios import XCUITestOptions
    options = XCUITestOptions()
    options.udid = udid
    options.bundle_id = APP_ID
    options.no_reset = True
    options.set_capability("appium:wdaLaunchTimeout", 120000)
    return webdriver.Remote(APPIUM_URL, options=options)


# ----------------------------------------------------------------------- Android
def connected_android_serial() -> str:
    """Serial of the one connected device/emulator ($ANDROID_SERIAL picks among many)."""
    preferred = os.environ.get("ANDROID_SERIAL")
    out = subprocess.run(["adb", "devices"], capture_output=True, text=True, check=True).stdout
    serials = [line.split()[0] for line in out.splitlines()[1:]
               if line.strip() and line.split()[-1] == "device"]
    if not serials:
        raise RuntimeError("No Android device/emulator connected. Boot an AVD or attach a device.")
    if preferred:
        if preferred not in serials:
            raise RuntimeError(f"ANDROID_SERIAL={preferred} is not among connected devices: {serials}")
        return preferred
    return serials[0]


def _reset_app_data_android(serial: str) -> None:
    """`adb shell pm clear` — clears the app's data + cache and revokes its
    runtime permissions, without uninstalling the APK (a human-installed build
    survives). The shared keystore is not touched."""
    listed = subprocess.run(
        ["adb", "-s", serial, "shell", "pm", "list", "packages", APP_ID],
        capture_output=True, text=True, check=False,
    )
    installed = any(line.strip() == f"package:{APP_ID}"
                    for line in listed.stdout.splitlines())
    if not installed:
        raise RuntimeError(
            f"Cannot reset {APP_ID}: not installed on {serial} "
            "(is the app installed?). Set reset_app_data: never to skip this."
        )
    subprocess.run(["adb", "-s", serial, "shell", "pm", "clear", APP_ID],
                   capture_output=True, text=True, check=True)


def _build_android_driver(serial: str):
    from appium.options.android import UiAutomator2Options
    options = UiAutomator2Options()
    options.udid = serial
    options.app_package = APP_ID
    activity = app_activity()
    if activity:
        options.app_activity = activity
    options.no_reset = True
    # Leave runtime permissions ungranted: reset_app_data restores the prompt, so
    # the test must dismiss it the same way exploration did (mirrors iOS).
    options.set_capability("appium:appWaitActivity", "*")
    options.set_capability("appium:autoGrantPermissions", False)
    return webdriver.Remote(APPIUM_URL, options=options)


# ------------------------------------------------------------------- dispatchers
def reset_app_data(target: str) -> None:
    """Wipe local app data. `target` is a simulator UDID (iOS) or adb serial (Android)."""
    if PLATFORM == "android":
        _reset_app_data_android(target)
    else:
        _reset_app_data_ios(target)


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
    if PLATFORM == "android":
        target = connected_android_serial()
        if reset_app_data_enabled():
            reset_app_data(target)
        drv = _build_android_driver(target)
    else:
        target = booted_simulator_udid()
        if reset_app_data_enabled():
            reset_app_data(target)
        drv = _build_ios_driver(target)
    # Cold-start the app so every session begins from a deterministic state.
    drv.terminate_app(APP_ID)
    drv.activate_app(APP_ID)
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
