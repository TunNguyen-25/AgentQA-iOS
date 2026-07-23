# Tests and page objects written

## `AutomationTests/pages/base_page.py`

```python
"""Shared page-object helpers.

The session `driver` fixture sets `implicitly_wait(10)`. Mixing that with
explicit waits makes *negative* checks ("this element is gone") cost the full
implicit timeout, so `no_implicit_wait()` turns it off for those.
"""
from contextlib import contextmanager

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import (
    NoAlertPresentException,
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

IMPLICIT_WAIT = 10
DEFAULT_TIMEOUT = 15


class BasePage:
    def __init__(self, driver):
        self.driver = driver

    # --- waiting -----------------------------------------------------------
    def _wait(self, timeout=None):
        return WebDriverWait(self.driver, timeout or DEFAULT_TIMEOUT)

    @contextmanager
    def no_implicit_wait(self):
        """Zero the implicit wait so absence checks fail fast."""
        self.driver.implicitly_wait(0)
        try:
            yield
        finally:
            self.driver.implicitly_wait(IMPLICIT_WAIT)

    # --- element access ----------------------------------------------------
    def element(self, accessibility_id, timeout=None):
        return self._wait(timeout).until(
            EC.presence_of_element_located(
                (AppiumBy.ACCESSIBILITY_ID, accessibility_id)
            ),
            f"element {accessibility_id!r} never appeared",
        )

    def is_visible(self, accessibility_id, timeout=None):
        try:
            self.element(accessibility_id, timeout=timeout)
            return True
        except TimeoutException:
            return False

    def is_absent(self, accessibility_id):
        """True when the element is not in the tree right now."""
        with self.no_implicit_wait():
            try:
                self.driver.find_element(
                    AppiumBy.ACCESSIBILITY_ID, accessibility_id
                )
                return False
            except NoSuchElementException:
                return True

    def text_of(self, accessibility_id, timeout=None):
        el = self.element(accessibility_id, timeout=timeout)
        return el.get_attribute("label") or el.text or ""

    def is_enabled(self, accessibility_id, timeout=None):
        return self.element(accessibility_id, timeout=timeout).get_attribute(
            "enabled"
        ) in ("true", True)

    # --- actions -----------------------------------------------------------
    def tap(self, accessibility_id, timeout=None):
        self.element(accessibility_id, timeout=timeout).click()

    def type_into(self, accessibility_id, text, timeout=None):
        field = self.element(accessibility_id, timeout=timeout)
        field.clear()
        field.send_keys(text)

    # --- system alerts -----------------------------------------------------
    def dismiss_system_alert(self, button_label, timeout=5):
        """Dismiss a SpringBoard alert by button label. False if none showed."""
        try:
            WebDriverWait(self.driver, timeout).until(EC.alert_is_present())
        except TimeoutException:
            return False
        try:
            self.driver.execute_script(
                "mobile: alert", {"action": "accept", "buttonLabel": button_label}
            )
        except WebDriverException:
            # Fall back to the alert's cancel button.
            self.driver.switch_to.alert.dismiss()
        return True

    def has_alert(self):
        with self.no_implicit_wait():
            try:
                _ = self.driver.switch_to.alert.text
                return True
            except (NoAlertPresentException, WebDriverException):
                return False
```

## `AutomationTests/pages/home_page.py`

```python
"""MainTabBarController — the post-login landing surface (native UIKit).

Reached by `AppRouter.presentHome` swapping the window's root view controller,
so arriving here means the login actually succeeded.
"""
from .base_page import BasePage


class HomePage(BasePage):
    HOME_TAB = "home_home_tab"
    LIVE_TAB = "home_live_tab"
    PROFILE_TAB = "home_profile_tab"

    TAB_LABELS = {
        HOME_TAB: "Trang chủ",
        LIVE_TAB: "Truyền hình",
        PROFILE_TAB: "Cá nhân",
    }

    def is_loaded(self, timeout=None):
        return self.is_visible(self.HOME_TAB, timeout=timeout)

    def visible_tab_labels(self):
        return {tab: self.text_of(tab) for tab in self.TAB_LABELS}
```

## `AutomationTests/pages/intro_page.py`

```python
"""IntroductionContentViewController — the launch screen (native UIKit).

Requests notification permission in `viewDidLoad`, so on a launch after a
privacy wipe a SpringBoard alert covers this screen. The reviewer's answer for
that alert is "Don't Allow".
"""
from .base_page import BasePage

PERMISSION_ALERT_BUTTON = "Don't Allow"


class IntroPage(BasePage):
    LOGIN_BUTTON = "login_intro_login_button"
    FREE_BUTTON = "login_intro_free_button"

    def dismiss_notification_permission(self):
        """Tap 'Don't Allow' if the permission alert is up. Safe to always call."""
        return self.dismiss_system_alert(PERMISSION_ALERT_BUTTON)

    def is_loaded(self):
        return self.is_visible(self.LOGIN_BUTTON)

    def go_to_login(self):
        self.tap(self.LOGIN_BUTTON)
        from .login_page import LoginPage

        return LoginPage(self.driver)
```

## `AutomationTests/pages/login_page.py`

```python
"""LoginView / LoginViewController — the login form (native UIKit).

`login_error_label` is absent from the tree until `showError(_:)` runs, so its
presence is a reliable signal that submit was rejected.
"""
from .base_page import BasePage

WRONG_CREDENTIALS_ERROR = "Sai tên đăng nhập hoặc mật khẩu"
TERMS_REQUIRED_ERROR = "Vui lòng đồng ý với điều khoản sử dụng"


class LoginPage(BasePage):
    USERNAME_FIELD = "login_username_field"
    PASSWORD_FIELD = "login_password_field"
    TERMS_CHECKBOX = "login_terms_checkbox"
    TERMS_LINK = "login_terms_link"
    SUBMIT_BUTTON = "login_submit_button"
    ERROR_LABEL = "login_error_label"

    def is_loaded(self):
        return self.is_visible(self.SUBMIT_BUTTON)

    def enter_username(self, username):
        self.type_into(self.USERNAME_FIELD, username)
        return self

    def enter_password(self, password):
        self.type_into(self.PASSWORD_FIELD, password)
        return self

    def accept_terms(self):
        """Tick 'Tôi đồng ý với điều khoản sử dụng'. The checkbox is a
        UIImageView with a tap gesture, so it surfaces as XCUIElementTypeOther."""
        self.tap(self.TERMS_CHECKBOX)
        return self

    def submit(self):
        self.tap(self.SUBMIT_BUTTON)
        return self

    def login(self, username, password, accept_terms=True):
        self.enter_username(username)
        self.enter_password(password)
        if accept_terms:
            self.accept_terms()
        return self.submit()

    # --- assertions support -------------------------------------------------
    def error_text(self, timeout=None):
        return self.text_of(self.ERROR_LABEL, timeout=timeout)

    def has_error(self, timeout=5):
        return self.is_visible(self.ERROR_LABEL, timeout=timeout)

    def has_no_error(self):
        return self.is_absent(self.ERROR_LABEL)
```

## `AutomationTests/tests/test_login.py`

```python
"""Login flow: intro → login form → home tab bar.

Success (per the session requirement): the user enters a valid username and
password, ticks the terms checkbox, taps "Đăng nhập", and lands on the home
screen with the bottom tab bar visible.

Failure: the app stays on the login screen and shows the inline error
"Sai tên đăng nhập hoặc mật khẩu" — it must not bounce back to intro and must
not show a modal.

All identifiers used here were verified against the built app on the simulator
on 2026-07-23.
"""
import pytest

from pages.home_page import HomePage
from pages.login_page import WRONG_CREDENTIALS_ERROR, LoginPage


@pytest.mark.smoke
def test_login_with_valid_credentials_lands_on_home(driver, intro, credentials):
    username, password = credentials

    assert intro.is_loaded(), "intro screen did not load after launch"

    login = intro.go_to_login()
    assert login.is_loaded(), "login form did not open from the intro screen"

    login.login(username, password, accept_terms=True)

    home = HomePage(driver)
    assert home.is_loaded(), (
        "expected MainTabBarController after a valid login, but the home tab "
        "never appeared"
    )
    assert home.visible_tab_labels() == {
        HomePage.HOME_TAB: "Trang chủ",
        HomePage.LIVE_TAB: "Truyền hình",
        HomePage.PROFILE_TAB: "Cá nhân",
    }, "the bottom tab bar is not showing the three expected tabs"


def test_login_with_wrong_credentials_shows_inline_error(driver, intro):
    login = intro.go_to_login()
    assert login.is_loaded(), "login form did not open from the intro screen"

    login.login("no.such.user@example.com", "WrongPass!123", accept_terms=True)

    assert login.has_error(), "no inline error appeared for wrong credentials"
    assert login.error_text() == WRONG_CREDENTIALS_ERROR

    # Stays on the login screen — no bounce back to intro, no modal.
    assert login.is_visible(LoginPage.SUBMIT_BUTTON), "left the login screen"
    assert login.is_absent(intro.LOGIN_BUTTON), "bounced back to the intro screen"
    assert not login.has_alert(), "an unexpected modal/alert was shown"

    home = HomePage(driver)
    assert home.is_absent(HomePage.HOME_TAB), "reached home with wrong credentials"
```
