# The memory layer

AgentQA remembers what it learns about your app so the next test run doesn't
start from zero. This page explains how that works.

It deliberately does **not** define the note format — that lives in one place,
[`memory-model.md`](../skills/agentqa-write-test/references/memory-model.md).
Read this to understand the shape; read that to write a note.

## What memory is for

Source code tells you what the app *should* do. Memory records what it *actually
did* when the agent drove it: the real navigation path, which screens turned out
to be web views, where an accessibility identifier really lives, what a flaky
failure looked like last time.

That knowledge is expensive — it costs a live exploration run to earn — and it
can't be regenerated from the code. (Code-level knowledge is CodeGraph's job, and
that *is* regenerated, which is why none of it is stored here.)

## The four layers

```
  ┌─ docs: (optional) ────────────── intent ── read-only, never written
  │     your SRDs, PM scenarios, acceptance criteria
  │
  ├─ .agentqa/memory/ ────────────── knowledge ── committed, permanent
  │     flows/  screens/  failures/  env.md
  │        │
  │        └─→ index.md ─────────── derived ── generated, gitignored
  │
  └─ .session-requirement.md ─────── session ── gitignored, deleted at the end
     .run-checkpoint.md
```

| Layer | Lives in | Lifetime | Holds |
|---|---|---|---|
| **1. Knowledge** | `flows/`, `screens/`, `failures/`, `env.md` | Forever, committed | What the agent observed in the live app |
| **2. Index** | `index.md` | Rebuilt on demand | A one-line-per-note view, for fast lookup |
| **3. Session** | `.session-requirement.md`, `.run-checkpoint.md` | One run | What you asked for, and where the run got to |
| **4. Intent** | Whatever `docs:` points at | Yours | What the app was *meant* to do |

Only layer 1 is written by the agent as durable knowledge. Layer 2 is disposable.
Layer 3 is thrown away when the run ends. Layer 4 is never written at all.

### Why the session layer is separate

Two things happen mid-run that would otherwise corrupt the store.

A run pauses for you to build the app — that's a context break, and the agent has
to come back knowing what it was doing. That's `.run-checkpoint.md`.

And a spec might claim "wrong password shows an inline error" when the shipped app
actually bounces to the start screen. Until the agent has *seen* it, that claim is
a rumour. It sits in `.session-requirement.md` and dies with the session. Only
things confirmed against the running app graduate into `flows/` and `screens/`.

This is the whole reason for the split: everything in layer 1 was earned by
driving the app, so a later run can trust it as a map.

## How retrieval works

At the start of a run:

```bash
# 1. rebuild the index (it's generated, so it's always current)
python3 scripts/memory-index.py .agentqa/memory

# 2. load only this flow's slice
python3 scripts/memory-index.py .agentqa/memory --flow login

# 3. check what's gone stale
python3 scripts/memory-index.py .agentqa/memory --stale
```

Step 2 is the important one. It returns the `login` flow note, every screen
tagged `#login`, and the full failure list — not the two hundred screens you've
explored over the past year. **The `#flow` tag on each observation is what makes
this work.** An untagged observation is stored but unfindable, which is why the
skill tags everything it writes.

Failures are deliberately *not* scoped: a phantom signature learned on checkout is
exactly what you want when login times out the same way.

Step 3 lists identifiers nobody has confirmed in over 30 days, each with the exact
`file:line` to update. Age is computed from the date on the note, never declared,
so it can't disagree with the calendar.

### Recall is a map, not an oracle

Everything recalled is treated as a **claim**, then checked against the live app —
the "verify-delta" pass. The agent walks the known path, confirms the waypoints it
expects, and only digs in where reality has diverged. That's what makes a repeat
run fast without making it wrong.

When sources disagree, the order is fixed:

> **live app > memory > source code > docs**

A doc is the weakest because it describes intent, which can be months out of date.
The live hierarchy is strongest because it's the only thing that can't be wrong
about itself.

## How writing works

Capture is two-phase, on purpose:

```bash
# 1. see what's already there
python3 scripts/memory-write.py propose --note screens/login \
    --category quirk --text "submit sits under the keyboard #login"

# 2. decide, then write
python3 scripts/memory-write.py apply --op ADD --note screens/login \
    --category quirk --text "submit sits under the keyboard #login"
```

`propose` prints the three most similar existing observations so you don't append
a fourth copy of a fact already recorded. The matching is textual — it reliably
catches restatements and will miss the same fact worded differently — so it's a
prompt to look, not a guarantee.

When reality has changed, `--op UPDATE` rewrites the observation in place instead
of appending a contradiction. The store wants to be under git so a wrong edit is
one `git checkout HEAD -- .agentqa/memory` away.

### What the writer refuses

These are all silent-corruption failures — the store keeps looking healthy while
answering less and less:

| Refused | Why |
|---|---|
| Writing to `index.md` | Regenerated; your edit disappears on the next rebuild |
| Writing to a session file | Puts an unverified claim where later runs read it as fact |
| Any path outside the four locations | Recall never looks there |
| An unknown category (`[quirck]`) | The fact drops out of every query built on the schema |
| A malformed identifier line | Staleness reporting skips it, so it stops being re-verified |
| A literal password or API token | The store is committed — that's git history |

`memory-lint.py` runs the same checks over the whole store, plus frontmatter and
tagging. `/agentqa-init init --check` runs it for you.

## In one paragraph

Four layers: permanent knowledge, a disposable index over it, one session's
scratch state, and your own docs as read-only intent. Retrieval rebuilds the index
and pulls just the current flow's slice by tag, then re-checks it against the
running app rather than trusting it. Writing goes through a propose-then-apply
step that shows you near-duplicates and refuses the edits that quietly break the
store.
