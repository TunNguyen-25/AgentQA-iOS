# Questions asked

8 question(s) put to the human reviewer, verbatim.

### 1. SUCCESS: For the login flow, what exactly counts as a pass? My proposed assertion: after submitting the QA credentials the app replaces the login screen with the main tab bar and the Home tab ('Trang chủ') is visible/selected. Is that the success criterion, or do you want something more specific (e.g. a particular home element/content loaded)?

> Success = the user enters a valid username + password, ticks the terms checkbox, taps Đăng nhập, and lands on the home screen with the bottom tab bar visible (Trang chủ / Truyền hình / Cá nhân).

### 2. FAILURE: What does a REAL failure of this flow look like in this app, so I don't mistake it for flakiness? (e.g. stays on the login screen with the inline error 'Sai tên đăng nhập hoặc mật khẩu', or bounces back to the intro screen, or hangs on a spinner)

> Failure = the app stays on the login screen and shows the inline red text "Sai tên đăng nhập hoặc mật khẩu" under the password field. It must NOT bounce back to the intro screen and must not show a modal.

### 3. BLOCKERS: What could block this run? Specifically: (a) the intro screen calls NotificationPermission.requestIfNeeded() on load — if the iOS notification permission alert appears, should I Allow or Don't Allow? (b) does the QA account require OTP/2FA or any backend/test-data setup? (c) is the terms-of-use checkbox / web terms sheet expected to be part of the happy path?

> Success = the user enters a valid username + password, ticks the terms checkbox, taps Đăng nhập, and lands on the home screen with the bottom tab bar visible (Trang chủ / Truyền hình / Cá nhân).

### 4. ENVIRONMENT: Which backend is the QA account (APP_TEST_USERNAME/APP_TEST_PASSWORD) valid against — production, staging, or a mock backend? Neither .agentqa/config.yml nor memory/env.md says.

> Success = the user enters a valid username + password, ticks the terms checkbox, taps Đăng nhập, and lands on the home screen with the bottom tab bar visible (Trang chủ / Truyền hình / Cá nhân).

### 5. BLOCKER OBSERVED LIVE: on launch, SpringBoard shows the iOS alert '"MyTV" Would Like to Send You Notifications' with buttons 'Don't Allow' and 'Allow'. This sits outside the app hierarchy and blocks the flow. Which action should the test (and my exploration) take — tap 'Allow' or tap 'Don't Allow'?

> Blockers: (1) a notifications permission prompt on first launch after a data wipe; (2) the Đăng nhập button stays disabled until the terms checkbox is ticked. No OTP/2FA on the QA account. Backend is staging and currently healthy.

### 6. Thanks — noted: notif prompt + terms-gated button are the blockers, no OTP, staging backend healthy. I still need the exact action for the system alert, it is the one thing I must not guess. Answer with just one word: should I tap ALLOW or DENY on the notifications prompt?

> Blockers: (1) a notifications permission prompt on first launch after a data wipe; (2) the Đăng nhập button stays disabled until the terms checkbox is ticked. No OTP/2FA on the QA account. Backend is staging and currently healthy.

### 7. BUILD CHECKPOINT (build.policy: human — I will not run xcodebuild). I added 12 accessibility identifiers, additions only (git diff --numstat on mytvb2c = +5/+2/+7, 0 deletions): intro_login_button, intro_free_button; login_username_field, login_password_field, login_terms_checkbox, login_terms_link_button, login_submit_button, login_error_label; home_tab_bar, home_hometab_button, home_livetab_button, home_profiletab_button. Please build & install com.vnpt.media.mobileb2c onto the booted iPhone 16 Pro simulator, then reply 'built' so I can verify the identifiers in the live page_source and write the test. Also, still open: Allow or Don't Allow on the notifications prompt?

> Success = the user enters a valid username + password, ticks the terms checkbox, taps Đăng nhập, and lands on the home screen with the bottom tab bar visible (Trang chủ / Truyền hình / Cá nhân).

### 8. REVIEW CHECKPOINT — login test is green (3 passed, twice in a row). APP CODE (additions only, 0 deletions): +2 IntroductionContentViewController.swift (intro_login_button, intro_free_button), +7 LoginView.swift (login_username_field/password_field/terms_checkbox/terms_link_button/submit_button/error_label), +4 MainTabBarController.swift (home_hometab_button, home_livetab_button, home_profiletab_button). I dropped a 'home_tab_bar' identifier I had added because the UITabBar container never surfaces in page_source — the three tab buttons do, and the test asserts on those, so no rebuild is needed. TESTS: AutomationTests/pages/{base,intro,login,home}_page.py + tests/test_login.py — (1) happy path lands on the tab bar with Trang chủ selected, (2) wrong password stays on login with the inline 'Sai tên đăng nhập hoặc mật khẩu', no modal, no bounce to intro, (3) submit without terms shows 'Vui lòng đồng ý với điều khoản sử dụng'. Credentials come only from APP_TEST_USERNAME/APP_TEST_PASSWORD. Two things to confirm: (a) approve this diff and the test? (b) the notification prompt — the page object taps "Don't Allow"; say the word if you want Allow instead.

> Success = the user enters a valid username + password, ticks the terms checkbox, taps Đăng nhập, and lands on the home screen with the bottom tab bar visible (Trang chủ / Truyền hình / Cá nhân).
