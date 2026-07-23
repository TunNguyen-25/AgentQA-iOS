# Tests and page objects written

## `AutomationTests/pages/base_page.py`

```python
"""Shared Appium helpers for the MyTV page objects.

Every locator in this package is an accessibility identifier following the
project's `identifier_convention: screen_element_type` (see
`.agentqa/config.yml`). Identifiers are assigned in the Swift sources, so a
locator that stops resolving means the app code changed, not the copy.
"""
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import (
    NoAlertPresentException,
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

DEFAULT_TIMEOUT = 20


class BasePage:
    """Thin wrapper over the driver: waits, taps, typing, alert handling."""

    def __init__(self, driver):
        self.driver = driver

    # -- lookups -----------------------------------------------------------
    def _wait(self, timeout=DEFAULT_TIMEOUT):
        return WebDriverWait(self.driver, timeout)

    def element(self, identifier, timeout=DEFAULT_TIMEOUT):
        return self._wait(timeout).until(
            EC.presence_of_element_located(
                (AppiumBy.ACCESSIBILITY_ID, identifier))
        )

    def is_displayed(self, identifier, timeout=DEFAULT_TIMEOUT):
        try:
            return self.element(identifier, timeout).is_displayed()
        except (TimeoutException, NoSuchElementException):
            return False

    # -- interactions ------------------------------------------------------
    def tap(self, identifier, timeout=DEFAULT_TIMEOUT):
        element = self._wait(timeout).until(
            EC.element_to_be_clickable(
                (AppiumBy.ACCESSIBILITY_ID, identifier))
        )
        element.click()
        return element

    def type_text(self, identifier, text, timeout=DEFAULT_TIMEOUT):
        element = self.element(identifier, timeout)
        element.click()
        element.clear()
        element.send_keys(text)
        return element

    # -- system (SpringBoard) alerts ---------------------------------------
    def deny_system_alert(self, timeout=5):
        """Dismiss the iOS permission prompt with the *deny* button.

        `reset_app_data: always` wipes the app's privacy grants, so the
        notification prompt is shown on every session's first launch. The suite
        must run with notifications OFF, otherwise a banner can land on top of
        the UI mid-test, so this always takes the deny branch — never "Allow".

        The prompt belongs to SpringBoard, not to the app under test, so it is
        located by its system label rather than by an app identifier.
        """
        deny_predicate = (
            "type == 'XCUIElementTypeButton' AND "
            "(name == \"Don't Allow\" OR name == 'Không cho phép')"
        )
        try:
            button = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable(
                    (AppiumBy.IOS_PREDICATE, deny_predicate))
            )
            button.click()
            return True
        except (TimeoutException, NoSuchElementException, WebDriverException):
            pass
        # Fallback: on some XCUITest versions the prompt is only reachable
        # through the alert API, where dismiss() maps to the deny button.
        try:
            self.driver.switch_to.alert.dismiss()
            return True
        except (NoAlertPresentException, TimeoutException, WebDriverException):
            return False
```

## `AutomationTests/pages/home_page.py`

```python
"""MainTabBarController — the home screen reached after a successful login."""
from pages.base_page import BasePage


class HomePage(BasePage):

    HOME_TAB = "home_home_button"
    LIVE_TAB = "home_live_button"
    PROFILE_TAB = "home_profile_button"

    def wait_until_loaded(self, timeout=30):
        """Wait for the tab bar. Timeout is generous: submit triggers a real
        POST /auth/login round trip before AppRouter swaps the root VC."""
        self.element(self.HOME_TAB, timeout)
        return self

    def tab_bar_is_visible(self):
        """All three bottom tabs present: Trang chủ / Truyền hình / Cá nhân.

        The live tab is the discriminator — a guest session
        (`presentHome(guest: true)`) renders the same MainTabBarController but
        without it, so requiring all three proves an authenticated session.
        """
        return all(
            self.is_displayed(tab, timeout=5)
            for tab in (self.HOME_TAB, self.LIVE_TAB, self.PROFILE_TAB)
        )
```

## `AutomationTests/pages/introduction_page.py`

```python
"""IntroductionContentViewController — the first screen after launch."""
from pages.base_page import BasePage
from pages.login_page import LoginPage


class IntroductionPage(BasePage):

    LOGIN_BUTTON = "intro_login_button"
    GUEST_BUTTON = "intro_guest_button"

    def wait_until_loaded(self, timeout=30):
        # viewDidLoad calls NotificationPermission.requestIfNeeded(), so the
        # SpringBoard prompt covers this screen on a freshly reset install.
        self.deny_system_alert()
        self.element(self.LOGIN_BUTTON, timeout)
        return self

    def go_to_login(self):
        """Tap 'Đăng nhập ngay' and hand over to the login form."""
        self.tap(self.LOGIN_BUTTON)
        return LoginPage(self.driver)
```

## `AutomationTests/pages/login_page.py`

```python
"""LoginViewController / LoginView — the username + password form."""
from pages.base_page import BasePage
from pages.home_page import HomePage


class LoginPage(BasePage):

    USERNAME_FIELD = "login_username_field"
    PASSWORD_FIELD = "login_password_field"
    TERMS_CHECKBOX = "login_terms_checkbox"
    TERMS_LINK = "login_terms_link"
    SUBMIT_BUTTON = "login_submit_button"
    ERROR_LABEL = "login_error_label"

    def wait_until_loaded(self, timeout=20):
        self.element(self.USERNAME_FIELD, timeout)
        return self

    def enter_credentials(self, username, password):
        self.type_text(self.USERNAME_FIELD, username)
        self.type_text(self.PASSWORD_FIELD, password)
        return self

    def accept_terms(self):
        """Tick the terms box.

        Required: LoginView keeps `btnLogin` disabled until `termsAccepted` is
        true, and submitting without it only renders the inline error
        "Vui lòng đồng ý với điều khoản sử dụng" — it never calls AuthService.
        The box is a UIImageView with a tap gesture (not a UISwitch/UIButton),
        so it must be tapped by its own identifier; tapping TERMS_LINK instead
        opens the WKWebView terms sheet and does not tick anything.
        """
        self.tap(self.TERMS_CHECKBOX)
        return self

    def submit(self):
        self.tap(self.SUBMIT_BUTTON)
        return HomePage(self.driver)

    def login(self, username, password):
        """Full happy path: credentials -> terms -> submit."""
        self.enter_credentials(username, password)
        self.accept_terms()
        return self.submit()

    def error_message(self, timeout=5):
        """Inline error text, or None when no error is shown."""
        try:
            return self.element(self.ERROR_LABEL, timeout).text
        except Exception:
            return None
```

## `AutomationTests/tests/test_login.py`

```python
"""Login flow: the QA account signs in and lands on the home screen.

Flow verified on the simulator (iPhone 16 Pro, iOS 18.5):
  launch -> SpringBoard notification prompt (denied)
         -> IntroductionContentViewController ("Đăng nhập ngay")
         -> LoginViewController (username, password, terms checkbox, submit)
         -> MainTabBarController (Trang chủ / Truyền hình / Cá nhân)
"""
import os

import pytest

from pages.introduction_page import IntroductionPage

USERNAME = os.environ.get("APP_TEST_USERNAME", "")
PASSWORD = os.environ.get("APP_TEST_PASSWORD", "")

pytestmark = pytest.mark.skipif(
    not (USERNAME and PASSWORD),
    reason="QA credentials not exported (APP_TEST_USERNAME / APP_TEST_PASSWORD)",
)


def test_qa_account_login_lands_on_home(driver):
    """Happy path: valid credentials + accepted terms -> home tab bar."""
    intro = IntroductionPage(driver).wait_until_loaded()

    login = intro.go_to_login().wait_until_loaded()
    home = login.login(USERNAME, PASSWORD)

    home.wait_until_loaded()
    assert home.tab_bar_is_visible(), (
        "expected the home tab bar (Trang chủ / Truyền hình / Cá nhân) after "
        "logging in with the QA account"
    )
```
