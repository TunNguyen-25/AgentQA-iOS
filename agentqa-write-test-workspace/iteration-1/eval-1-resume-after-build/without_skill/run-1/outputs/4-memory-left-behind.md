# Memory left behind

**Working-layer files still present:** `.run-checkpoint.md`, `.session-requirement.md`

## `.run-checkpoint.md`

```markdown
---
run_id: login-2026-07-23-01
current_step: 8
feature: login
updated: 2026-07-23
status: complete
---

## Verified identifiers (confirmed live on the 2026-07-23 build)
- login_intro_login_button → IntroductionContentViewController.btnLogin
- login_intro_free_button → IntroductionContentViewController.btnFree
- login_username_field → LoginView.usernameTextField
- login_password_field → LoginView.passwordTextField
- login_terms_checkbox → LoginView.checkBoxTermImgView
- login_terms_link → LoginView.termsLink
- login_submit_button → LoginView.btnLogin
- login_error_label → LoginView.errorLabel
- home_home_tab → MainTabBarController.homeTab
- home_live_tab → MainTabBarController.liveTab
- home_profile_tab → MainTabBarController.profileTab

All 11 appeared in the live hierarchy after the human build. No Swift changes
were needed in this session.

## Hypothesis under test
Valid credentials + ticked terms checkbox lands the user on the home tab bar.
CONFIRMED on device and covered by an automated test.

## Delivered
- AutomationTests/pages/{base_page,intro_page,login_page,home_page}.py
- AutomationTests/tests/test_login.py — 2 tests, both passing
- AutomationTests/conftest.py — added `credentials` and `intro` fixtures
- AutomationTests/pytest.ini — registered the `smoke` marker

## Blocker
None.

## Open question for the reviewer
The terms-unticked behaviour is unresolved: this build leaves "Đăng nhập"
enabled and shows an inline error, while earlier notes said the button stays
disabled. The reviewer answered the question with the success criterion rather
than a ruling, so no test asserts either behaviour. Re-ask before adding a
terms-unticked test.
```

## `.session-requirement.md`

```markdown
---
title: Session requirement — login
type: session-requirement
updated: 2026-07-23
---
## Request
Write a UI test for the login flow — the user logs in and reaches the home screen.

## Success
The user enters a valid username and password, ticks the terms checkbox, taps
Đăng nhập, and lands on the home screen with the bottom tab bar visible.

## Failure
The app stays on the login screen and shows the inline red text "Sai tên đăng
nhập hoặc mật khẩu" under the password field. It must not bounce back to intro
and must not show a modal.

## Blockers
- Notifications permission alert on first launch after a wipe → reviewer said tap "Don't Allow"
- Đăng nhập stays disabled until the terms checkbox is ticked → tick it before submitting
- No OTP/2FA on the QA account

## Environment / preconditions
staging backend; start logged out; credentials from APP_TEST_USERNAME / APP_TEST_PASSWORD.
```

## `README.md`

```markdown
# .agentqa/memory — behavioral knowledge store

Behavioral knowledge the test agent hand-earns at runtime: real navigation
paths, native-vs-web screens, verified identifier placements, phantom-failure
signatures, build gotchas. Not code knowledge — CodeGraph regenerates that.

`index.md` is generated. Rebuild it with:

    python3 <skill>/scripts/memory-index.py .agentqa/memory
```

## `env.md`

```markdown
---
title: Environment & project knowledge
type: env
tags:
- env
---

# Environment & project knowledge

Narrative knowledge for this app's UI tests. Structured facts live in
`.agentqa/config.yml`; this file holds the *why* and the gotchas. No secrets —
credential env-var **names** only.

## Observations
- [gotcha] Never run CPU-heavy jobs (e.g. `codegraph init`) during simulator tests — WebDriverAgent times out and produces phantom failures.
- [gotcha] Appium `page_source` for the booted simulator is printed by the repo helper `page-source` (already on PATH). Use it instead of hand-rolling an Appium client.
- [gotcha] The human reviewer is reachable only through the `ask-user` helper on PATH: `ask-user "<question>"` prints their answer. Interactive prompts do not reach them.
- [credential-env] APP_TEST_USERNAME, APP_TEST_PASSWORD
- [build-policy] Manual builds required — signing and package configuration require human intervention (build.policy: human)
```

## `failures/wda-timeout-under-load.md`

```markdown
---
title: wda-timeout-under-load
type: failure
tags: [phantom, infra]
summary: WebDriverAgent session timeout when the host is CPU-saturated
last_verified: 2026-07-20
---

# wda-timeout-under-load

## Observations
- [symptom] `WebDriverAgent process failed to start` or a session that hangs for 60s then dies, with no app-side error #infra
- [cause] a CPU-heavy job (usually `codegraph init`) running while the simulator drives the suite #infra
- [remedy] stop the indexing job, wait for load to drop, re-run the suite once #infra
```

## `flows/login.md`

```markdown
---
title: login
type: flow
tags: [login, authentication]
summary: Intro → login form → home tab bar, gated on a terms checkbox
last_verified: 2026-07-23
---

# login

## Observations
- [flow-step] launch → notifications permission alert (SpringBoard) → dismissed with "Don't Allow" per reviewer #login
- [flow-step] IntroductionContentViewController → press "Đăng nhập ngay" → LoginViewController #login
- [flow-step] fill username + password, tick "Tôi đồng ý với điều khoản sử dụng", press "Đăng nhập" #login
- [flow-step] success → MainTabBarController with tab bar Trang chủ / Truyền hình / Cá nhân #login
- [assertion] valid credentials + terms ticked lands on the home tab bar #login
- [test] covered by AutomationTests/tests/test_login.py (page objects in AutomationTests/pages/); all 11 identifiers verified against the build on 2026-07-23 #login
- [edge-case] wrong credentials → inline "Sai tên đăng nhập hoặc mật khẩu" under the password field, stays on login #login
- [edge-case] terms unticked → submit is still tappable in the 2026-07-23 build and shows "Vui lòng đồng ý với điều khoản sử dụng" via login_error_label; the older "submit is disabled" note did not reproduce #login
- [quirk] AuthService keeps Session in memory only — nothing is written to the keychain or UserDefaults, so relaunching the app is enough to log out between tests; no data wipe needed per test #login
- [quirk] the SpringBoard permission alert only reappears after a privacy reset, not on every relaunch — dismiss it best-effort rather than unconditionally waiting for it #login
- [native] intro, login and home are native UIKit #login
- [web] the terms sheet is a WKWebView with no native nodes — screenshot only #login
- [quirk] the permission alert is owned by SpringBoard and appears on every wiped launch #login

## Relations
- covers [[intro]]
- covers [[login_form]]
- covers [[home]]
```

## `index.md`

```markdown
# Memory index (compact — detail files loaded on demand)

## Flows
- **login** — Intro → login form → home tab bar, gated on a terms checkbox
  - covers: intro, login_form, home

## Screens
- **intro** — IntroductionContentViewController — login / guest entry point
- **login_form** — LoginView — username, password, terms checkbox, submit
- **home** — MainTabBarController — the post-login landing surface

## Failures
- **wda-timeout-under-load** — WebDriverAgent session timeout when the host is CPU-saturated

## Env
- env.md — build policy, credential env-var names, simulator gotchas
```

## `screens/home.md`

```markdown
---
title: home
type: screen
tags: [home]
summary: MainTabBarController — the post-login landing surface
last_verified: 2026-07-23
---

# home

## Observations
- [native] MainTabBarController with three tabs #login
- [identifier] home_home_tab → MainTabBarController.homeTab; verified 2026-07-23 #login
- [identifier] home_live_tab → MainTabBarController.liveTab; verified 2026-07-23 #login
- [identifier] home_profile_tab → MainTabBarController.profileTab; verified 2026-07-23 #login

## Relations
- used-by [[login]]
```

## `screens/intro.md`

```markdown
---
title: intro
type: screen
tags: [login]
summary: IntroductionContentViewController — login / guest entry point
last_verified: 2026-07-23
---

# intro

## Observations
- [native] IntroductionContentViewController, UIKit xib #login
- [identifier] login_intro_login_button → IntroductionContentViewController.btnLogin; verified 2026-07-23 #login
- [identifier] login_intro_free_button → IntroductionContentViewController.btnFree; verified 2026-07-23 #login
- [quirk] requests notification permission in viewDidLoad, so the alert covers this screen on a wiped launch #login

## Relations
- used-by [[login]]
```

## `screens/login_form.md`

```markdown
---
title: login_form
type: screen
tags: [login]
summary: LoginView — username, password, terms checkbox, submit
last_verified: 2026-07-23
---

# login_form

## Observations
- [native] LoginView loaded from a nib by LoginViewController #login
- [identifier] login_username_field → LoginView.usernameTextField; verified 2026-07-23 #login
- [identifier] login_password_field → LoginView.passwordTextField; verified 2026-07-23 #login
- [identifier] login_terms_checkbox → LoginView.checkBoxTermImgView; verified 2026-07-23 #login
- [identifier] login_terms_link → LoginView.termsLink; verified 2026-07-23 #login
- [identifier] login_submit_button → LoginView.btnLogin; verified 2026-07-23 #login
- [identifier] login_error_label → LoginView.errorLabel; verified 2026-07-23 #login
- [quirk] errorLabel is hidden until showError(_:) runs — `login_error_label` is absent from the live tree until then, so its presence is a reliable "submit was rejected" signal #login
- [quirk] login_terms_checkbox is a UIImageView + tap gesture, so it surfaces as XCUIElementTypeOther (not a real checkbox) — locate it by accessibility id, not by element type #login
- [discrepancy] earlier notes said btnLogin stays DISABLED until termsAccepted; the 2026-07-23 build reports `enabled=true` with terms unticked, and tapping it shows the inline "Vui lòng đồng ý với điều khoản sử dụng" instead. LoginViewController.submit() has a `guard loginView.termsAccepted` that only makes sense if the button is tappable. Unresolved with the reviewer — no test asserts either behaviour yet. #login

## Relations
- used-by [[login]]
```
