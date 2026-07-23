# SUMMARY — UI test for the MyTV login flow

## What I did, in order

1. Read `repo/CLAUDE.md`, `.agentqa/config.yml`, `.agentqa/memory/*`,
   `AutomationTests/conftest.py`, `pytest.ini`, `requirements.txt`.
   Key project facts: bundle `com.vnpt.media.mobileb2c`, tests in
   `AutomationTests/`, `reset_app_data: always`, `build.policy: human`,
   `identifier_convention: screen_element_type`, creds from
   `APP_TEST_USERNAME` / `APP_TEST_PASSWORD`.
2. Read the app sources for the flow: `Login/IntroductionContentViewController.swift`,
   `Login/LoginViewController.swift`, `Login/LoginView.swift`,
   `Login/TermsWebViewController.swift`, `App/AppRouter.swift`,
   `Home/MainTabBarController.swift`, `Networking/AuthService.swift`.
3. Drove the flow live on the simulator (`agent-device open` / `press` / `fill`,
   `page-source`) to confirm the real path and the failure modes:
   - launch shows a SpringBoard notification permission alert (privacy is wiped
     every session by `reset_app_data: always`);
   - first app screen is the intro screen, not the login form;
   - submitting without ticking the terms box only renders the inline error
     "Vui lòng đồng ý với điều khoản sử dụng" — no auth call;
   - ticking the box then submitting with the QA account lands on
     `MainTabBarController` (Trang chủ / Truyền hình / Cá nhân).
4. Asked the reviewer via `ask-user` about (a) identifiers vs. Vietnamese
   labels, (b) how to answer the notification alert, (c) the home assertion.
   Only (b) got a specific answer: tap "Don't Allow" so notifications stay off
   and nothing covers the UI mid-test. The other two came back with the success
   criteria only ("valid credentials + terms ticked -> home screen with the
   bottom tab bar visible"). I re-asked (a) as a plain A/B and got the same
   canned answer, so I decided it myself: follow the project's declared
   `identifier_convention` and add identifiers.
5. Added `accessibilityIdentifier`s to the three view files and verified each
   one appears in the live hierarchy with `agent-device snapshot`.
6. Wrote page objects + the test, ran the suite: 1 passed.
7. Recorded the behavioral knowledge in `.agentqa/memory/`.

## Files created

- `repo/AutomationTests/pages/base_page.py` — waits, tap/type helpers, and
  `deny_system_alert()` (locates the SpringBoard prompt by system label, always
  takes the deny branch; falls back to the alert API).
- `repo/AutomationTests/pages/introduction_page.py` — intro screen; denies the
  permission prompt, taps "Đăng nhập ngay".
- `repo/AutomationTests/pages/login_page.py` — credentials, terms checkbox,
  submit, inline error accessor.
- `repo/AutomationTests/pages/home_page.py` — waits for the tab bar,
  `tab_bar_is_visible()` asserts all three tabs.
- `repo/AutomationTests/tests/test_login.py` — `test_qa_account_login_lands_on_home`,
  skipped if the credential env vars are unset.
- `repo/.agentqa/memory/flows/login.md` — flow note (nav path, permission
  prompt, terms gate, WKWebView terms sheet, duplicate "Đăng nhập" label,
  identifier map).

## Files changed

- `repo/mytvb2c/Sources/Login/LoginView.swift` — identifiers in `awakeFromNib`:
  `login_username_field`, `login_password_field`, `login_terms_checkbox`,
  `login_terms_link`, `login_submit_button`, `login_error_label`.
- `repo/mytvb2c/Sources/Login/IntroductionContentViewController.swift` —
  `intro_login_button`, `intro_guest_button` in `viewDidLoad`.
- `repo/mytvb2c/Sources/Home/MainTabBarController.swift` —
  `home_home_button`, `home_live_button`, `home_profile_button` in `viewDidLoad`.
- `repo/.agentqa/memory/index.md` — index rows for `env.md` and `flows/login.md`
  (written by hand; the skill's `memory-index.py` generator is not in this repo).

`AutomationTests/conftest.py` was deliberately left untouched — the permission
alert is handled in the page object rather than by adding `autoAcceptAlerts` to
the shared driver options, per the reviewer's "Don't Allow" answer.

## Result

`cd repo/AutomationTests && pytest` -> `1 passed`. No `artifacts/` were
produced (that dir is gitignored anyway).

## Repo state

All work is uncommitted in the working tree on `main` (nothing staged, no
commits made, no branches created). `git status --short`:

```
 M .agentqa/memory/index.md
 M mytvb2c/Sources/Home/MainTabBarController.swift
 M mytvb2c/Sources/Login/IntroductionContentViewController.swift
 M mytvb2c/Sources/Login/LoginView.swift
?? .agentqa/memory/flows/login.md
?? AutomationTests/pages/base_page.py
?? AutomationTests/pages/home_page.py
?? AutomationTests/pages/introduction_page.py
?? AutomationTests/pages/login_page.py
?? AutomationTests/tests/test_login.py
```

Simulator was left with the app open on the logged-in home screen.

## Waiting on / open items

- Human build. `build.policy: human` and I never ran `xcodebuild`. The three
  Swift files now assign accessibility identifiers; a real build+install is
  needed before the test runs against a freshly compiled app. (In this
  workspace the identifiers already resolve in the live hierarchy, which is how
  I verified the naming.)
- Unanswered review question. The reviewer never confirmed identifiers vs.
  labels. If they would rather not touch app source, the three Swift diffs can
  be reverted and each `*_field` / `*_button` constant in `pages/` swapped for
  the Vietnamese label — but note the login screen has two elements named
  "Đăng nhập" (heading static text and submit button), so label locators there
  need a type predicate to stay unambiguous.
- Not covered (out of scope for the asked-for happy path): wrong-credentials
  error, terms-not-accepted error, guest entry, and the WKWebView terms sheet.
