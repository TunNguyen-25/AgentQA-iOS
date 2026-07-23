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
- [gotcha] The conftest `driver` fixture is session-scoped and the data wipe runs once per session — per-test isolation is done inside the test module with driver.terminate_app + activate_app, not by re-wiping
- [gotcha] Negative assertions ("X must NOT be on screen") must drop the 10s implicit wait for the lookup or every one costs 10s — pages/base_page.py:is_present(timeout=0) does this and restores it
```

## `flows/login.md`

```markdown
---
title: Login flow (QA account → home)
type: flow
tags:
- login
- auth
- home
summary: Launch → notif alert → intro → login form (username, password, terms tick) → main tab bar; wrong password keeps you on login with an inline error.
last_verified: 2026-07-23
---

# Login flow (QA account → home)

## Relations
- covers [[Introduction screen]]
- covers [[Login screen]]
- covers [[Home (MainTabBarController)]]
- covers [[Terms sheet (web)]]

## Observations
- [flow-step] Launch with wiped app data → SpringBoard alert ""MyTV" Would Like to Send You Notifications" (Don't Allow / Allow) must be dismissed before the app UI is reachable #login
- [flow-step] Intro screen → tap "Đăng nhập ngay" → LoginViewController/LoginView is pushed #login
- [flow-step] Login screen → fill "Tên đăng nhập" + "Mật khẩu", tap the terms checkbox, tap "Đăng nhập" #login
- [flow-step] Valid credentials → window root swaps to MainTabBarController (tab bar Trang chủ selected / Truyền hình / Cá nhân) #login
- [assertion] After valid QA credentials with the terms box ticked, the login screen is replaced by the main tab bar showing Trang chủ (selected), Truyền hình and Cá nhân #login
- [edge-case] Wrong password + terms ticked → stays on LoginView with inline staticText "Sai tên đăng nhập hoặc mật khẩu"; no modal, no bounce back to the intro screen (observed live) #login
- [edge-case] Submit with terms NOT ticked → stays on LoginView with inline staticText "Vui lòng đồng ý với điều khoản sử dụng"; no network call (observed live) #login
- [native] Every step of this flow is native UIKit; the only web surface is the optional terms sheet #login
- [quirk] Test isolation: driver.terminate_app + activate_app returns the app to the intro screen (no persisted session, verified live); the notification alert only appears on the first launch after a privacy/data reset, so later tests in a session must tolerate its absence #login
- [quirk] Covered by AutomationTests/tests/test_login.py (3 tests: happy path, wrong password, terms guard) with page objects pages/{base,intro,login,home}_page.py — green twice consecutively from a wiped app on 2026-07-23 #login
```

## `index.md`

```markdown
# Memory index (compact — detail files loaded on demand)

## Flows
- Login flow (QA account → home) → Launch → notif alert → intro → login form (username, password, terms tick) → main tab bar; wrong password keeps you on login with an inline error. | detail: flows/login.md

## Screens
- Home (MainTabBarController) ids: home_hometab_button✓ 0d, home_livetab_button✓ 0d, home_profiletab_button✓ 0d | Post-login root — native tab bar with Trang chủ (selected) / Truyền hình / Cá nhân and a "Xin chào" greeting.
- Introduction screen ids: intro_free_button✓ 0d, intro_login_button✓ 0d | First screen after launch; native; "Đăng nhập ngay" / "Xem miễn phí"; triggers the notification permission alert.
- Login screen ids: login_error_label✓ 0d, login_password_field✓ 0d, login_submit_button✓ 0d, login_terms_checkbox✓ 0d, login_terms_link_button✓ 0d, login_username_field✓ 0d | Native LoginView — username, secure password, terms checkbox (no state exposed), terms link to a web sheet, submit button, inline error label.
- Terms sheet (web) ids: Xong✓ 0d | Modal WKWebView opened from the login screen's terms link; content invisible to the accessibility tree; dismissed with "Xong".

## Failures
```

## `screens/home.md`

```markdown
---
title: Home (MainTabBarController)
type: screen
tags:
- home
- tabbar
summary: Post-login root — native tab bar with Trang chủ (selected) / Truyền hình / Cá nhân and a "Xin chào" greeting.
last_verified: 2026-07-23
---

# Home (MainTabBarController)

## Relations
- used-by [[Login flow (QA account → home)]]

## Observations
- [native] MainTabBarController: staticText "Xin chào" plus tab buttons "Trang chủ" (selected), "Truyền hình", "Cá nhân" #login
- [quirk] AppRouter.presentHome swaps the window rootViewController — the login screen is destroyed, not covered; there is no back navigation to it #login
- [identifier] home_hometab_button → mytvb2c/Sources/Home/MainTabBarController.swift:homeTab (viewDidLoad); verified-in-hierarchy 2026-07-23 #login
- [identifier] home_livetab_button → mytvb2c/Sources/Home/MainTabBarController.swift:liveTab (viewDidLoad); verified-in-hierarchy 2026-07-23 #login
- [identifier] home_profiletab_button → mytvb2c/Sources/Home/MainTabBarController.swift:profileTab (viewDidLoad); verified-in-hierarchy 2026-07-23 #login
- [quirk] The UITabBar container itself is NOT exposed in page_source — only the three tab buttons are. An accessibilityIdentifier set on `tabBar` never surfaces (tried "home_tab_bar", removed); assert on home_hometab_button / home_livetab_button / home_profiletab_button instead #login
- [quirk] home_hometab_button carries selected=true right after login — the Trang chủ tab is the default selection #login
```

## `screens/introduction.md`

```markdown
---
title: Introduction screen
type: screen
tags:
- login
- intro
summary: First screen after launch; native; "Đăng nhập ngay" / "Xem miễn phí"; triggers the notification permission alert.
last_verified: 2026-07-23
---

# Introduction screen

## Relations
- used-by [[Login flow (QA account → home)]]

## Observations
- [native] IntroductionContentViewController: staticTexts "Đăng nhập MyTV" / "Xem phim, truyền hình mọi lúc mọi nơi"; buttons "Đăng nhập ngay" and "Xem miễn phí" #login
- [quirk] viewDidLoad calls NotificationPermission.requestIfNeeded() → a SpringBoard-owned notification alert covers this screen on the first launch after a data wipe; it is outside the app hierarchy and must be dismissed before any app element is hittable #login
- [identifier] intro_login_button → mytvb2c/Sources/Login/IntroductionContentViewController.swift:btnLogin (viewDidLoad); verified-in-hierarchy 2026-07-23 #login
- [identifier] intro_free_button → mytvb2c/Sources/Login/IntroductionContentViewController.swift:btnFree (viewDidLoad); verified-in-hierarchy 2026-07-23 #login
- [quirk] The notification alert IS reachable from the app page_source in this setup: XCUIElementTypeButton name="Don't Allow" / name="Allow" — a test can dismiss it with a plain accessibility-id lookup, no springboard context switch needed #login
```

## `screens/login.md`

```markdown
---
title: Login screen
type: screen
tags:
- login
- auth
summary: Native LoginView — username, secure password, terms checkbox (no state exposed), terms link to a web sheet, submit button, inline error label.
last_verified: 2026-07-23
---

# Login screen

## Relations
- used-by [[Login flow (QA account → home)]]

## Observations
- [native] LoginView: staticText "Đăng nhập", textinput "Tên đăng nhập", secure textinput "Mật khẩu", checkbox "Tôi đồng ý với điều khoản sử dụng", button "Điều khoản sử dụng", button "Đăng nhập" #login
- [quirk] The terms checkbox exposes no checked/selected value in the hierarchy (UIImageView + tap gesture, image swap only) — never assert its state, just tap it once #login
- [quirk] The submit button reports enabled+hittable even before the terms box is ticked (code sets isEnabled=false, the live tree disagrees); tapping it then shows the inline guard error instead of submitting — never gate the test on is_enabled #login
- [quirk] The error staticText does not exist in the hierarchy until a submit fails (errorLabel is hidden until showError) — assert on its appearance, not its text being empty #login
- [quirk] Opening and dismissing the terms sheet preserves the typed credentials and the terms tick #login
- [identifier] login_username_field → mytvb2c/Sources/Login/LoginView.swift:usernameTextField (awakeFromNib); XCUIElementTypeTextField; verified-in-hierarchy 2026-07-23 #login
- [identifier] login_password_field → mytvb2c/Sources/Login/LoginView.swift:passwordTextField (awakeFromNib); XCUIElementTypeSecureTextField; verified-in-hierarchy 2026-07-23 #login
- [identifier] login_terms_checkbox → mytvb2c/Sources/Login/LoginView.swift:checkBoxTermImgView (awakeFromNib); surfaces as XCUIElementTypeOther; verified-in-hierarchy 2026-07-23 #login
- [identifier] login_terms_link_button → mytvb2c/Sources/Login/LoginView.swift:termsLink (awakeFromNib); verified-in-hierarchy 2026-07-23 #login
- [identifier] login_submit_button → mytvb2c/Sources/Login/LoginView.swift:btnLogin (awakeFromNib); verified-in-hierarchy 2026-07-23 #login
- [identifier] login_error_label → mytvb2c/Sources/Login/LoginView.swift:errorLabel (awakeFromNib); only present after a failed submit; verified-in-hierarchy 2026-07-23 #login
```

## `screens/terms.md`

```markdown
---
title: Terms sheet (web)
type: screen
tags:
- login
- web
summary: Modal WKWebView opened from the login screen's terms link; content invisible to the accessibility tree; dismissed with "Xong".
last_verified: 2026-07-23
---

# Terms sheet (web)

## Relations
- used-by [[Login flow (QA account → home)]]

## Observations
- [web] Terms sheet is a WKWebView; its page content is NOT exposed to the accessibility tree — only the native "Xong" bar button is visible to Appium; read content via screenshot if ever needed #login
- [quirk] Dismiss with the "Xong" bar button; returns to the login screen with field contents and the terms tick intact #login
- [identifier] Xong (dismiss) → native bar button, exposed as XCUIElementTypeButton name="Xong"; no custom identifier added; verified-in-hierarchy 2026-07-23 #login
```
