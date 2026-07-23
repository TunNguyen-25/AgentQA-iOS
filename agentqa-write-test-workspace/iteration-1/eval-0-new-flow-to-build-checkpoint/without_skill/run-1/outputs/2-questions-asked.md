# Questions asked

4 question(s) put to the human reviewer, verbatim.

### 1. The MyTV app source has NO accessibility identifiers on the login/intro/home elements — the page_source only exposes Vietnamese labels (e.g. textfield name='Tên đăng nhập', button name='Đăng nhập'). But .agentqa/config.yml declares identifier_convention: screen_element_type (e.g. login_username_field). Do you want me to (A) add accessibilityIdentifier to the Swift sources and write the test against those ids — which means the test can't pass until you do a manual build, or (B) write the test against the visible Vietnamese labels so it runs against the currently installed build today?

> Success = the user enters a valid username + password, ticks the terms checkbox, taps Đăng nhập, and lands on the home screen with the bottom tab bar visible (Trang chủ / Truyền hình / Cá nhân).

### 2. reset_app_data: always wipes privacy, so the iOS 'MyTV Would Like to Send You Notifications' SpringBoard alert appears on every session launch. Should the test tap 'Allow' explicitly, or would you rather I add autoAcceptAlerts to the shared Appium options in AutomationTests/conftest.py?

> Tap "Don't Allow" — the suite must run with notifications off so nothing covers the UI mid-test.

### 3. For the 'ended up on home' assertion, the home screen shows a 'Xin chào' static text plus tab buttons 'Trang chủ', 'Truyền hình', 'Cá nhân'. Is asserting those tab buttons + greeting the right success signal, or is there a stronger logged-in-only marker you want checked (note: guest mode reaches the same MainTabBarController)?

> Success = the user enters a valid username + password, ticks the terms checkbox, taps Đăng nhập, and lands on the home screen with the bottom tab bar visible (Trang chủ / Truyền hình / Cá nhân).

### 4. Re-asking the one question that decides whether the test can run today — please answer just 'A' or 'B'. A = I edit mytvb2c/Sources (LoginView.swift, IntroductionContentViewController.swift, MainTabBarController.swift) to add accessibilityIdentifiers like login_username_field, then write the test against those ids; the test will FAIL until you do a manual build+install. B = I touch no app source and write the test against the Vietnamese labels already in the accessibility tree; it passes against the build currently on the simulator. Which one?

> Success = the user enters a valid username + password, ticks the terms checkbox, taps Đăng nhập, and lands on the home screen with the bottom tab bar visible (Trang chủ / Truyền hình / Cá nhân).
