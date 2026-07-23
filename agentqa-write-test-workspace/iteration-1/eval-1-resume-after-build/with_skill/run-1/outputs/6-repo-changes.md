# Repo changes

## git diff --numstat

```
1	0	.agentqa/memory/env.md
5	4	.agentqa/memory/flows/login.md
5	9	.agentqa/memory/index.md
3	3	.agentqa/memory/screens/home.md
2	2	.agentqa/memory/screens/intro.md
7	7	.agentqa/memory/screens/login_form.md
```

## New files

```
.agentqa/metrics/README.md
.agentqa/metrics/events.jsonl
.agentqa/metrics/summary.md
AutomationTests/pages/base_page.py
AutomationTests/pages/home_page.py
AutomationTests/pages/intro_page.py
AutomationTests/pages/login_page.py
AutomationTests/tests/test_login.py
```

## Full diff

```diff
diff --git a/.agentqa/memory/env.md b/.agentqa/memory/env.md
index 7b237cc..c5f2b98 100644
--- a/.agentqa/memory/env.md
+++ b/.agentqa/memory/env.md
@@ -17,3 +17,4 @@ credential env-var **names** only.
 - [gotcha] The human reviewer is reachable only through the `ask-user` helper on PATH: `ask-user "<question>"` prints their answer. Interactive prompts do not reach them.
 - [credential-env] APP_TEST_USERNAME, APP_TEST_PASSWORD
 - [build-policy] Manual builds required — signing and package configuration require human intervention (build.policy: human)
+- [gotcha] agentqa-init reset-app-data.sh reports "not installed — nothing to wipe" on this simulator (no data container resolved); the conftest session fixture (simctl terminate + privacy reset all) is what actually resets state, which is why the notifications alert appears on the first launch of each pytest session
diff --git a/.agentqa/memory/flows/login.md b/.agentqa/memory/flows/login.md
index b899d7a..3e7a9ec 100644
--- a/.agentqa/memory/flows/login.md
+++ b/.agentqa/memory/flows/login.md
@@ -13,14 +13,15 @@ last_verified: 2026-07-23
 - [flow-step] IntroductionContentViewController → press "Đăng nhập ngay" → LoginViewController #login
 - [flow-step] fill username + password, tick "Tôi đồng ý với điều khoản sử dụng", press "Đăng nhập" #login
 - [flow-step] success → MainTabBarController with tab bar Trang chủ / Truyền hình / Cá nhân #login
-- [assertion] valid credentials + terms ticked lands on the home tab bar #login
-- [edge-case] wrong credentials → inline "Sai tên đăng nhập hoặc mật khẩu" under the password field, stays on login #login
-- [edge-case] terms unticked → "Vui lòng đồng ý với điều khoản sử dụng", submit is disabled #login
+- [assertion] valid credentials + terms ticked lands on the home tab bar (Trang chủ / Truyền hình / Cá nhân) — covered by AutomationTests/tests/test_login.py::test_valid_credentials_land_on_home, green 2026-07-23 #login
+- [edge-case] wrong credentials → inline "Sai tên đăng nhập hoặc mật khẩu" in login_error_label, stays on login, no modal, no bounce to intro — covered by test_wrong_password_shows_inline_error_and_stays_on_login #login
+- [edge-case] terms unticked → submit is still tappable; pressing it shows "Vui lòng đồng ý với điều khoản sử dụng" in login_error_label and stays on login #login
 - [native] intro, login and home are native UIKit #login
 - [web] the terms sheet is a WKWebView with no native nodes — screenshot only #login
-- [quirk] the permission alert is owned by SpringBoard and appears on every wiped launch #login
+- [quirk] the SpringBoard notifications alert appears only on the first launch after the app privacy grants are reset — later terminate+activate relaunches in the same session do not re-prompt #login
 
 ## Relations
 - covers [[intro]]
 - covers [[login_form]]
 - covers [[home]]
+- [flow-step] terminate + activate returns to the intro screen — no session is persisted (AppRouter only swaps the in-memory root VC), so each test can relaunch to build its own state #login
diff --git a/.agentqa/memory/index.md b/.agentqa/memory/index.md
index 4fc1f6e..c639ac1 100644
--- a/.agentqa/memory/index.md
+++ b/.agentqa/memory/index.md
@@ -1,16 +1,12 @@
 # Memory index (compact — detail files loaded on demand)
 
 ## Flows
-- **login** — Intro → login form → home tab bar, gated on a terms checkbox
-  - covers: intro, login_form, home
+- login → Intro → login form → home tab bar, gated on a terms checkbox | detail: flows/login.md
 
 ## Screens
-- **intro** — IntroductionContentViewController — login / guest entry point
-- **login_form** — LoginView — username, password, terms checkbox, submit
-- **home** — MainTabBarController — the post-login landing surface
+- home ids: home_home_tab✓ 0d, home_live_tab✓ 0d, home_profile_tab✓ 0d | MainTabBarController — the post-login landing surface
+- intro ids: login_intro_free_button✓ 0d, login_intro_login_button✓ 0d | IntroductionContentViewController — login / guest entry point
+- login_form ids: login_error_label✓ 0d, login_password_field✓ 0d, login_submit_button✓ 0d, login_terms_checkbox✓ 0d, login_terms_link✓ 0d, login_username_field✓ 0d | LoginView — username, password, terms checkbox, submit
 
 ## Failures
-- **wda-timeout-under-load** — WebDriverAgent session timeout when the host is CPU-saturated
-
-## Env
-- env.md — build policy, credential env-var names, simulator gotchas
+- wda-timeout-under-load → WebDriverAgent session timeout when the host is CPU-saturated
diff --git a/.agentqa/memory/screens/home.md b/.agentqa/memory/screens/home.md
index 00a7996..722cc85 100644
--- a/.agentqa/memory/screens/home.md
+++ b/.agentqa/memory/screens/home.md
@@ -10,9 +10,9 @@ last_verified: 2026-07-23
 
 ## Observations
 - [native] MainTabBarController with three tabs #login
-- [identifier] home_home_tab → MainTabBarController.homeTab; added-unverified 2026-07-23 #login
-- [identifier] home_live_tab → MainTabBarController.liveTab; added-unverified 2026-07-23 #login
-- [identifier] home_profile_tab → MainTabBarController.profileTab; added-unverified 2026-07-23 #login
+- [identifier] home_home_tab → MainTabBarController.homeTab; verified-in-hierarchy 2026-07-23 #login
+- [identifier] home_live_tab → MainTabBarController.liveTab; verified-in-hierarchy 2026-07-23 #login
+- [identifier] home_profile_tab → MainTabBarController.profileTab; verified-in-hierarchy 2026-07-23 #login
 
 ## Relations
 - used-by [[login]]
diff --git a/.agentqa/memory/screens/intro.md b/.agentqa/memory/screens/intro.md
index c22bee2..4931225 100644
--- a/.agentqa/memory/screens/intro.md
+++ b/.agentqa/memory/screens/intro.md
@@ -10,8 +10,8 @@ last_verified: 2026-07-23
 
 ## Observations
 - [native] IntroductionContentViewController, UIKit xib #login
-- [identifier] login_intro_login_button → IntroductionContentViewController.btnLogin; added-unverified 2026-07-23 #login
-- [identifier] login_intro_free_button → IntroductionContentViewController.btnFree; added-unverified 2026-07-23 #login
+- [identifier] login_intro_login_button → IntroductionContentViewController.btnLogin; verified-in-hierarchy 2026-07-23 #login
+- [identifier] login_intro_free_button → IntroductionContentViewController.btnFree; verified-in-hierarchy 2026-07-23 #login
 - [quirk] requests notification permission in viewDidLoad, so the alert covers this screen on a wiped launch #login
 
 ## Relations
diff --git a/.agentqa/memory/screens/login_form.md b/.agentqa/memory/screens/login_form.md
index ff08ee7..970a11c 100644
--- a/.agentqa/memory/screens/login_form.md
+++ b/.agentqa/memory/screens/login_form.md
@@ -10,13 +10,13 @@ last_verified: 2026-07-23
 
 ## Observations
 - [native] LoginView loaded from a nib by LoginViewController #login
-- [identifier] login_username_field → LoginView.usernameTextField; added-unverified 2026-07-23 #login
-- [identifier] login_password_field → LoginView.passwordTextField; added-unverified 2026-07-23 #login
-- [identifier] login_terms_checkbox → LoginView.checkBoxTermImgView; added-unverified 2026-07-23 #login
-- [identifier] login_terms_link → LoginView.termsLink; added-unverified 2026-07-23 #login
-- [identifier] login_submit_button → LoginView.btnLogin; added-unverified 2026-07-23 #login
-- [identifier] login_error_label → LoginView.errorLabel; added-unverified 2026-07-23 #login
-- [quirk] btnLogin.isEnabled is driven by termsAccepted — the checkbox must be tapped before submit #login
+- [identifier] login_username_field → LoginView.usernameTextField; verified-in-hierarchy 2026-07-23 #login
+- [identifier] login_password_field → LoginView.passwordTextField; verified-in-hierarchy 2026-07-23 #login
+- [identifier] login_terms_checkbox → LoginView.checkBoxTermImgView; verified-in-hierarchy 2026-07-23 #login
+- [identifier] login_terms_link → LoginView.termsLink; verified-in-hierarchy 2026-07-23 #login
+- [identifier] login_submit_button → LoginView.btnLogin; verified-in-hierarchy 2026-07-23 #login
+- [identifier] login_error_label → LoginView.errorLabel; verified-in-hierarchy 2026-07-23 #login
+- [quirk] btnLogin.isEnabled reports enabled=true in the live hierarchy even with terms unticked — do not gate on isEnabled; pressing submit unticked shows login_error_label "Vui lòng đồng ý với điều khoản sử dụng" #login
 - [quirk] errorLabel is hidden until showError(_:) runs #login
 
 ## Relations
```