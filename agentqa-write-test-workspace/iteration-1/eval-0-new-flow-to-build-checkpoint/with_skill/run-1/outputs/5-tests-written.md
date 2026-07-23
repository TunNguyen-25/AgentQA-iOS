# Tests and page objects written

## `AutomationTests/pages/base_page.py`

```python
"""Shared Appium helpers for the MyTV page objects.

Locators are accessibility identifiers added to the app source (see
`.agentqa/memory/screens/*.md` for the identifier → symbol map and the
verification dates). Only UI the app does not own — e.g. the SpringBoard
notification alert and the terms sheet's "Xong" bar button — is matched by its
visible name.
"""
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait

#: Mirrors the implicit wait the `driver` fixture in conftest.py sets.
DEFAULT_IMPLICIT_WAIT = 10


class BasePage:
    def __init__(self, driver):
        self.driver = driver

    def find(self, accessibility_id):
        return self.driver.find_element(AppiumBy.ACCESSIBILITY_ID, accessibility_id)

    def wait_for(self, accessibility_id, timeout=DEFAULT_IMPLICIT_WAIT):
        """Wait for an element and return it. Raises TimeoutException if absent."""
        return WebDriverWait(self.driver, timeout).until(
            lambda d: d.find_element(AppiumBy.ACCESSIBILITY_ID, accessibility_id),
            f"element {accessibility_id!r} never appeared",
        )

    def is_present(self, accessibility_id, timeout=0):
        """Presence check that does not pay the full implicit-wait cost.

        Used for negative assertions ("the home tab bar must NOT be here"), so
        the implicit wait is dropped for the duration of the lookup and always
        restored.
        """
        self.driver.implicitly_wait(timeout)
        try:
            self.driver.find_element(AppiumBy.ACCESSIBILITY_ID, accessibility_id)
            return True
        except NoSuchElementException:
            return False
        finally:
            self.driver.implicitly_wait(DEFAULT_IMPLICIT_WAIT)

    @staticmethod
    def label_of(element):
        """Visible text of an element — iOS exposes it as the `label` attribute."""
        return element.get_attribute("label") or element.text
```

## `AutomationTests/pages/home_page.py`

```python
"""Home screen — MainTabBarController, the post-login window root."""
from pages.base_page import BasePage


class HomePage(BasePage):

    # The UITabBar container itself is not exposed in page_source — only its
    # three buttons are (verified 2026-07-23), so the tab bar's presence is
    # asserted through them.
    HOME_TAB = "home_hometab_button"
    LIVE_TAB = "home_livetab_button"
    PROFILE_TAB = "home_profiletab_button"
    TABS = (HOME_TAB, LIVE_TAB, PROFILE_TAB)

    EXPECTED_TAB_LABELS = ["Trang chủ", "Truyền hình", "Cá nhân"]

    def wait_until_loaded(self, timeout=15):
        self.wait_for(self.HOME_TAB, timeout=timeout)
        return self

    def is_displayed(self, timeout=0):
        return self.is_present(self.HOME_TAB, timeout=timeout)

    def tab_labels(self):
        return [self.label_of(self.find(tab)) for tab in self.TABS]

    def is_home_tab_selected(self):
        return self.find(self.HOME_TAB).get_attribute("selected") in ("true", True)
```

## `AutomationTests/pages/intro_page.py`

```python
"""Introduction screen — the first app screen after launch."""
from pages.base_page import BasePage
from pages.login_page import LoginPage


class IntroPage(BasePage):

    LOGIN_BUTTON = "intro_login_button"
    FREE_BUTTON = "intro_free_button"

    # Not app-owned: the iOS notification permission alert. It is raised by
    # IntroductionContentViewController.viewDidLoad on the first launch after a
    # data/privacy wipe and blocks every app element until it is answered.
    # It is reachable by its visible button name in page_source (verified
    # 2026-07-23). NOTE: "Don't Allow" is the least-privilege choice; the
    # reviewer has not yet confirmed Allow vs Don't Allow — change this one
    # constant if they want Allow.
    NOTIFICATION_ALERT_BUTTON = "Don't Allow"

    def dismiss_notification_permission(self):
        """Answer the notification alert if it is up. No-op when it is not.

        Only the first launch after a wipe shows it, so later tests in the same
        session must tolerate its absence.
        """
        if self.is_present(self.NOTIFICATION_ALERT_BUTTON, timeout=2):
            self.find(self.NOTIFICATION_ALERT_BUTTON).click()
        return self

    def is_displayed(self, timeout=2):
        return self.is_present(self.LOGIN_BUTTON, timeout=timeout)

    def open_login(self):
        self.wait_for(self.LOGIN_BUTTON).click()
        return LoginPage(self.driver)
```

## `AutomationTests/pages/login_page.py`

```python
"""Login screen (LoginViewController / LoginView)."""
from pages.base_page import BasePage
from pages.home_page import HomePage


class LoginPage(BasePage):

    USERNAME_FIELD = "login_username_field"
    PASSWORD_FIELD = "login_password_field"
    TERMS_CHECKBOX = "login_terms_checkbox"
    TERMS_LINK = "login_terms_link_button"
    SUBMIT_BUTTON = "login_submit_button"
    #: Only exists in the hierarchy once a submit has failed.
    ERROR_LABEL = "login_error_label"

    #: Terms sheet dismiss button — a WKWebView modal we do not own, matched by
    #: its visible name. Used only to prove no modal is on screen.
    TERMS_SHEET_DONE = "Xong"

    WRONG_CREDENTIALS_ERROR = "Sai tên đăng nhập hoặc mật khẩu"
    TERMS_REQUIRED_ERROR = "Vui lòng đồng ý với điều khoản sử dụng"

    def is_displayed(self, timeout=2):
        return self.is_present(self.USERNAME_FIELD, timeout=timeout)

    def enter_credentials(self, username, password):
        username_field = self.wait_for(self.USERNAME_FIELD)
        username_field.clear()
        username_field.send_keys(username)
        password_field = self.find(self.PASSWORD_FIELD)
        password_field.clear()
        password_field.send_keys(password)
        return self

    def accept_terms(self):
        """Tick the terms box.

        The checkbox exposes no checked/selected state in the hierarchy (it is a
        UIImageView with a tap gesture that only swaps its image), so its state
        can never be asserted — tap exactly once.
        """
        self.find(self.TERMS_CHECKBOX).click()
        return self

    def submit(self):
        """Tap 'Đăng nhập'.

        The button reports enabled+hittable even when the terms box is unticked,
        so the test must never gate on `is_enabled()`; an unticked submit simply
        produces the inline terms error.
        """
        self.find(self.SUBMIT_BUTTON).click()
        return self

    def login(self, username, password, accept_terms=True):
        """Fill the form and submit. Returns the HomePage view of the driver.

        The caller decides whether it expects to have landed there — on failure
        the app stays on this screen, which the returned page object's
        `is_displayed()` reports.
        """
        self.enter_credentials(username, password)
        if accept_terms:
            self.accept_terms()
        self.submit()
        return HomePage(self.driver)

    def error_text(self, timeout=10):
        return self.label_of(self.wait_for(self.ERROR_LABEL, timeout=timeout))

    def has_error(self, timeout=0):
        return self.is_present(self.ERROR_LABEL, timeout=timeout)

    def is_terms_sheet_open(self, timeout=0):
        return self.is_present(self.TERMS_SHEET_DONE, timeout=timeout)
```

## `AutomationTests/tests/test_login.py`

```python
"""Login flow: QA account → home screen.

Success (confirmed with the reviewer): the user enters a valid username and
password, ticks the terms checkbox, taps "Đăng nhập", and lands on the home
screen with the bottom tab bar visible (Trang chủ / Truyền hình / Cá nhân).

Failure (confirmed with the reviewer): the app stays on the login screen and
shows the inline error "Sai tên đăng nhập hoặc mật khẩu" under the password
field — it must NOT bounce back to the intro screen and must NOT show a modal.

Credentials come from APP_TEST_USERNAME / APP_TEST_PASSWORD (never hardcoded);
the tests skip cleanly when they are unset.
"""
import os

import pytest

from pages.home_page import HomePage
from pages.intro_page import IntroPage

USERNAME = os.environ.get("APP_TEST_USERNAME")
PASSWORD = os.environ.get("APP_TEST_PASSWORD")

requires_qa_account = pytest.mark.skipif(
    not (USERNAME and PASSWORD),
    reason="QA account missing — set APP_TEST_USERNAME and APP_TEST_PASSWORD",
)


@pytest.fixture()
def intro(driver):
    """Start every test from a freshly launched app on the intro screen.

    `reset_app_data: always` wipes the app once per session (conftest), so each
    test must establish its own state. terminate + activate is enough to get
    back to the intro screen — the app keeps no persisted session — and the
    notification alert is answered only if it is actually up (it appears on the
    first launch after the wipe).
    """
    bundle_id = driver.capabilities.get("bundleId") or os.environ["AGENTQA_BUNDLE_ID"]
    driver.terminate_app(bundle_id)
    driver.activate_app(bundle_id)
    page = IntroPage(driver)
    page.dismiss_notification_permission()
    return page


@requires_qa_account
def test_qa_account_login_lands_on_home(intro):
    """Happy path — the assertion this suite exists for."""
    login = intro.open_login()
    assert login.is_displayed(timeout=10), "tapping 'Đăng nhập ngay' did not open the login screen"

    home = login.login(USERNAME, PASSWORD)
    home.wait_until_loaded()

    assert home.tab_labels() == HomePage.EXPECTED_TAB_LABELS, (
        "home tab bar does not show Trang chủ / Truyền hình / Cá nhân"
    )
    assert home.is_home_tab_selected(), "the Trang chủ tab is not the selected tab"
    assert not login.is_displayed(), "the login screen is still on top after a valid login"
    assert not login.has_error(), "an error was shown even though the credentials are valid"


@requires_qa_account
def test_wrong_password_keeps_user_on_login_with_inline_error(intro):
    """Failure criteria, exactly as the reviewer described them."""
    login = intro.open_login()
    home = login.login(USERNAME, PASSWORD + "-wrong")

    assert login.error_text() == login.WRONG_CREDENTIALS_ERROR
    assert login.is_displayed(), "the app left the login screen after a failed login"
    assert not home.is_displayed(), "a failed login must not reach the home tab bar"
    assert not login.is_terms_sheet_open(), "a failed login must not open a modal"
    assert not intro.is_displayed(), "a failed login must not bounce back to the intro screen"


@requires_qa_account
def test_submit_without_accepting_terms_shows_terms_error(intro):
    """Guard path: the terms box gates the submit, and nothing is sent."""
    login = intro.open_login()
    home = login.login(USERNAME, PASSWORD, accept_terms=False)

    assert login.error_text() == login.TERMS_REQUIRED_ERROR
    assert login.is_displayed(), "the app left the login screen without accepted terms"
    assert not home.is_displayed(), "login must not succeed with the terms box unticked"
```
