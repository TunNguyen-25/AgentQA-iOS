# AgentQA Studio — local dashboard design

**Date:** 2026-07-24
**Status:** Approved (design) — implementation plan pending

## Problem

AgentQA today is driven entirely from the terminal through two skills
(`agentqa-init`, `agentqa-write-test`). Everything the agent learns and does —
the memory store, test runs, the human-in-the-loop checkpoints — is visible only
as scrolling terminal text. There is no single surface to *see* the state of the
rig, run a test with one click, browse what the agent has learned, or answer the
agent's checkpoint questions without reading them out of a wall of output.

AgentQA Studio is a **local web dashboard** that gives that surface. It does not
replace the agent — it is a window onto the agent and a control panel for it.

## Core architecture — two halves with different lifetimes

The dashboard splits cleanly along one fact: **Claude Code is turn-based, not a
resident daemon.** A background web server can stay up for hours; an agent's
*thinking* only happens while a Claude session is open and attending to it.

- **Half A — always-on, no AI:** run pytest, tail output, browse
  `flows/`/`screens/`/`failures/`, run `memory-index`/`memory-lint`, check the
  rig (simulator, Appium, CodeGraph). Plain Python. Runs as a persistent daemon.
- **Half B — needs a live brain:** write a test, diagnose a failure, answer the
  clarify questions. Only works while an agent is attached.

This is why the product is **a CLI daemon plus a connector skill**, not one or
the other.

```
  agentqa studio  ──►  THE dashboard (the real thing)
   (CLI daemon)        web server + browser UI. Stays up on its own.
                       Runs tests, browses memory, checks the rig — Half A.
                              ▲
                              │  shared file "mailbox" in .agentqa/studio/
                              ▼
  /agentqa-studio  ──►  THE connector (a live brain)
    (skill)             a Claude session that attaches to the running dashboard,
                        watches for jobs, does Half B, posts messages back.
```

The dashboard runs with **no** agent attached — the AI features simply show "no
agent connected." An agent can attach or detach at any time without restarting
the dashboard. The two communicate only through plain files, the same ethos as
the rest of the memory layer.

## Components

### 1. `agentqa studio` — the daemon (the real dashboard)

- Python, reusing the project's existing virtualenv.
- **Stdlib `http.server` (threaded, for SSE) + a vanilla-JS single-page UI.** No
  Flask, no npm, no build step. Chosen for debuggability and zero new
  toolchain — consistent with the plain-file memory layer.
- Reads `.agentqa/config.yml` for platform, `bundle_id`/`app_package`,
  `test_dir`, `build.policy`, `reset_app_data`, credential env-var *names*, and
  the Appium port.
- Serves the UI and a small set of endpoints:
  - preconditions check (sim booted, app installed, Appium up on the config
    port, CodeGraph indexed)
  - list tests under `<test_dir>/tests/`
  - run pytest (full suite / one file) with output streamed to the browser
  - read memory notes (`flows/`, `screens/`, `failures/`, `env.md`)
  - run `memory-index.py` (incl. `--stale`) and `memory-lint.py`
  - the mailbox (post a job; stream messages back)
- Credential values are **never stored**: when a run needs them, the browser
  prompts using the env-var *names* from the config and passes them through for
  that run only.

### 2. The mailbox — `.agentqa/studio/` (gitignored)

Transient, session-scoped state — treated like the working-layer files
(`.session-requirement.md`, `.run-checkpoint.md`) and gitignored.

- `inbox.jsonl` — browser → agent. Job types: `write-test`, `diagnose`,
  `clarify-answer`, `build-done`, `review-decision`.
- `outbox.jsonl` — agent → browser. Message types: `progress`, `question`
  (clarify / build / review), `diff`, `result`, `error`.
- Append-only JSONL. The browser tails `outbox.jsonl` over SSE; the attached
  agent polls `inbox.jsonl`. A small `state.json` holds current run status
  (idle / running / waiting-on-user) and whether an agent is attached.

Each record carries an `id`, `ts`, `type`, and a `type`-specific payload. A
`question` from the agent is answered by a matching `clarify-answer` /
`build-done` / `review-decision` record referencing the question `id`.

### 3. `/agentqa-studio` — the connector skill

- **Built via the `skill-creator` skill** (explicit constraint — see below).
- Boots the daemon if it is not already running, then enters a watch loop:
  read `inbox.jsonl` → do the work using the existing `agentqa-write-test` flow
  and green loop → post to `outbox.jsonl`.
- The three human-in-the-loop checkpoints in the write-test flow become browser
  cards instead of terminal prompts:
  - **Clarify (step 2):** success / failure / blockers → answered in the browser.
  - **Build checkpoint (step 5):** `WAITING_FOR_HUMAN_BUILD` → an "I've built &
    installed" button.
  - **Review (step 8):** app-code diff (additions only) + the test → Approve /
    reject.
- A thin skill: it delegates the actual test-writing to the logic that already
  exists; its own job is the attach + watch + post-back loop.

## Panels (UI)

| # | Panel | Half | Milestone |
|---|---|---|---|
| 1 | **Status bar** — sim booted · app installed · Appium up · CodeGraph indexed · config summary | A | M1 |
| 2 | **Test runner** — list tests, run suite/file, streamed output, failure artifact (`failed_<test>.xml` + `.png`) inline | A | M1 |
| 3 | **Agent conversation** — "Write a test for ___" box, live agent messages, the 3 checkpoint cards | B | M2 |
| 4 | **Memory browser** — `flows`/`screens`/`failures` as cards, `--stale` list, `lint` health (read-only) | A | M1 |
| 5 | Session inspector — live `.session-requirement.md` / `.run-checkpoint.md` | A | Deferred |

## Scope — two milestones

- **M1 — Dashboard, no agent needed.** Daemon + panels 1, 2, 4. A working,
  useful tool on its own: see the rig, run tests, browse memory. No mailbox, no
  skill.
- **M2 — Agent bridge.** Mailbox + connector skill + panel 3 + the three
  checkpoints. Turns the viewer into the full Option A experience.

## Constraints

- **`skill-creator` for the skill.** When the `/agentqa-studio` skill is created,
  it goes through the `skill-creator` skill — not hand-rolled.
- **No commits or pushes.** All work stays local. When a step would normally
  commit (e.g. this design doc), stop and tell the user instead.

## Out of scope (YAGNI)

- Editing memory notes from the UI (the agent owns writing, guarded by
  `memory-write.py`'s propose→apply).
- A code editor for tests.
- Multi-project support.
- Auth / user accounts.
- Headless-spawn model (dashboard launching its own `claude -p` per job — the
  "Option C" we set aside as too complex). Half B stays skill-attached for now.
- Auto-woken `/loop` agent for v1 — the agent attaches via the skill the user
  invokes.

## Decisions locked

- Stdlib `http.server` + vanilla JS, no framework / no build.
- Mailbox = two append-only JSONL files under `.agentqa/studio/`, gitignored.
- Agent attaches via an invoked skill (not an auto-woken loop) in v1.
- Ship M1 first (usable without an agent), then M2.
