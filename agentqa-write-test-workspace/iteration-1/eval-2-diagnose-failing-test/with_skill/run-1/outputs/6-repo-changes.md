# Repo changes

## git diff --numstat

```
2	0	.agentqa/memory/flows/login.md
6	9	.agentqa/memory/index.md
```

## New files

```
.agentqa/memory/failures/device-register-404-blocks-login.md
.agentqa/metrics/README.md
.agentqa/metrics/events.jsonl
.agentqa/metrics/summary.md
```

## Full diff

```diff
diff --git a/.agentqa/memory/flows/login.md b/.agentqa/memory/flows/login.md
index b899d7a..c650f5a 100644
--- a/.agentqa/memory/flows/login.md
+++ b/.agentqa/memory/flows/login.md
@@ -19,8 +19,10 @@ last_verified: 2026-07-23
 - [native] intro, login and home are native UIKit #login
 - [web] the terms sheet is a WKWebView with no native nodes — screenshot only #login
 - [quirk] the permission alert is owned by SpringBoard and appears on every wiped launch #login
+- [quirk] verify-delta 2026-07-23 (staging): the manual agent-device walkthrough intro→login→home still passes with valid credentials, so a red suite here points at the backend, not at the nav path #login
 
 ## Relations
 - covers [[intro]]
 - covers [[login_form]]
 - covers [[home]]
+- diagnosed-by [[device-register-404-blocks-login]]
diff --git a/.agentqa/memory/index.md b/.agentqa/memory/index.md
index 4fc1f6e..16e5007 100644
--- a/.agentqa/memory/index.md
+++ b/.agentqa/memory/index.md
@@ -1,16 +1,13 @@
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
+- device-register-404-blocks-login → staging POST /device/register 404 → modal "THÔNG BÁO … (58)" over the intro screen, login unreachable — a real defect, not a flake
+- wda-timeout-under-load → WebDriverAgent session timeout when the host is CPU-saturated
```