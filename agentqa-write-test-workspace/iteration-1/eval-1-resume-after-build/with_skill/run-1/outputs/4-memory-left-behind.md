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
- [gotcha] agentqa-init reset-app-data.sh reports "not installed — nothing to wipe" on this simulator (no data container resolved); the conftest session fixture (simctl terminate + privacy reset all) is what actually resets state, which is why the notifications alert appears on the first launch of each pytest session
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
- [assertion] valid credentials + terms ticked lands on the home tab bar (Trang chủ / Truyền hình / Cá nhân) — covered by AutomationTests/tests/test_login.py::test_valid_credentials_land_on_home, green 2026-07-23 #login
- [edge-case] wrong credentials → inline "Sai tên đăng nhập hoặc mật khẩu" in login_error_label, stays on login, no modal, no bounce to intro — covered by test_wrong_password_shows_inline_error_and_stays_on_login #login
- [edge-case] terms unticked → submit is still tappable; pressing it shows "Vui lòng đồng ý với điều khoản sử dụng" in login_error_label and stays on login #login
- [native] intro, login and home are native UIKit #login
- [web] the terms sheet is a WKWebView with no native nodes — screenshot only #login
- [quirk] the SpringBoard notifications alert appears only on the first launch after the app privacy grants are reset — later terminate+activate relaunches in the same session do not re-prompt #login

## Relations
- covers [[intro]]
- covers [[login_form]]
- covers [[home]]
- [flow-step] terminate + activate returns to the intro screen — no session is persisted (AppRouter only swaps the in-memory root VC), so each test can relaunch to build its own state #login
```

## `index.md`

```markdown
# Memory index (compact — detail files loaded on demand)

## Flows
- login → Intro → login form → home tab bar, gated on a terms checkbox | detail: flows/login.md

## Screens
- home ids: home_home_tab✓ 0d, home_live_tab✓ 0d, home_profile_tab✓ 0d | MainTabBarController — the post-login landing surface
- intro ids: login_intro_free_button✓ 0d, login_intro_login_button✓ 0d | IntroductionContentViewController — login / guest entry point
- login_form ids: login_error_label✓ 0d, login_password_field✓ 0d, login_submit_button✓ 0d, login_terms_checkbox✓ 0d, login_terms_link✓ 0d, login_username_field✓ 0d | LoginView — username, password, terms checkbox, submit

## Failures
- wda-timeout-under-load → WebDriverAgent session timeout when the host is CPU-saturated
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
- [quirk] btnLogin.isEnabled reports enabled=true in the live hierarchy even with terms unticked — do not gate on isEnabled; pressing submit unticked shows login_error_label "Vui lòng đồng ý với điều khoản sử dụng" #login
- [quirk] errorLabel is hidden until showError(_:) runs #login

## Relations
- used-by [[login]]
```
