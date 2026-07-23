# Questions asked

2 question(s) put to the human reviewer, verbatim.

### 1. Verified the new build on the sim. All 11 accessibility identifiers are live and the happy path works (intro -> login -> home tab bar). One discrepancy: our notes said the 'Đăng nhập' submit button stays DISABLED until the terms checkbox is ticked, but in this build it is ENABLED with terms unticked, and tapping it just shows the inline error 'Vui lòng đồng ý với điều khoản sử dụng'. Should the test assert the current behaviour (button tappable + inline error), or assert the button is disabled (which would fail this build as a regression)?

> Success = the user enters a valid username + password, ticks the terms checkbox, taps Đăng nhập, and lands on the home screen with the bottom tab bar visible (Trang chủ / Truyền hình / Cá nhân).

### 2. Besides the happy path, the requirement describes a wrong-credentials failure case ('Sai tên đăng nhập hoặc mật khẩu', stays on login, no modal). Do you want that as a second test in the same file, plus the terms-unticked case as a third?

> Success = the user enters a valid username + password, ticks the terms checkbox, taps Đăng nhập, and lands on the home screen with the bottom tab bar visible (Trang chủ / Truyền hình / Cá nhân).
