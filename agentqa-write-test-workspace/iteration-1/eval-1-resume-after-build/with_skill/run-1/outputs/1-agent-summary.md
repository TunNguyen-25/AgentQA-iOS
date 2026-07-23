# Login UI test — session summary

Resumed the `agentqa-write-test` run from `.agentqa/memory/.run-checkpoint.md`
(`current_step: 5`, `Blocker: WAITING_FOR_HUMAN_BUILD`) after the human built and
installed the app. Steps 0–5 were done in the previous session; this session ran
steps 6 → 9. Nothing was re-clarified and nothing was re-explored from scratch.

## What was done, in order

1. **Recalled the working layer** — read `.run-checkpoint.md` and
   `.session-requirement.md`, plus `config.yml`, `index.md`, `flows/login.md`,
   `screens/{intro,login_form,home}.md`, `failures/wda-timeout-under-load.md`,
   and the four Swift sources for the flow. Confirmed all 11 identifiers were
   present in `mytvb2c/Sources/` (already part of the `fixture baseline` commit,
   i.e. in the build the human installed).
2. **Checked green-loop preconditions** — simulator booted (iPhone 16 Pro,
   iOS 18.5), `com.vnpt.media.mobileb2c` installed, Appium up on 4723.
3. **Step 6 — verified every identifier in the live Appium hierarchy.** Wiped app
   data, launched with `agent-device`, dismissed the SpringBoard notifications
   alert with "Don't Allow" (the reviewer's pre-recorded decision in
   `.session-requirement.md` — not re-asked), then walked intro → login form →
   error states → home, pulling `page-source` at each stop.
   All 11 identifiers confirmed present:
   `login_intro_login_button`, `login_intro_free_button`, `login_username_field`,
   `login_password_field`, `login_terms_checkbox`, `login_terms_link`,
   `login_submit_button`, `login_error_label`, `home_home_tab`, `home_live_tab`,
   `home_profile_tab`. No missing identifiers, no false-confidence events
   (all were `added-unverified`, none previously `verified-in-hierarchy`).
4. **Refreshed memory after verification** — all 11 identifier observations moved
   from `added-unverified` to `verified-in-hierarchy 2026-07-23` via
   `memory-write.py propose` → `apply --op UPDATE`.
5. **Step 7 — wrote the page objects and the test** (first `.py` file of the run).
6. **Step 8 — ran the suite: 3 passed.** Re-ran a second time from the same clean
   state: 3 passed again (not dependent on leftover state).
7. **Review checkpoint** — presented the (empty) app-code diff and the test to the
   reviewer via `ask-user`. Reviewer approved: "Looks good, go ahead."
8. **Step 9 — capture** — deduped new/refreshed observations into memory, rebuilt
   `index.md`, recorded P0 metrics, deleted both Working-layer files, re-indexed
   CodeGraph (9 files / 34 symbols / 51 edges) after the simulator work finished.

## Divergence found (memory was wrong, live hierarchy was right)

Memory claimed the submit button is **disabled** until the terms checkbox is
ticked (`LoginView.swift` does set `btnLogin.isEnabled = false`). The live
hierarchy reports `login_submit_button enabled="true"` with terms unticked, and
pressing it surfaces the inline error `Vui lòng đồng ý với điều khoản sử dụng`.
Memory was refreshed to match reality and the test asserts the **error**, not a
disabled button. Raised with the reviewer, who approved.

## Files created

- `repo/AutomationTests/pages/base_page.py` — shared accessibility-id locator
  helpers (`wait_for`, `is_present`, `is_absent`, `label_of`); `is_absent`
  temporarily zeroes the implicit wait so negative assertions are cheap.
- `repo/AutomationTests/pages/intro_page.py` — `IntroPage`
- `repo/AutomationTests/pages/login_page.py` — `LoginPage`, incl. the two inline
  error strings read off the live hierarchy
- `repo/AutomationTests/pages/home_page.py` — `HomePage`, `missing_tabs()`
- `repo/AutomationTests/tests/test_login.py` — 3 tests:
  - `test_valid_credentials_land_on_home` (the confirmed assertion)
  - `test_wrong_password_shows_inline_error_and_stays_on_login` (the confirmed
    failure criteria: inline error, no modal, no bounce to intro)
  - `test_submit_without_accepting_terms_shows_terms_error` (edge case)

  Credentials come only from `APP_TEST_USERNAME` / `APP_TEST_PASSWORD`; the tests
  skip cleanly when either is unset. A function-scoped `intro` fixture does
  `terminate_app` + `activate_app` and tolerates the notifications alert being
  absent, so every test builds its own state under `reset_app_data: always`.

## Files changed

- `repo/.agentqa/memory/screens/{intro,login_form,home}.md` — 11 identifier
  observations refreshed to `verified-in-hierarchy 2026-07-23`; the
  `btnLogin.isEnabled` quirk corrected.
- `repo/.agentqa/memory/flows/login.md` — assertion and both edge cases refreshed
  with the covering test names; permission-alert quirk corrected (first launch
  after a privacy reset only, not every relaunch); new `[flow-step]` recording
  that terminate+activate returns to intro because no session is persisted.
- `repo/.agentqa/memory/env.md` — new gotcha: `reset-app-data.sh` reports
  "not installed — nothing to wipe" on this simulator; the conftest fixture
  (`simctl terminate` + `privacy reset all`) is what actually resets state.
- `repo/.agentqa/memory/index.md` — regenerated.

## Files deleted

- `repo/.agentqa/memory/.run-checkpoint.md`
- `repo/.agentqa/memory/.session-requirement.md`

Both are Working-layer files and are deleted at the end of the session per the
memory model.

## Repo state

- **No app-code changes in this session** — `git diff --numstat -- mytvb2c` is
  empty, so 0 deletions in app code.
- Nothing committed; everything left in the working tree for review.
  `git status`: 5 modified memory files + `index.md`, 5 untracked test files,
  and an untracked `.agentqa/metrics/` (P0-eval instrumentation).
- No credential values appear in any created or modified file (grep-verified).
- App is left installed and running on the booted simulator; Appium still up.
- CodeGraph index rebuilt at `repo/.codegraph/index.db`.

## Waiting on

Nothing. The flow is complete and the reviewer approved at the review checkpoint.
The only open judgement call, already surfaced and approved, is whether the
tappable-submit-with-terms-unticked behaviour should be filed as an app bug — the
reviewer said to go ahead as-is, so it is recorded as behaviour, not a defect.
