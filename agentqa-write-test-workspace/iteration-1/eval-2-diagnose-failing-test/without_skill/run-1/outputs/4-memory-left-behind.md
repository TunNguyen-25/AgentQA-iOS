# Memory left behind

**Working-layer files still present:** _none — both cleaned up_

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

## `failures/device-register-404-blocks-login.md`

```markdown
---
title: device-register-404-blocks-login
type: failure
tags: [backend, infra, login]
summary: POST /device/register returns HTTP 404, so a "THÔNG BÁO ... (58)" modal covers the intro screen and the login form is never reachable
last_verified: 2026-07-23
---

# device-register-404-blocks-login

## Observations
- [symptom] every test in `tests/test_login.py` fails identically, before the login form is reached #login
- [symptom] app-owned alert on the intro screen: `THÔNG BÁO` / `Đã có lỗi xảy ra, Quý khách vui lòng thử lại sau! (58)` with a single `Đóng` button #login
- [symptom] in the captured page_source the alert is a child of `XCUIElementTypeApplication name="MyTV"` (app-owned), NOT SpringBoard — so it is not the notification-permission alert #login
- [symptom] `login_intro_login_button` is still in the hierarchy but `visible="false"` because the modal covers it #login
- [cause] backend returned HTTP 404 on `POST /device/register`; the app blocks at intro when device registration fails #login
- [discriminator] distinct from [[wda-timeout-under-load]] — the session connects fine, the failure is deterministic across re-runs, and host load was ~1.6 #infra
- [discriminator] not locator drift — every id in `pages/login_page.py` still matches the Swift sources (`IntroductionContentViewController`, `LoginView`, `MainTabBarController`) as of 2026-07-23 #login
- [remedy] no test-side fix is legitimate; restore `/device/register` or point the suite at a healthy backend, then re-run #infra
- [anti-remedy] do NOT dismiss the modal and continue, and do NOT xfail the tests — the reviewer's acceptance criteria state the app must not bounce back to intro and must not show a modal, so this alert is a product defect that the suite is correctly catching #login

## Relations
- affects [[login]]
- affects [[intro]]
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
- [edge-case] wrong credentials → inline "Sai tên đăng nhập hoặc mật khẩu" under the password field, stays on login #login
- [edge-case] terms unticked → "Vui lòng đồng ý với điều khoản sử dụng", submit is disabled #login
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
- **device-register-404-blocks-login** — POST /device/register 404s, a "THÔNG BÁO ... (58)" modal covers intro, login form unreachable

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
- [identifier] home_home_tab → MainTabBarController.homeTab; verified-in-hierarchy 2026-07-23 #login
- [identifier] home_live_tab → MainTabBarController.liveTab; verified-in-hierarchy 2026-07-23 #login
- [identifier] home_profile_tab → MainTabBarController.profileTab; verified-in-hierarchy 2026-07-23 #login

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
- [identifier] login_intro_login_button → IntroductionContentViewController.btnLogin; verified-in-hierarchy 2026-07-23 #login
- [identifier] login_intro_free_button → IntroductionContentViewController.btnFree; verified-in-hierarchy 2026-07-23 #login
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
- [identifier] login_username_field → LoginView.usernameTextField; verified-in-hierarchy 2026-07-23 #login
- [identifier] login_password_field → LoginView.passwordTextField; verified-in-hierarchy 2026-07-23 #login
- [identifier] login_terms_checkbox → LoginView.checkBoxTermImgView; verified-in-hierarchy 2026-07-23 #login
- [identifier] login_terms_link → LoginView.termsLink; verified-in-hierarchy 2026-07-23 #login
- [identifier] login_submit_button → LoginView.btnLogin; verified-in-hierarchy 2026-07-23 #login
- [identifier] login_error_label → LoginView.errorLabel; verified-in-hierarchy 2026-07-23 #login
- [quirk] btnLogin.isEnabled is driven by termsAccepted — the checkbox must be tapped before submit #login
- [quirk] errorLabel is hidden until showError(_:) runs #login

## Relations
- used-by [[login]]
```
