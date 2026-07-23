# Tests and page objects written

## `AutomationTests/pages/login_page.py`

```python
"""Page objects for the login flow."""
from appium.webdriver.common.appiumby import AppiumBy


class IntroPage:
    LOGIN_BUTTON = (AppiumBy.ACCESSIBILITY_ID, "login_intro_login_button")

    def __init__(self, driver):
        self.driver = driver

    def tap_login(self):
        self.driver.find_element(*self.LOGIN_BUTTON).click()


class LoginPage:
    USERNAME = (AppiumBy.ACCESSIBILITY_ID, "login_username_field")
    PASSWORD = (AppiumBy.ACCESSIBILITY_ID, "login_password_field")
    TERMS = (AppiumBy.ACCESSIBILITY_ID, "login_terms_checkbox")
    SUBMIT = (AppiumBy.ACCESSIBILITY_ID, "login_submit_button")
    ERROR = (AppiumBy.ACCESSIBILITY_ID, "login_error_label")

    def __init__(self, driver):
        self.driver = driver

    def login(self, username, password):
        self.driver.find_element(*self.USERNAME).send_keys(username)
        self.driver.find_element(*self.PASSWORD).send_keys(password)
        self.driver.find_element(*self.TERMS).click()
        self.driver.find_element(*self.SUBMIT).click()

    def error_text(self):
        return self.driver.find_element(*self.ERROR).text


class HomePage:
    HOME_TAB = (AppiumBy.ACCESSIBILITY_ID, "home_home_tab")

    def __init__(self, driver):
        self.driver = driver

    def is_loaded(self):
        return self.driver.find_element(*self.HOME_TAB).is_displayed()
```

## `AutomationTests/tests/test_login.py`

```python
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
    IntroPage(driver).tap_login()
    LoginPage(driver).login(username, password)
    assert HomePage(driver).is_loaded(), "expected the home tab bar after login"


def test_login_rejects_wrong_password(driver, credentials):
    """A wrong password keeps the user on the login screen with an inline error."""
    username, _ = credentials
    IntroPage(driver).tap_login()
    page = LoginPage(driver)
    page.login(username, "definitely-not-the-password")
    assert page.error_text() == "Sai tên đăng nhập hoặc mật khẩu"
```
