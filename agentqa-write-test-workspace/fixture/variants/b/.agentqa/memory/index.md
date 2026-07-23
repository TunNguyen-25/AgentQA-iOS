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
