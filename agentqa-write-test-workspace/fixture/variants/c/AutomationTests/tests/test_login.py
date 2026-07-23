"""Login flow UI tests."""
import os

import pytest

from pages.login_page import HomePage, IntroPage, LoginPage


@pytest.fixture
def credentials():
    user = os.environ.get("APP_TEST_USERNAME")
    pwd = os.environ.get("APP_TEST_PASSWORD")
    if not user or not pwd:
        pytest.skip("APP_TEST_USERNAME / APP_TEST_PASSWORD not set")
    return user, pwd


def test_login_happy_path(driver, credentials):
    """Valid credentials + accepted terms land the user on the home tab bar."""
    username, password = credentials
    intro = IntroPage(driver)
    intro.dismiss_permission_alert()
    intro.tap_login()
    LoginPage(driver).login(username, password)
    assert HomePage(driver).is_loaded(), "expected the home tab bar after login"


def test_login_rejects_wrong_password(driver, credentials):
    """A wrong password keeps the user on the login screen with an inline error."""
    username, _ = credentials
    intro = IntroPage(driver)
    intro.dismiss_permission_alert()
    intro.tap_login()
    page = LoginPage(driver)
    page.login(username, "definitely-not-the-password")
    assert page.error_text() == "Sai tên đăng nhập hoặc mật khẩu"
