# /agentqa-init init — configure a project for agent-driven UI testing

Goal: a `.agentqa/config.yml` at the host repo root plus a runnable (empty)
test suite. Idempotent — if pieces exist, keep them and fill only the gaps.

## 1. Gather the facts (ask the user; don't guess)

- **Bundle id** of the app under test (for iOS you can list installed apps on
  a booted simulator: `xcrun simctl listapps booted`).
- **Test directory** name (default `AutomationTests`).
- **Build policy**: `human` (agent stops and asks the user to build & install
  — right choice when CLI builds are slow or signing is involved) or `agent`.
- **Reset local app data on every launch?** `always` (**default** — recommend it;
  every test session and every explore launch starts from a wiped data container,
  so runs are deterministic and one test can't inherit another's state) or `never`
  (keep state between launches — pick it only when re-establishing state is
  expensive, e.g. a manual login the tests can't redo). The binary is never
  uninstalled, so a human-installed build survives; the keychain is
  simulator-wide and is not wiped either.
- **Credential env var names** the tests will read (e.g. `APP_TEST_USERNAME`).
  Values are never stored anywhere — only the names.
- **Identifier convention** (recommend `screen_element_type`, lowercase
  snake_case: `login_phone_field`, `home_profile_button`; suffixes `field`,
  `button`, `label`, `alert`, `tab`, `cell`).

## 2. Write the config

Copy [assets/config.template.yml](../assets/config.template.yml) to
`.agentqa/config.yml` in the repo root and fill in the answers.

## 3. Scaffold the test suite (if the test dir doesn't exist)

Copy the files from [assets/scaffold/](../assets/scaffold/) into the test
directory:

- `conftest.py` — Appium driver fixture: auto-detects the booted simulator,
  reads the bundle id from the config (or `AGENTQA_BUNDLE_ID`), attaches
  with `noReset`, wipes the app's data container when `reset_app_data` is
  `always` (config, or `AGENTQA_RESET_APP_DATA` to override per run),
  cold-starts the app, and saves page_source + screenshot automatically on any
  test failure.
- `requirements.txt`, `pytest.ini`, `.gitignore` — pinned deps, defaults.
- Create empty `pages/` (+ `__init__.py`), `tests/`, `notes/` directories.

Then create the venv: `scripts/setup-python-env.sh` (from this skill).

**Re-running `init` on a repo scaffolded by an older version:** keep the project's
own files, but fill the gaps — add any missing key to `.agentqa/config.yml`
(`reset_app_data` first; without it the default `always` still applies) and diff
the scaffold's `conftest.py` against the project's. It is generated, not
hand-edited: if the project hasn't customized it, re-copy it so the reset policy
takes effect; if it has, port the change and say what you moved.

## 4. Bootstrap the memory store

Create `.agentqa/memory/` (behavioral knowledge; the note schema lives in the
`agentqa-write-test` skill's `references/memory-model.md` — you don't need it
here, `init` only creates the empty store) by running the scaffold script from
this skill:

```bash
scripts/scaffold-memory.sh            # from the host repo root
```

It creates `flows/`, `screens/`, `failures/` and seeds `env.md` + a fallback
`README.md`. The store **starts empty** — `/agentqa-write-test` fills `screens/` with
runtime-verified facts as flows are actually explored, so every note is grounded
in `page_source`. Never pre-seed `screens/` from the CodeGraph index: those
claims are unverified and a real build can contradict them (feature flags, web
SSO replacing native screens).

Then fill `env.md`'s placeholders from the config: the build-policy rationale and
the credential env-var **names** (names only, never values). Add a short pointer
in the repo's agent docs (`CLAUDE.md`/`AGENTS.md`) to `.agentqa/memory/` — the
memory is the home for narrative knowledge; `config.yml` stays the home for
structured facts. Do not duplicate facts across the two.

## 5. Reset policy outside pytest

`conftest.py` handles pytest runs. Launches that don't go through pytest — the
`agent-device open` calls `/agentqa-write-test` makes while exploring — reset via
the same mechanism, this skill's `scripts/reset-app-data.sh`:

```bash
scripts/reset-app-data.sh          # bundle id from .agentqa/config.yml
```

It terminates the app, empties its data container (`Documents/`, `Library/`
including NSUserDefaults, `tmp/`) and resets its privacy grants — without
uninstalling the binary, so a `build.policy: human` build stays installed. When
`reset_app_data: never`, nobody calls it.

## 6. Verify

`scripts/setup-all.sh --check` should end all green, and
`pytest --collect-only` inside the test dir should succeed (0 tests is fine).
- `scripts/scaffold-memory.sh --check` should print `memory scaffold: OK`.
