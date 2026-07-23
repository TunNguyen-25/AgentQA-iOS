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

## `flows/login.md`

```markdown
---
title: Login flow (QA account -> home)
type: flow
tags:
- login
- home
- intro
- permissions
---

# Login flow (QA account -> home)

Verified on the booted simulator (iPhone 16 Pro, iOS 18.5) on 2026-07-23 while
writing `AutomationTests/tests/test_login.py`.

## Path
launch -> SpringBoard notification prompt -> `IntroductionContentViewController`
-> `LoginViewController` -> `MainTabBarController`.

## Observations
- [nav] The app does NOT open on the login form. First screen is
  `IntroductionContentViewController`; the login form is reached by tapping
  "Đăng nhập ngay" (`intro_login_button`). "Xem miễn phí"
  (`intro_guest_button`) goes straight to a guest home and skips auth.
- [permission] `reset_app_data: always` wipes privacy grants, so
  `NotificationPermission.requestIfNeeded()` fires the "MyTV Would Like to Send
  You Notifications" prompt on every session's first launch, on top of the intro
  screen. It is owned by SpringBoard, so it is not in the app's own tree — match
  it by system label, not by an app identifier. Reviewer decision: always take
  **"Don't Allow"** so no banner can cover the UI mid-test. Handled in
  `BasePage.deny_system_alert()`, called from `IntroductionPage.wait_until_loaded()`.
- [gotcha] Login cannot succeed without ticking the terms box. `LoginView` keeps
  `btnLogin` disabled until `termsAccepted`, and `LoginViewController.submit()`
  returns early with the inline error "Vui lòng đồng ý với điều khoản sử dụng"
  — `AuthService.login` is never called. Confirmed live.
- [gotcha] The terms box is a `UIImageView` + `UITapGestureRecognizer`
  (`checkBoxTermImgView`), not a control. Tap `login_terms_checkbox`. The
  neighbouring `login_terms_link` button opens the `TermsWebViewController`
  sheet instead and ticks nothing.
- [web-screen] `TermsWebViewController` is a `WKWebView`; its content is not in
  the accessibility tree. Only the "Xong" dismiss button is reachable natively.
  Read it with `agent-device screenshot` if a test ever needs it.
- [gotcha] Labels are not unique on the login screen: the heading static text
  and the submit button are both named "Đăng nhập". Locate by accessibility
  identifier, or a name-only locator can hit the heading.
- [assert] Success signal = the bottom tab bar on `MainTabBarController`:
  Trang chủ / Truyền hình / Cá nhân. Guest mode reaches the same tab bar but
  without the live tab, so asserting all three tabs discriminates an
  authenticated session from a guest one.

## Identifiers added for this flow
The app shipped with no accessibility identifiers; they were added to the Swift
sources following `identifier_convention: screen_element_type` and verified in
the live hierarchy with `agent-device snapshot`.

| Identifier | Swift symbol |
|---|---|
| `intro_login_button` | `IntroductionContentViewController.btnLogin` |
| `intro_guest_button` | `IntroductionContentViewController.btnFree` |
| `login_username_field` | `LoginView.usernameTextField` |
| `login_password_field` | `LoginView.passwordTextField` |
| `login_terms_checkbox` | `LoginView.checkBoxTermImgView` |
| `login_terms_link` | `LoginView.termsLink` |
| `login_submit_button` | `LoginView.btnLogin` |
| `login_error_label` | `LoginView.errorLabel` |
| `home_home_button` | `MainTabBarController.homeTab` |
| `home_live_button` | `MainTabBarController.liveTab` |
| `home_profile_button` | `MainTabBarController.profileTab` |

- [build-policy] Those source edits need a human build+install before the test
  can run against a real device build (`build.policy: human`).
```

## `index.md`

```markdown
# Memory index (compact — detail files loaded on demand)

| Note | Type | About |
|---|---|---|
| [env.md](env.md) | env | Environment gotchas, helper commands, credential env-var names |
| [flows/login.md](flows/login.md) | flow | Intro -> login -> home path, notification prompt, terms-checkbox gate, identifier map |
```
