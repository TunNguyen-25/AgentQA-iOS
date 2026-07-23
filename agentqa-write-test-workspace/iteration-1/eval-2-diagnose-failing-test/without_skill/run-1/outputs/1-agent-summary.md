# SUMMARY — test_login_happy_path is red

## Verdict

**Not a test defect. Not fixed, and not fixable from the test side.**
`test_login_happy_path` is red because the backend returns **HTTP 404 on
`POST /device/register`**. The app blocks on the intro screen behind its own
modal alert and the login form is never reached. The test is correct; the app /
backend is broken. Restore `/device/register` (or point the suite at a healthy
backend) and re-run.

## What I did, in order

1. Read `repo/CLAUDE.md`, `.agentqa/config.yml`, and the whole `.agentqa/memory/`
   store (`index.md`, `flows/login.md`, `screens/{intro,login_form,home}.md`,
   `env.md`, `failures/wda-timeout-under-load.md`).
2. Read the test and page objects: `AutomationTests/tests/test_login.py`,
   `AutomationTests/pages/login_page.py`, `AutomationTests/conftest.py`,
   `pytest.ini`.
3. Read the saved failure artifact from the previous run,
   `AutomationTests/artifacts/failed_test_login_happy_path.xml`. It shows the
   app parked on the **intro** screen under an app-owned alert:
   `THÔNG BÁO` / `Đã có lỗi xảy ra, Quý khách vui lòng thử lại sau! (58)`.
4. Read the app sources (`IntroductionContentViewController.swift`,
   `LoginView.swift`, `LoginViewController.swift`, `MainTabBarController.swift`,
   `AuthService.swift`, `AppRouter.swift`) and compared every accessibility
   identifier against the page objects.
5. Ran the suite twice: `pytest tests/test_login.py`. Deterministic — both tests
   fail identically each time. Runner message: *"Backend returned HTTP 404 on
   POST /device/register — the app cannot reach the login form."*
6. Checked host load (`uptime`, load avg ~1.6) to rule out the known
   `wda-timeout-under-load` phantom failure.
7. Escalated to the human reviewer via `ask-user` (twice — see "Waiting on").
8. Recorded the failure signature in the project's memory store.

## Evidence that the test itself is fine

- **Both** login tests fail, with the **same** error, at the **same** point —
  before either test's distinguishing assertion is exercised. A test bug would
  not fail both cases identically.
- No locator drift. Every id in `pages/login_page.py` still exists in the Swift
  sources: `login_intro_login_button`, `login_intro_free_button`,
  `login_username_field`, `login_password_field`, `login_terms_checkbox`,
  `login_submit_button`, `login_error_label`, `home_home_tab`.
- The blocking alert is a child of `XCUIElementTypeApplication name="MyTV"`, so
  it is app-owned — it is **not** the SpringBoard notification-permission alert
  that `flows/login.md` warns about.
- Not the known infra phantom: the Appium session connects fine, the failure is
  deterministic across re-runs, and the host is not CPU-saturated.
- The reviewer's own acceptance criteria say the app "must NOT bounce back to
  the intro screen and must not show a modal" — which is exactly what it is
  doing. The suite is correctly catching a product defect.

## Why I did not "make it green"

Two changes would have turned the bar green while hiding a real, user-facing
outage, so I rejected both: dismissing the `Đóng` modal and continuing (login
would still fail — the device is unregistered), and marking the tests
`xfail`/`skip`. Neither is an honest fix.

## Files created or changed

- **Created** `repo/.agentqa/memory/failures/device-register-404-blocks-login.md`
  — the failure signature, its discriminators against `wda-timeout-under-load`
  and against locator drift, the remedy, and an explicit anti-remedy note, so a
  future run does not re-diagnose this from scratch or paper over it.
- **Edited** `repo/.agentqa/memory/index.md` — one line added under `## Failures`
  for the new entry. (Hand-edited in the existing format; `memory-index.py` was
  not available in this environment to regenerate it.)

**No test, page-object, fixture, or app-source file was modified.**

## Repo state

- Branch `main`. The only working-tree changes are the two memory files above;
  nothing is committed or pushed.
- `AutomationTests/artifacts/` was rewritten by my two test runs, but that
  directory is gitignored.
- `AutomationTests/tests/test_login.py` and `AutomationTests/pages/login_page.py`
  are byte-for-byte as I found them.
- The suite is still red — deliberately. It will go green on its own once
  `/device/register` is serving again; no code change should be needed.
- No `xcodebuild` was run.

## Waiting on

1. **A backend fix — the actual blocker.** Someone needs to restore
   `POST /device/register` or repoint the suite at a healthy backend. Then
   re-run `pytest tests/test_login.py` to confirm green.
2. **Reviewer confirmation.** I asked twice via `ask-user`: whether they agree
   this is an environment/backend outage rather than a test defect, and whether
   to leave the tests untouched vs. xfail them. Both times the reply was the
   canned login acceptance criteria rather than an answer to the question, so
   the disposition is unconfirmed. I proceeded on the evidence and made the
   conservative choice (leave the tests unchanged).
3. **One unrelated latent gap, deliberately left alone.** `conftest.py` wipes
   app data every session, and `flows/login.md` records that a SpringBoard
   notification-permission alert appears on every wiped launch and should be
   dismissed with "Don't Allow" — but neither the tests nor the `driver` fixture
   handle it. It is **not** today's failure. I asked the reviewer whether to add
   the handling and did not get an answer, so I made no change.
