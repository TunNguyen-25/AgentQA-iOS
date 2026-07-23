---
name: agentqa-init
description: Install and validate the agent-driven mobile UI testing toolchain (Appium 2.x + XCUITest, agent-device, CodeGraph, basic-memory, the Appium MCP, a Python venv), and configure an app repo for it — .agentqa/config.yml, a runnable pytest suite, and an empty behavioral-memory store. Use when setting up the machine or onboarding a repo for automated iOS UI tests. Invoked as /agentqa-init setup or /agentqa-init init. Writing tests is the separate /agentqa-write-test skill.
license: MIT
compatibility: macOS with Xcode and an iOS simulator; requires Node.js and Python 3.9+; npm network access for installs
metadata:
  agentqa-init-version: "1.0.0"
---

# agentqa-init — toolchain setup & project configuration

Two subcommands. The first word of the arguments selects one; read ONLY the
matching reference file and follow it.

| Subcommand | Also accepts | Read | Purpose |
|---|---|---|---|
| `setup` | `install` | [references/setup.md](references/setup.md) | Install/validate the toolchain on this machine (once per machine) |
| `init` | `config` | [references/init.md](references/init.md) | Configure a project: `.agentqa/config.yml`, test-suite scaffold, empty memory store (once per repo) |

No subcommand, or an unrecognized one → show the table above and ask which to
run. A fresh machine + fresh repo wants `setup` then `init`, in that order.

## What this skill does NOT do

It never writes, runs, or diagnoses a test — it only makes those possible.

- **Writing / running a test** → the **`agentqa-write-test`** skill
  (`/agentqa-write-test <idea>`), which owns the memory schema, the clarify
  checklist, the sub-agents, and the green loop.

Once `setup` and `init` are green, hand off — don't start exploring the app or
drafting tests here.

## Project configuration (both subcommands)

Project facts live in `.agentqa/config.yml` at the host repo root — bundle
id, test directory, build policy, credential env var names, identifier
convention. It is written by `init` and read by every other skill. Never
hardcode project facts in tests, and never commit credentials — accounts flow
through the env vars named in the config.

Behavioral knowledge lives in `.agentqa/memory/`, scaffolded empty by `init`
(`scripts/scaffold-memory.sh`). The note **schema** belongs to the
`agentqa-write-test` skill (`references/memory-model.md` there) because that's
what fills the store; `init` only creates the folders and seeds `env.md`. Never
pre-seed notes here — memory holds runtime-verified facts only.

## Build policy (record it, respect it)

`build.policy` in the config decides who builds the app:
- `human` — stop after any app-code change and ask the user to build &
  install onto the booted simulator; never run xcodebuild for the app.
- `agent` — the agent may build/install itself.

`init` asks for this and writes the rationale into `.agentqa/memory/env.md`.

## Reset policy (record it, respect it)

`reset_app_data` in the config decides whether the app's local data is wiped
before every launch:
- `always` — **the default.** Each pytest session (`conftest.py`) and each
  `agent-device open` during exploration starts from an empty data container
  (`Documents/`, `Library/` incl. NSUserDefaults, `tmp/`) with privacy grants
  reset. Deterministic runs; no state leaking between tests.
- `never` — local state survives across launches. Only for apps where
  re-establishing state is expensive.

The app is **never uninstalled** — a human-installed build survives a reset — and
the simulator-wide keychain is not wiped. `scripts/reset-app-data.sh` is the one
implementation for non-pytest launches; `AGENTQA_RESET_APP_DATA=never|always`
overrides the config for a single run.
