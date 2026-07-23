# Questions asked

5 question(s) put to the human reviewer, verbatim.

### 1. Diagnosis of test_login_happy_path: it never reaches the login form. The app itself puts up 'THÔNG BÁO - Đã có lỗi xảy ra, Quý khách vui lòng thử lại sau! (58)' over the intro screen, and pytest reports 'Backend returned HTTP 404 on POST /device/register'. test_login_rejects_wrong_password fails with the identical alert, and no locator/identifier drifted (all login_* ids are present in the live hierarchy). Driving the same flow by hand (wipe data -> Don't Allow -> username/password -> terms -> Đăng nhập) reached the home tab bar fine. Is the /device/register 404 a known backend outage on this environment, or a real app regression I should report?

> Success = the user enters a valid username + password, ticks the terms checkbox, taps Đăng nhập, and lands on the home screen with the bottom tab bar visible (Trang chủ / Truyền hình / Cá nhân).

### 2. Confirm the success criterion for test_login_happy_path: valid credentials + terms ticked lands on MainTabBarController with home_home_tab visible. And what counts as a REAL failure for this flow - only the inline 'Sai tên đăng nhập hoặc mật khẩu' under the password field, or does this THÔNG BÁO alert also count as a genuine product failure the test should report rather than work around?

> Success = the user enters a valid username + password, ticks the terms checkbox, taps Đăng nhập, and lands on the home screen with the bottom tab bar visible (Trang chủ / Truyền hình / Cá nhân).

### 3. How do you want the THÔNG BÁO (58) alert handled? (a) leave the test unchanged and treat red as a real backend/app defect to file; (b) keep the assertion but add an explicit fail-fast that names the alert so the report is unambiguous; (c) dismiss it with 'Đóng' and continue - I will not do this without your say-so since it hides the error; (d) point the tests at a different backend/environment.

> Failure = the app stays on the login screen and shows the inline red text "Sai tên đăng nhập hoặc mật khẩu" under the password field. It must NOT bounce back to the intro screen and must not show a modal.

### 4. Understood: success = valid creds + terms -> home tab bar; failure = stays on login with the inline 'Sai tên đăng nhập hoặc mật khẩu', no modal, no bounce to intro. By that definition the current red IS a real defect: the app shows a modal THÔNG BÁO (58) on the intro screen after a POST /device/register 404, so login is unreachable. The test and its locators are correct - I will NOT dismiss the modal or loosen the assertion to make it green. Do you want me to (a) leave the test exactly as it is and file this as an app/backend defect, or (b) something else?

> Success = the user enters a valid username + password, ticks the terms checkbox, taps Đăng nhập, and lands on the home screen with the bottom tab bar visible (Trang chủ / Truyền hình / Cá nhân).

### 5. Is the /device/register 404 a known backend outage that will be fixed, so I should just re-run the suite once it is back - or should I treat it as an app regression and hand it to the app team?

> staging
