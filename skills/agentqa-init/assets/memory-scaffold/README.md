# .agentqa/memory

Behavioral knowledge the agentqa skill has learned about this app, as
basic-memory-native markdown notes. Committed and team-shared. **No secrets.**

- `flows/` — one note per user flow: nav path, the assertion that matters, edge cases.
- `screens/` — one note per screen: native/web, identifier map (+ verification date), quirks.
- `failures/` — phantom/flaky signatures: symptom → cause → remedy.
- `env.md` — build-policy rationale, credential env-var names, simulator gotchas.
- `index.md` — generated compact entry point (flows → screens → failures → data);
  Recall loads this first. Rebuild with `scripts/memory-index.py` (agentqa-write-test skill); never hand-edit.

Notes use observations (`- [category] fact #tag`) and relations
(`- rel [[Other Note]]`). Schema: `references/memory-model.md` in the agentqa-write-test skill. The
basic-memory MCP indexes this folder for semantic search (Markdown stays the source
of truth); without it, read these files directly.
