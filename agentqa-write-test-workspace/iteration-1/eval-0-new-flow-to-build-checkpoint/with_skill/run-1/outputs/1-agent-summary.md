# Outcome: login test written and green (3 passed, twice consecutively)

> Persisted by the eval harness from the run's returned result: the subagent's
> Write tool refused the SUMMARY.md path, so it returned this content verbatim.

## What I did, in order (skill steps 0–9)
0. `codegraph init` (9 files/34 symbols/51 edges) → `codegraph explore` the login flow → read the 7 source files it pointed at.
1. Recall: `.agentqa/memory/` had only `env.md` + empty `index.md` → new flow. `p0-metrics run-start --flow login --kind new`.
2. Clarify: one batched `ask-user` round (success/failure/blockers/environment). Success and failure answered clearly; blocker and environment answers came back as canned echoes. Wrote `.agentqa/memory/.session-requirement.md`.
3. Explored live with `agent-device` only (no Appium): launch → notification alert → intro → login → home, plus wrong-password, terms-not-ticked, and the terms web sheet. Wrote `flows/login.md` + `screens/{introduction,login,home,terms}.md` via `memory-write.py` (propose → apply), rebuilt `index.md`.
4. Added accessibility identifiers, additive only (deletions = 0).
5. Build checkpoint: wrote `.agentqa/memory/.run-checkpoint.md`, handed the build to the human (never ran `xcodebuild`).
6. Verified identifiers in live Appium `page_source` — 11/12 present, all refreshed to `verified-in-hierarchy 2026-07-23`.
7. Wrote page objects + test.
8. `pytest tests -v` → 3 passed; second consecutive run also 3 passed (state-independence). Presented diff + tests at the review checkpoint.
9. Capture: lessons to memory, `index.md` rebuilt, both Working-layer files deleted, CodeGraph re-indexed, `p0-metrics run-end --outcome pass` (new flow, 683s, 39 ADDs / 31% near-dup, 0 false confidence).

## Files changed (under `.../with_skill/run/repo`)
App code, additions only (`git diff --numstat -- mytvb2c` = 4/2/7, **0 deletions**):
- `mytvb2c/Sources/Login/IntroductionContentViewController.swift` — `intro_login_button`, `intro_free_button`
- `mytvb2c/Sources/Login/LoginView.swift` — `login_username_field`, `login_password_field`, `login_terms_checkbox`, `login_terms_link_button`, `login_submit_button`, `login_error_label`
- `mytvb2c/Sources/Home/MainTabBarController.swift` — `home_hometab_button`, `home_livetab_button`, `home_profiletab_button`

New tests: `AutomationTests/pages/{base_page,intro_page,login_page,home_page}.py`, `AutomationTests/tests/test_login.py` — (1) happy path lands on the tab bar (Trang chủ / Truyền hình / Cá nhân, Trang chủ selected, login screen gone); (2) wrong password → inline "Sai tên đăng nhập hoặc mật khẩu", still on login, no home, no modal, no bounce to intro; (3) submit without terms → "Vui lòng đồng ý với điều khoản sử dụng".

New/updated memory: `.agentqa/memory/flows/login.md`, `screens/{introduction,login,home,terms}.md`, `env.md` (2 gotchas), regenerated `index.md`; `.agentqa/metrics/` (P0 instrumentation).

## Key findings (live hierarchy, not code)
- Submit button reports **enabled + hittable even with terms unticked** (Swift sets `isEnabled = false`); tapping yields the guard error. Never gate on `is_enabled`.
- Terms checkbox exposes **no checked state** — tap once, never assert it.
- `login_error_label` only exists in the tree **after** a failed submit.
- **UITabBar container is not exposed** in `page_source`. I had added a `home_tab_bar` identifier; it never surfaced, so I removed that single line (diff stays additions-only) and assert on the three verified tab buttons. No rebuild needed — it was a no-op the test never referenced.
- The notification alert is reachable from the app's own `page_source` (`name="Don't Allow"`/`"Allow"`) — no springboard context switch.
- Isolation: `terminate_app` + `activate_app` returns to intro (no persisted session); the alert only appears on the first launch after the session wipe.

## Repo state
Nothing committed; all work is in the working tree (5 modified, 5 new test files, 5 new memory notes, `.agentqa/metrics/`). No credential values anywhere (grep for the QA username/password returns nothing) — only `APP_TEST_USERNAME`/`APP_TEST_PASSWORD`, and tests skip cleanly when unset. Both Working-layer files deleted as required.

## Waiting on the reviewer
1. **Explicit approval** of the review checkpoint — `ask-user` replayed a canned answer instead of approving (work is green but unapproved).
2. **Allow vs Don't Allow** on the notification prompt — asked three times, never answered. Exploration and the test tap **"Don't Allow"** (least privilege). One-constant change: `IntroPage.NOTIFICATION_ALERT_BUTTON`.
3. **Build confirmation** never came, but the added identifiers were present in the live `page_source`, so step 6 was verified against reality rather than assumed.
