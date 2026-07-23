# Tests and page objects written

## `AutomationTests/pages/base_page.py`

```python
"""Shared behaviour for the MyTV page objects.

Locators are the app's own accessibility identifiers (see
`.agentqa/memory/screens/*.md`), all verified against the live Appium
hierarchy. Never locate app-owned UI by label — labels are Vietnamese copy and
change without notice.
"""
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait

# Mirrors the implicit wait conftest.py sets on the session driver.
IMPLICIT_WAIT = 10
DEFAULT_TIMEOUT = 15


class BasePage:
    def __init__(self, driver):
        self.driver = driver

    # --- element access -------------------------------------------------
    def find(self, identifier):
        return self.driver.find_element(AppiumBy.ACCESSIBILITY_ID, identifier)

    def wait_for(self, identifier, timeout=DEFAULT_TIMEOUT):
        return WebDriverWait(self.driver, timeout).until(
            lambda d: d.find_element(AppiumBy.ACCESSIBILITY_ID, identifier)
        )

    def is_present(self, identifier, timeout=DEFAULT_TIMEOUT):
        try:
            self.wait_for(identifier, timeout)
            return True
        except (TimeoutException, NoSuchElementException):
            return False

    def is_absent(self, identifier):
        """Immediate presence check — the implicit wait would otherwise make
        every "this must NOT be here" assertion cost a full timeout."""
        self.driver.implicitly_wait(0)
        try:
            self.driver.find_element(AppiumBy.ACCESSIBILITY_ID, identifier)
            return False
        except NoSuchElementException:
            return True
        finally:
            self.driver.implicitly_wait(IMPLICIT_WAIT)

    def label_of(self, identifier):
        element = self.wait_for(identifier)
        return element.get_attribute("label") or element.text
```

## `AutomationTests/pages/home_page.py`

```python
"""MainTabBarController — the post-login landing surface."""
from .base_page import BasePage


class HomePage(BasePage):
    HOME_TAB = "home_home_tab"
    LIVE_TAB = "home_live_tab"
    PROFILE_TAB = "home_profile_tab"

    TAB_BAR = (HOME_TAB, LIVE_TAB, PROFILE_TAB)

    def is_displayed(self):
        return self.is_present(self.HOME_TAB)

    def missing_tabs(self):
        """Tab identifiers that are not in the live hierarchy."""
        return [tab for tab in self.TAB_BAR if not self.is_present(tab, timeout=5)]
```

## `AutomationTests/pages/intro_page.py`

```python
"""IntroductionContentViewController — the logged-out entry point."""
from .base_page import BasePage
from .login_page import LoginPage


class IntroPage(BasePage):
    LOGIN_BUTTON = "login_intro_login_button"
    FREE_BUTTON = "login_intro_free_button"

    def is_displayed(self, timeout=None):
        if timeout is None:
            return self.is_present(self.LOGIN_BUTTON)
        return self.is_present(self.LOGIN_BUTTON, timeout=timeout)

    def tap_login(self):
        self.wait_for(self.LOGIN_BUTTON).click()
        return LoginPage(self.driver)

    def tap_watch_free(self):
        self.wait_for(self.FREE_BUTTON).click()
```

## `AutomationTests/pages/login_page.py`

```python
"""LoginView / LoginViewController — username, password, terms, submit.

Live-hierarchy facts this page object relies on (verified 2026-07-23):
- `login_submit_button` reports `enabled=true` even while the terms box is
  unticked, so the checkbox state can NOT be read off the button.
- `login_error_label` is absent from the hierarchy until `showError(_:)` runs.
"""
from .base_page import BasePage


class LoginPage(BasePage):
    USERNAME_FIELD = "login_username_field"
    PASSWORD_FIELD = "login_password_field"
    TERMS_CHECKBOX = "login_terms_checkbox"
    TERMS_LINK = "login_terms_link"
    SUBMIT_BUTTON = "login_submit_button"
    ERROR_LABEL = "login_error_label"

    # Inline error copy, read off the live hierarchy.
    WRONG_CREDENTIALS_ERROR = "Sai tên đăng nhập hoặc mật khẩu"
    TERMS_REQUIRED_ERROR = "Vui lòng đồng ý với điều khoản sử dụng"

    def is_displayed(self):
        return self.is_present(self.SUBMIT_BUTTON)

    def enter_username(self, username):
        field = self.wait_for(self.USERNAME_FIELD)
        field.clear()
        field.send_keys(username)
        return self

    def enter_password(self, password):
        field = self.wait_for(self.PASSWORD_FIELD)
        field.clear()
        field.send_keys(password)
        return self

    def accept_terms(self):
        self.wait_for(self.TERMS_CHECKBOX).click()
        return self

    def submit(self):
        self.wait_for(self.SUBMIT_BUTTON).click()
        return self

    def login(self, username, password, accept_terms=True):
        self.enter_username(username)
        self.enter_password(password)
        if accept_terms:
            self.accept_terms()
        return self.submit()

    # --- error state ----------------------------------------------------
    def has_error(self):
        return self.is_present(self.ERROR_LABEL)

    def has_no_error(self):
        return self.is_absent(self.ERROR_LABEL)

    def error_text(self):
        return self.label_of(self.ERROR_LABEL)
```

## `AutomationTests/tests/test_login.py`

```python
"""UI tests for the login flow.

Assertion under test (confirmed with the reviewer): a valid username and
password plus a ticked terms checkbox land the user on the home screen with the
bottom tab bar visible.

Failure criteria (confirmed with the reviewer): the app stays on the login
screen and shows the inline error "Sai tên đăng nhập hoặc mật khẩu" — it must
not bounce back to intro and must not show a modal.

`reset_app_data: always`, so the session starts on a wiped app and every test
relaunches to the logged-out intro screen and builds its own state.
"""
import os

import pytest
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import NoSuchElementException

from conftest import BUNDLE_ID
from pages.base_page import IMPLICIT_WAIT
from pages.home_page import HomePage
from pages.intro_page import IntroPage
from pages.login_page import LoginPage

USERNAME = os.environ.get("APP_TEST_USERNAME")
PASSWORD = os.environ.get("APP_TEST_PASSWORD")

requires_credentials = pytest.mark.skipif(
    not (USERNAME and PASSWORD),
    reason="set APP_TEST_USERNAME and APP_TEST_PASSWORD to run the login tests",
)

# Reviewer's decision for the one known blocker: the SpringBoard notifications
# alert is dismissed with "Don't Allow". It is owned by SpringBoard, not by the
# app, and only appears on the first launch after the privacy grants are reset.
NOTIFICATIONS_ALERT_DISMISS = "Don't Allow"


def _dismiss_notifications_alert(driver):
    driver.implicitly_wait(0)
    try:
        driver.find_element(AppiumBy.ACCESSIBILITY_ID,
                            NOTIFICATIONS_ALERT_DISMISS).click()
    except NoSuchElementException:
        pass  # already answered on an earlier launch in this session
    finally:
        driver.implicitly_wait(IMPLICIT_WAIT)


def _modal_is_showing(driver):
    driver.implicitly_wait(0)
    try:
        return bool(driver.find_elements(AppiumBy.CLASS_NAME,
                                         "XCUIElementTypeAlert"))
    finally:
        driver.implicitly_wait(IMPLICIT_WAIT)


@pytest.fixture
def intro(driver):
    """Relaunch into a logged-out app so tests do not depend on each other.

    No session is persisted (AppRouter only swaps the in-memory root view
    controller), so terminate + activate always returns to the intro screen.
    """
    driver.terminate_app(BUNDLE_ID)
    driver.activate_app(BUNDLE_ID)
    _dismiss_notifications_alert(driver)
    page = IntroPage(driver)
    assert page.is_displayed(), "app did not land on the intro screen after launch"
    return page


@requires_credentials
def test_valid_credentials_land_on_home(driver, intro):
    login = intro.tap_login()
    assert login.is_displayed(), "tapping 'Đăng nhập ngay' did not open the login form"

    login.login(USERNAME, PASSWORD, accept_terms=True)

    home = HomePage(driver)
    assert home.is_displayed(), (
        "login with valid credentials did not land on the home screen"
    )
    assert home.missing_tabs() == [], (
        f"home tab bar is incomplete: missing {home.missing_tabs()}"
    )


@requires_credentials
def test_wrong_password_shows_inline_error_and_stays_on_login(driver, intro):
    login = intro.tap_login()
    login.login(USERNAME, "definitely-not-the-password", accept_terms=True)

    assert login.has_error(), "wrong password did not surface the inline error label"
    assert login.error_text() == LoginPage.WRONG_CREDENTIALS_ERROR
    # Stays on login: neither the home tab bar nor the intro screen appears.
    assert login.is_displayed(), "app left the login screen after a failed login"
    assert login.is_absent(HomePage.HOME_TAB), "a failed login reached the home screen"
    assert login.is_absent(IntroPage.LOGIN_BUTTON), (
        "a failed login bounced back to the intro screen"
    )
    assert not _modal_is_showing(driver), "a failed login showed a modal alert"


@requires_credentials
def test_submit_without_accepting_terms_shows_terms_error(driver, intro):
    login = intro.tap_login()
    login.login(USERNAME, PASSWORD, accept_terms=False)

    assert login.has_error(), "submitting without the terms box showed no error"
    assert login.error_text() == LoginPage.TERMS_REQUIRED_ERROR
    assert login.is_absent(HomePage.HOME_TAB), (
        "login succeeded without the terms checkbox ticked"
    )
```
