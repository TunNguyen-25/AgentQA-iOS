"""Page objects for the login flow."""
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import NoSuchElementException


class IntroPage:
    LOGIN_BUTTON = (AppiumBy.ACCESSIBILITY_ID, "login_intro_login_button")
    # SpringBoard's, not the app's: it sits outside the app element tree and no
    # accessibilityIdentifier can reach it, so match the visible label.
    PERMISSION_DENY = (AppiumBy.IOS_PREDICATE, 'label == "Don't Allow"')

    def __init__(self, driver):
        self.driver = driver

    def dismiss_permission_alert(self):
        """reset_app_data: always restores the permission state, so this prompt
        fires on every launch. Harmless when it is not there."""
        try:
            self.driver.find_element(*self.PERMISSION_DENY).click()
        except NoSuchElementException:
            pass

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
