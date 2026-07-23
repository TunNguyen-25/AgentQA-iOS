"""Tests for the scaffold conftest's reset-app-data policy and wipe guard.

conftest.py imports appium/selenium at module load and resolves the platform +
app id at import time, so it is loaded here from a temp copy of the real layout
(<repo>/.agentqa/config.yml next to <repo>/<test_dir>/conftest.py) with the
third-party imports stubbed. Covers both platforms: iOS (simctl container wipe)
and Android (`adb shell pm clear`).
"""
import importlib.util
import shutil
import sys
import types
from pathlib import Path

import pytest

SCAFFOLD = Path(__file__).resolve().parent.parent / "assets" / "scaffold"


def _stub_third_party(monkeypatch):
    appium = types.ModuleType("appium")
    appium.webdriver = types.SimpleNamespace(Remote=lambda *a, **k: None)
    options_ios = types.ModuleType("appium.options.ios")
    options_ios.XCUITestOptions = type("XCUITestOptions", (), {})
    options_android = types.ModuleType("appium.options.android")
    options_android.UiAutomator2Options = type("UiAutomator2Options", (), {})
    events = types.ModuleType("selenium.webdriver.support.events")
    events.AbstractEventListener = type("AbstractEventListener", (), {})
    events.EventFiringWebDriver = type("EventFiringWebDriver", (), {})
    for name, mod in {
        "appium": appium,
        "appium.options": types.ModuleType("appium.options"),
        "appium.options.ios": options_ios,
        "appium.options.android": options_android,
        "selenium": types.ModuleType("selenium"),
        "selenium.webdriver": types.ModuleType("selenium.webdriver"),
        "selenium.webdriver.support": types.ModuleType("selenium.webdriver.support"),
        "selenium.webdriver.support.events": events,
    }.items():
        monkeypatch.setitem(sys.modules, name, mod)
    monkeypatch.syspath_prepend(str(SCAFFOLD))  # for `import runbook`


def load_conftest(monkeypatch, tmp_path, config_body):
    """Copy the scaffold into a fake repo and import its conftest."""
    _stub_third_party(monkeypatch)
    repo = tmp_path / "repo"
    (repo / ".agentqa").mkdir(parents=True)
    (repo / ".agentqa" / "config.yml").write_text(config_body, encoding="utf-8")
    tests_dir = repo / "AutomationTests"
    tests_dir.mkdir()
    shutil.copy(SCAFFOLD / "conftest.py", tests_dir / "conftest.py")
    spec = importlib.util.spec_from_file_location("scaffold_conftest", tests_dir / "conftest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE_CONFIG = 'bundle_id: com.example.app   # app under test\n'
ANDROID_CONFIG = 'platform: android\napp_package: com.example.app   # app under test\n'


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Keep leaked AGENTQA_* env out of the import-time platform/app resolution."""
    for var in ("AGENTQA_PLATFORM", "AGENTQA_BUNDLE_ID", "AGENTQA_APP_PACKAGE",
                "AGENTQA_APP_ACTIVITY", "AGENTQA_RESET_APP_DATA"):
        monkeypatch.delenv(var, raising=False)


# --------------------------------------------------------------------------- iOS
def test_reset_defaults_to_always_when_unset(monkeypatch, tmp_path):
    conftest = load_conftest(monkeypatch, tmp_path, BASE_CONFIG)
    assert conftest.platform() == "ios"
    assert conftest.BUNDLE_ID == "com.example.app"
    assert conftest.APP_ID == "com.example.app"
    assert conftest.reset_app_data_enabled() is True


def test_reset_never_in_config_disables_it(monkeypatch, tmp_path):
    conftest = load_conftest(monkeypatch, tmp_path, BASE_CONFIG + "reset_app_data: never\n")
    assert conftest.reset_app_data_enabled() is False


def test_env_var_overrides_config(monkeypatch, tmp_path):
    conftest = load_conftest(monkeypatch, tmp_path, BASE_CONFIG + "reset_app_data: never\n")
    monkeypatch.setenv("AGENTQA_RESET_APP_DATA", "always")
    assert conftest.reset_app_data_enabled() is True
    monkeypatch.setenv("AGENTQA_RESET_APP_DATA", "never")
    assert conftest.reset_app_data_enabled() is False


def test_config_value_strips_comments_and_quotes(monkeypatch, tmp_path):
    conftest = load_conftest(
        monkeypatch, tmp_path, 'bundle_id: "com.example.app"   # quoted\nreset_app_data: always  # trailing\n'
    )
    assert conftest.config_value("bundle_id") == "com.example.app"
    assert conftest.config_value("reset_app_data") == "always"
    assert conftest.config_value("not_a_key") == ""


def _fake_simctl(container_stdout, returncode=0, calls=None):
    def run(cmd, **kwargs):
        if calls is not None:
            calls.append(cmd)
        if "get_app_container" in cmd:
            return types.SimpleNamespace(stdout=container_stdout, returncode=returncode)
        return types.SimpleNamespace(stdout="", returncode=0)
    return run


def test_reset_empties_the_data_container(monkeypatch, tmp_path):
    conftest = load_conftest(monkeypatch, tmp_path, BASE_CONFIG)
    container = tmp_path / "Containers" / "Data" / "Application" / "ABC"
    (container / "Library" / "Preferences").mkdir(parents=True)
    (container / "Library" / "Preferences" / "com.example.app.plist").write_text("prefs")
    (container / "Documents").mkdir()
    (container / "loose.txt").write_text("x")

    calls = []
    monkeypatch.setattr(conftest.subprocess, "run", _fake_simctl(f"{container}\n", calls=calls))
    conftest.reset_app_data("SIM-UDID")

    assert container.is_dir() and list(container.iterdir()) == []
    assert ["xcrun", "simctl", "terminate", "SIM-UDID", "com.example.app"] == calls[0]
    assert ["xcrun", "simctl", "privacy", "SIM-UDID", "reset", "all", "com.example.app"] == calls[-1]


def test_reset_refuses_a_path_that_is_not_a_data_container(monkeypatch, tmp_path):
    conftest = load_conftest(monkeypatch, tmp_path, BASE_CONFIG)
    victim = tmp_path / "not-a-container"
    victim.mkdir()
    (victim / "precious.txt").write_text("keep me")

    monkeypatch.setattr(conftest.subprocess, "run", _fake_simctl(f"{victim}\n"))
    with pytest.raises(RuntimeError, match="Cannot reset"):
        conftest.reset_app_data("SIM-UDID")
    assert (victim / "precious.txt").exists()


def test_reset_refuses_when_app_is_not_installed(monkeypatch, tmp_path):
    conftest = load_conftest(monkeypatch, tmp_path, BASE_CONFIG)
    monkeypatch.setattr(conftest.subprocess, "run", _fake_simctl("", returncode=1))
    with pytest.raises(RuntimeError, match="Cannot reset"):
        conftest.reset_app_data("SIM-UDID")


# ----------------------------------------------------------------------- Android
def test_android_resolves_platform_and_package(monkeypatch, tmp_path):
    conftest = load_conftest(monkeypatch, tmp_path, ANDROID_CONFIG)
    assert conftest.platform() == "android"
    assert conftest.APP_ID == "com.example.app"
    assert conftest.BUNDLE_ID == "com.example.app"   # alias tracks APP_ID
    assert conftest.reset_app_data_enabled() is True


def _fake_adb(installed_lines, calls=None):
    """Fake adb: `pm list packages` returns installed_lines; other calls are ok."""
    def run(cmd, **kwargs):
        if calls is not None:
            calls.append(cmd)
        if "list" in cmd and "packages" in cmd:
            return types.SimpleNamespace(stdout=installed_lines, returncode=0)
        return types.SimpleNamespace(stdout="", returncode=0)
    return run


def test_android_reset_calls_pm_clear(monkeypatch, tmp_path):
    conftest = load_conftest(monkeypatch, tmp_path, ANDROID_CONFIG)
    calls = []
    monkeypatch.setattr(conftest.subprocess, "run",
                        _fake_adb("package:com.example.app\n", calls=calls))
    conftest.reset_app_data("emulator-5554")
    assert ["adb", "-s", "emulator-5554", "shell", "pm", "clear", "com.example.app"] in calls


def test_android_reset_refuses_when_not_installed(monkeypatch, tmp_path):
    conftest = load_conftest(monkeypatch, tmp_path, ANDROID_CONFIG)
    monkeypatch.setattr(conftest.subprocess, "run", _fake_adb(""))
    with pytest.raises(RuntimeError, match="Cannot reset"):
        conftest.reset_app_data("emulator-5554")


def test_android_reset_matches_package_exactly(monkeypatch, tmp_path):
    """`pm list packages <pkg>` prefix-matches, so a lookalike must NOT count as installed."""
    conftest = load_conftest(monkeypatch, tmp_path, ANDROID_CONFIG)
    calls = []
    monkeypatch.setattr(conftest.subprocess, "run",
                        _fake_adb("package:com.example.app2\n", calls=calls))
    with pytest.raises(RuntimeError, match="Cannot reset"):
        conftest.reset_app_data("emulator-5554")
    assert not any("clear" in c for c in calls)  # never cleared the wrong package


def test_env_platform_override_forces_android(monkeypatch, tmp_path):
    """AGENTQA_PLATFORM + AGENTQA_APP_PACKAGE drive dispatch even without config keys."""
    monkeypatch.setenv("AGENTQA_PLATFORM", "android")
    monkeypatch.setenv("AGENTQA_APP_PACKAGE", "com.override.app")
    conftest = load_conftest(monkeypatch, tmp_path, "test_dir: AutomationTests\n")
    assert conftest.platform() == "android"
    assert conftest.APP_ID == "com.override.app"
