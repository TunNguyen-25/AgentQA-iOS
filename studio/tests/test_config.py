import textwrap
from pathlib import Path

from studio.config import load_config, config_summary


def _write_cfg(tmp_path: Path, body: str) -> Path:
    d = tmp_path / ".agentqa"
    d.mkdir(parents=True)
    (d / "config.yml").write_text(textwrap.dedent(body))
    return tmp_path


IOS_CFG = """\
    platform: ios
    bundle_id: com.vnpt.media.mobileb2c
    test_dir: AutomationTests
    build:
      policy: human
      note: "Manual builds required"
    reset_app_data: always
    credentials:
      username_env: APP_TEST_USERNAME
      password_env: APP_TEST_PASSWORD
    identifier_convention: screen_element_type
    appium:
      port: 4723
"""


def test_load_config_reads_nested_scalars(tmp_path):
    root = _write_cfg(tmp_path, IOS_CFG)
    cfg = load_config(root)
    assert cfg["platform"] == "ios"
    assert cfg["bundle_id"] == "com.vnpt.media.mobileb2c"
    assert cfg["build"]["policy"] == "human"
    assert cfg["credentials"]["username_env"] == "APP_TEST_USERNAME"
    assert cfg["appium"]["port"] == 4723


def test_load_config_missing_raises(tmp_path):
    try:
        load_config(tmp_path)
        assert False, "expected FileNotFoundError"
    except FileNotFoundError:
        pass


def test_summary_ios(tmp_path):
    root = _write_cfg(tmp_path, IOS_CFG)
    s = config_summary(load_config(root))
    assert s["platform"] == "ios"
    assert s["app_id"] == "com.vnpt.media.mobileb2c"
    assert s["test_dir"] == "AutomationTests"
    assert s["build_policy"] == "human"
    assert s["appium_port"] == 4723
    assert s["cred_env"] == {"username": "APP_TEST_USERNAME", "password": "APP_TEST_PASSWORD"}


def test_summary_android_uses_app_package(tmp_path):
    root = _write_cfg(tmp_path, """\
        platform: android
        app_package: com.example.app
        app_activity: .MainActivity
        test_dir: AutomationTests
        build:
          policy: agent
        reset_app_data: always
        identifier_convention: screen_element_type
    """)
    s = config_summary(load_config(root))
    assert s["platform"] == "android"
    assert s["app_id"] == "com.example.app"
    assert s["appium_port"] == 4723  # default when appium block absent
