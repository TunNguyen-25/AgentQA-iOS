from pathlib import Path
from unittest import mock

from studio import rig

IOS = {"platform": "ios", "app_id": "com.acme.app", "appium_port": 4723}


def test_ios_all_green(tmp_path):
    (tmp_path / ".codegraph").mkdir()
    def fake_run(cmd):
        joined = " ".join(cmd)
        if "list" in cmd and "devices" in cmd:
            return (0, "iPhone 15 (ABC) (Booted)")
        if "listapps" in cmd:
            return (0, "com.acme.app = { ... }")
        if cmd[0] == "nc":
            return (0, "")
        return (1, "")
    with mock.patch.object(rig, "_run", side_effect=fake_run):
        out = rig.check_rig(IOS, tmp_path)
    assert out == {"simulator": True, "app_installed": True, "appium": True, "codegraph": True}


def test_ios_appium_down_and_no_codegraph(tmp_path):
    def fake_run(cmd):
        if "list" in cmd and "devices" in cmd:
            return (0, "iPhone 15 (ABC) (Booted)")
        if "listapps" in cmd:
            return (0, "com.acme.app = { ... }")
        if cmd[0] == "nc":
            return (1, "")  # appium down
        return (1, "")
    with mock.patch.object(rig, "_run", side_effect=fake_run):
        out = rig.check_rig(IOS, tmp_path)
    assert out["simulator"] is True
    assert out["app_installed"] is True
    assert out["appium"] is False
    assert out["codegraph"] is False  # no .codegraph dir


def test_app_not_installed(tmp_path):
    (tmp_path / ".codegraph").mkdir()
    def fake_run(cmd):
        if "list" in cmd and "devices" in cmd:
            return (0, "Booted")
        if "listapps" in cmd:
            return (0, "com.other.app = {}")  # ours absent
        if cmd[0] == "nc":
            return (0, "")
        return (1, "")
    with mock.patch.object(rig, "_run", side_effect=fake_run):
        out = rig.check_rig(IOS, tmp_path)
    assert out["app_installed"] is False
