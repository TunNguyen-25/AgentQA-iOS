# agentqa memory model — behavioral knowledge store

Shared reference for every subcommand that reads or writes `.agentqa/memory/`.
Read this before touching memory; don't re-derive the schema.

Memory persists **behavioral** knowledge the skill hand-earns at runtime — real
navigation paths, native-vs-web screens, verified identifier placements,
phantom-failure signatures, build gotchas. It is NOT code knowledge (CodeGraph
regenerates that). Creed: *code reading lies; only the live hierarchy is truth* —
`agent-device snapshot` while exploring, Appium `page_source` once Appium is in
play (step 6 onward).

## Where & format

- Lives in `.agentqa/memory/` at the host repo root, **committed** (team-shared).
- **No secrets** — credential env-var *names* only, never values.
- Every note is a basic-memory-native markdown file: frontmatter + **observations**
  (`- [category] fact #tag`) and **relations** (`- relation-type [[Other Note]]`).
  The basic-memory MCP (wired in `assets/mcp.template.json`) indexes this graph for
  semantic recall; Markdown stays canonical and the index is a derived, rebuildable
  query layer — verify-on-read still applies.
- `index.md` (generated) is the **compact entry point** Recall loads by default:
  a terse tree of flows → screens (+ verified identifiers) → failures → data.
  Rebuild it with `python3 scripts/memory-index.py .agentqa/memory` — never hand-edit.
  Detail notes are loaded only when a flow is actively touched.

## Note types

| Folder / file | One note per | Captures |
|---|---|---|
| `flows/` | user flow | nav path, **the assertion that matters**, edge cases, native-vs-web per step |
| `screens/` | screen | native-or-web, identifier map (name → placement + verification status/date), quirks |
| `failures/` | phantom/flaky signature | symptom → cause → remedy (cross-flow library) |
| `env.md` | (single file) | build-policy rationale, credential env-var names, simulator/CodeGraph gotchas |

## Schema

- Frontmatter: `title`, `type` (`flow|screen|failure|env`), `tags`,
  `summary` (one line — the index is assembled from this), optional `last_verified`.
- Observation categories: `[flow-step]` `[assertion]` `[native]` `[web]`
  `[identifier]` `[quirk]` `[edge-case]` `[symptom]` `[cause]` `[remedy]`
  `[gotcha]` `[credential-env]`.
- Relation types: `used-by` `uses-identifier` `diagnosed-by` `covers`.
- Identifier observation (encodes status + date):
  `- [identifier] <logical_name> → <file/symbol>; <status> <YYYY-MM-DD> #<flow>`
  status ∈ {`added-unverified`, `verified-in-hierarchy`, `stale`}.

## Lifecycle — four verbs

- **Recall** (read-on-start): load the relevant notes before acting.
- **Verify-on-read**: recalled facts are *claims*, re-checked against the live
  hierarchy; stale claims are flagged, never blindly trusted.
- **Capture** (write-on-finish): append **deduped** observations via
  `scripts/memory-write.py` (`propose` shows the top-3 similar, then
  `apply --op ADD|UPDATE|DELETE|NOOP`) — dedup is enforced, not eyeballed. `UPDATE`
  is the **Refresh** verb below; it and `DELETE` want the store under git so a
  wrong call is one `git checkout HEAD -- .agentqa/memory` away. That undoes the
  whole session's writes in one command, so refreshing eleven observations is as
  recoverable as refreshing one — they refuse only on unresolved merge conflicts,
  which a revert would silently discard.
- **Refresh**: a mismatch **updates** the observation and bumps its date rather
  than appending a contradiction.

**Memory trust = verify-delta:** on a repeat run, use the note as a map, confirm
known waypoints against live state, deep-dive only where reality diverges.

## Working layer — two ephemeral files

The `agentqa-write-test` skill maintains exactly two ephemeral files, both for the
current session only (deliberately not a `sessions/<run-id>/` tree). Both are
gitignored, never committed, excluded from `index.md`, and **deleted at step 9** —
or whenever the session ends unfinished. They are session state, not knowledge:
what deserves to persist is captured into `flows/`, `screens/`, and `failures/`.

| File | Written | Holds |
|---|---|---|
| `.agentqa/memory/.session-requirement.md` | step 2 (clarify) | what the user asked for: request, **success**, **failure**, **blockers**, environment/preconditions — the contract steps 3–8 check themselves against |
| `.agentqa/memory/.run-checkpoint.md` | step 5 (build pause) | in-flight run state so step 6 resumes after a context break instead of re-clarifying and re-exploring |

- Requirement note frontmatter: `title`, `type: session-requirement`, `updated`.
  Sections: `## Request`, `## Success`, `## Failure`, `## Blockers`,
  `## Environment / preconditions` (template in
  [clarify.md](clarify.md)).
- Checkpoint frontmatter: `run_id`, `current_step`, `feature`, `updated`. Sections:
  `## Added identifiers (awaiting build+verify)`, `## Hypothesis under test`,
  `## Blocker` (e.g. `WAITING_FOR_HUMAN_BUILD`).

## Source-of-truth split (no duplication)

- `.agentqa/config.yml` — structured facts. `.agentqa/memory/` — narrative.
  `CLAUDE.md`/`AGENTS.md` — a pointer to `.agentqa/memory/`.
