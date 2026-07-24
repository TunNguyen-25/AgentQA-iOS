# agentqa memory model — behavioral knowledge store

Shared reference for every subcommand that reads or writes `.agentqa/memory/`.
Read this before touching memory; don't re-derive the schema.

Memory persists **behavioral** knowledge the skill hand-earns at runtime — real
navigation paths, native-vs-web screens, verified identifier placements,
phantom-failure signatures, build gotchas. It is NOT code knowledge (CodeGraph
regenerates that). Creed: *code reading lies; only the live hierarchy is truth* —
`agent-device snapshot` while exploring, Appium `page_source` once Appium is in
play (step 6 onward).

The schema below is **platform-neutral** — it holds for iOS and Android alike. An
`[identifier]` records a logical name and where it's set; the *mechanism* behind
it (iOS `accessibilityIdentifier`, Android `contentDescription`/`resource-id`) is
the write step's concern, not the note's. When you record a screen's identifiers
or quirks, they read the same way whichever platform produced them.

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
| `env.md` | (single file) | build-policy rationale, credential env-var names, device/simulator + CodeGraph gotchas |

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

## Intent layer — product artifacts (optional, read-only)

Some teams already have SRDs, PM scenarios, user-flow docs, acceptance criteria.
When `docs:` is set in `.agentqa/config.yml` (local paths/globs), those files are
readable at step 0 and feed the clarify round. Many repos have none — the block is
absent by default and everything below simply doesn't apply.

**They are intent, not truth.** A spec says what the app was *meant* to do. It can
be stale, aspirational, or describe something that shipped differently — which puts
it *further* from reality than the source code, and the creed already says code
reading lies. So artifacts get the weakest trust of any source here: they are good
at the one thing neither code nor the live app can supply (what *should* count as
passing), and unreliable at everything the live hierarchy answers directly.

What they're for:
- **Pre-filling the clarify round.** Success / failure / blockers / entry point are
  the questions asked every run because only a human could answer them. A spec is a
  written answer — so propose it back for confirmation instead of asking cold. The
  user still decides; a doc never silently becomes the requirement.
- **Aiming exploration.** A described flow is another map for the step-3
  verify-delta pass — one more prior to confirm against live state, exactly like a
  recalled memory note.

**Provenance rule — spec claims stay session-scoped until observed live.**
Anything read from an artifact and not yet seen in the live hierarchy lives only in
`.agentqa/memory/.session-requirement.md`, which is deleted when the session ends.
It is never written into `flows/`, `screens/`, or `failures/`. Those hold what the
skill *observed*; letting an unverified doc claim in would poison the store that
later runs trust as a map, and it would be indistinguishable from a fact earned by
driving the app. Once exploration confirms a claim, it gets captured the normal way
— as an observation grounded in what you saw, not a quotation from the doc.

When a doc and the live app disagree, the live app wins and **the divergence is
worth surfacing** — a spec that no longer matches the build is useful information
for the user, not just noise to discard.

The skill **never writes to these files.** They are owned by whoever wrote them.

## Source-of-truth split (no duplication)

- `.agentqa/config.yml` — structured facts. `.agentqa/memory/` — narrative
  behavioral knowledge the skill earned and owns. `CLAUDE.md`/`AGENTS.md` — a
  pointer to `.agentqa/memory/`. `docs:` artifacts — external **intent**,
  read-only, owned by PM/BO/dev; read for requirements, never written, never
  authoritative over the live hierarchy.
- Trust order when they disagree: **live hierarchy > memory > code > docs.**
