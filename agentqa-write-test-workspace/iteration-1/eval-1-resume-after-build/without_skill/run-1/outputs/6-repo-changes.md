# Repo changes

## git diff --numstat

```
4	1	.agentqa/memory/flows/login.md
3	3	.agentqa/memory/screens/home.md
2	2	.agentqa/memory/screens/intro.md
9	8	.agentqa/memory/screens/login_form.md
31	0	AutomationTests/conftest.py
2	0	AutomationTests/pytest.ini
```

## New files

```
AutomationTests/pages/base_page.py
AutomationTests/pages/home_page.py
AutomationTests/pages/intro_page.py
AutomationTests/pages/login_page.py
AutomationTests/tests/test_login.py
```

## Full diff

```diff
diff --git a/.agentqa/memory/flows/login.md b/.agentqa/memory/flows/login.md
index b899d7a..3a696d6 100644
--- a/.agentqa/memory/flows/login.md
+++ b/.agentqa/memory/flows/login.md
@@ -14,8 +14,11 @@ last_verified: 2026-07-23
 - [flow-step] fill username + password, tick "Tôi đồng ý với điều khoản sử dụng", press "Đăng nhập" #login
 - [flow-step] success → MainTabBarController with tab bar Trang chủ / Truyền hình / Cá nhân #login
 - [assertion] valid credentials + terms ticked lands on the home tab bar #login
+- [test] covered by AutomationTests/tests/test_login.py (page objects in AutomationTests/pages/); all 11 identifiers verified against the build on 2026-07-23 #login
 - [edge-case] wrong credentials → inline "Sai tên đăng nhập hoặc mật khẩu" under the password field, stays on login #login
-- [edge-case] terms unticked → "Vui lòng đồng ý với điều khoản sử dụng", submit is disabled #login
+- [edge-case] terms unticked → submit is still tappable in the 2026-07-23 build and shows "Vui lòng đồng ý với điều khoản sử dụng" via login_error_label; the older "submit is disabled" note did not reproduce #login
+- [quirk] AuthService keeps Session in memory only — nothing is written to the keychain or UserDefaults, so relaunching the app is enough to log out between tests; no data wipe needed per test #login
+- [quirk] the SpringBoard permission alert only reappears after a privacy reset, not on every relaunch — dismiss it best-effort rather than unconditionally waiting for it #login
 - [native] intro, login and home are native UIKit #login
 - [web] the terms sheet is a WKWebView with no native nodes — screenshot only #login
 - [quirk] the permission alert is owned by SpringBoard and appears on every wiped launch #login
diff --git a/.agentqa/memory/screens/home.md b/.agentqa/memory/screens/home.md
index 00a7996..dc198bb 100644
--- a/.agentqa/memory/screens/home.md
+++ b/.agentqa/memory/screens/home.md
@@ -10,9 +10,9 @@ last_verified: 2026-07-23
 
 ## Observations
 - [native] MainTabBarController with three tabs #login
-- [identifier] home_home_tab → MainTabBarController.homeTab; added-unverified 2026-07-23 #login
-- [identifier] home_live_tab → MainTabBarController.liveTab; added-unverified 2026-07-23 #login
-- [identifier] home_profile_tab → MainTabBarController.profileTab; added-unverified 2026-07-23 #login
+- [identifier] home_home_tab → MainTabBarController.homeTab; verified 2026-07-23 #login
+- [identifier] home_live_tab → MainTabBarController.liveTab; verified 2026-07-23 #login
+- [identifier] home_profile_tab → MainTabBarController.profileTab; verified 2026-07-23 #login
 
 ## Relations
 - used-by [[login]]
diff --git a/.agentqa/memory/screens/intro.md b/.agentqa/memory/screens/intro.md
index c22bee2..e6694f6 100644
--- a/.agentqa/memory/screens/intro.md
+++ b/.agentqa/memory/screens/intro.md
@@ -10,8 +10,8 @@ last_verified: 2026-07-23
 
 ## Observations
 - [native] IntroductionContentViewController, UIKit xib #login
-- [identifier] login_intro_login_button → IntroductionContentViewController.btnLogin; added-unverified 2026-07-23 #login
-- [identifier] login_intro_free_button → IntroductionContentViewController.btnFree; added-unverified 2026-07-23 #login
+- [identifier] login_intro_login_button → IntroductionContentViewController.btnLogin; verified 2026-07-23 #login
+- [identifier] login_intro_free_button → IntroductionContentViewController.btnFree; verified 2026-07-23 #login
 - [quirk] requests notification permission in viewDidLoad, so the alert covers this screen on a wiped launch #login
 
 ## Relations
diff --git a/.agentqa/memory/screens/login_form.md b/.agentqa/memory/screens/login_form.md
index ff08ee7..08f3888 100644
--- a/.agentqa/memory/screens/login_form.md
+++ b/.agentqa/memory/screens/login_form.md
@@ -10,14 +10,15 @@ last_verified: 2026-07-23
 
 ## Observations
 - [native] LoginView loaded from a nib by LoginViewController #login
-- [identifier] login_username_field → LoginView.usernameTextField; added-unverified 2026-07-23 #login
-- [identifier] login_password_field → LoginView.passwordTextField; added-unverified 2026-07-23 #login
-- [identifier] login_terms_checkbox → LoginView.checkBoxTermImgView; added-unverified 2026-07-23 #login
-- [identifier] login_terms_link → LoginView.termsLink; added-unverified 2026-07-23 #login
-- [identifier] login_submit_button → LoginView.btnLogin; added-unverified 2026-07-23 #login
-- [identifier] login_error_label → LoginView.errorLabel; added-unverified 2026-07-23 #login
-- [quirk] btnLogin.isEnabled is driven by termsAccepted — the checkbox must be tapped before submit #login
-- [quirk] errorLabel is hidden until showError(_:) runs #login
+- [identifier] login_username_field → LoginView.usernameTextField; verified 2026-07-23 #login
+- [identifier] login_password_field → LoginView.passwordTextField; verified 2026-07-23 #login
+- [identifier] login_terms_checkbox → LoginView.checkBoxTermImgView; verified 2026-07-23 #login
+- [identifier] login_terms_link → LoginView.termsLink; verified 2026-07-23 #login
+- [identifier] login_submit_button → LoginView.btnLogin; verified 2026-07-23 #login
+- [identifier] login_error_label → LoginView.errorLabel; verified 2026-07-23 #login
+- [quirk] errorLabel is hidden until showError(_:) runs — `login_error_label` is absent from the live tree until then, so its presence is a reliable "submit was rejected" signal #login
+- [quirk] login_terms_checkbox is a UIImageView + tap gesture, so it surfaces as XCUIElementTypeOther (not a real checkbox) — locate it by accessibility id, not by element type #login
+- [discrepancy] earlier notes said btnLogin stays DISABLED until termsAccepted; the 2026-07-23 build reports `enabled=true` with terms unticked, and tapping it shows the inline "Vui lòng đồng ý với điều khoản sử dụng" instead. LoginViewController.submit() has a `guard loginView.termsAccepted` that only makes sense if the button is tappable. Unresolved with the reviewer — no test asserts either behaviour yet. #login
 
 ## Relations
 - used-by [[login]]
diff --git a/AutomationTests/conftest.py b/AutomationTests/conftest.py
index 8c3b9b3..ee2e4bc 100644
--- a/AutomationTests/conftest.py
+++ b/AutomationTests/conftest.py
@@ -55,6 +55,37 @@ def driver(wipe_app_data):
     drv.quit()
 
 
+@pytest.fixture(scope="session")
+def credentials():
+    """QA credentials, by env-var name only — never hardcode the values."""
+    username = os.environ.get("APP_TEST_USERNAME")
+    password = os.environ.get("APP_TEST_PASSWORD")
+    if not username or not password:
+        pytest.fail(
+            "APP_TEST_USERNAME and APP_TEST_PASSWORD must be set in the environment"
+        )
+    return username, password
+
+
+@pytest.fixture
+def intro(driver):
+    """Start every test from a fresh, logged-out intro screen.
+
+    AuthService holds the Session in memory only (nothing is written to the
+    keychain or UserDefaults), so relaunching the app is enough to log out —
+    no per-test data wipe is needed. The notification permission alert only
+    reappears after the session-scoped privacy reset, so dismissing it is
+    best-effort.
+    """
+    from pages.intro_page import IntroPage
+
+    driver.terminate_app(BUNDLE_ID)
+    driver.activate_app(BUNDLE_ID)
+    page = IntroPage(driver)
+    page.dismiss_notification_permission()
+    return page
+
+
 @pytest.hookimpl(hookwrapper=True, tryfirst=True)
 def pytest_runtest_makereport(item, call):
     outcome = yield
diff --git a/AutomationTests/pytest.ini b/AutomationTests/pytest.ini
index 0bc5130..6953905 100644
--- a/AutomationTests/pytest.ini
+++ b/AutomationTests/pytest.ini
@@ -1,3 +1,5 @@
 [pytest]
 testpaths = tests
 addopts = -ra
+markers =
+    smoke: core happy-path checks that must pass on every build
```