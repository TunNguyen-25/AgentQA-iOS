# Questions asked

2 question(s) put to the human reviewer, verbatim.

### 1. Review checkpoint for the login flow. APP CODE: no changes in this session — the 11 accessibility identifiers were already in the build you installed, and all 11 are now confirmed present in the live Appium hierarchy (git diff on mytvb2c/ is empty, 0 deletions). NEW TEST FILES: AutomationTests/pages/{base_page,intro_page,login_page,home_page}.py and AutomationTests/tests/test_login.py — 3 tests, all passing: (1) valid credentials + ticked terms lands on the home tab bar with all 3 tabs present, (2) wrong password stays on login with inline 'Sai ten dang nhap hoac mat khau', no modal, no bounce to intro, (3) submit with terms unticked shows 'Vui long dong y voi dieu khoan su dung'. Do you approve this as-is?

> Success = the user enters a valid username + password, ticks the terms checkbox, taps Đăng nhập, and lands on the home screen with the bottom tab bar visible (Trang chủ / Truyền hình / Cá nhân).

### 2. One divergence from memory found during verification: the memory note said the submit button is DISABLED until the terms box is ticked, but the live hierarchy reports login_submit_button enabled=true even unticked — pressing it just shows the inline terms error. I have refreshed the memory notes to match the live behaviour and the test asserts the error rather than a disabled button. Is that the intended app behaviour, or should I file it as a bug against the app?

> Looks good, go ahead.
