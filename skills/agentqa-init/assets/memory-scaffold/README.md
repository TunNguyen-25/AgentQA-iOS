# .agentqa/memory

Behavioral knowledge the agentqa skill has learned about this app, as plain
Markdown notes. Committed and team-shared. **No secrets** — credential env-var
*names* only.

- `flows/` — one note per user flow.
- `screens/` — one note per screen.
- `failures/` — phantom/flaky signatures.
- `env.md` — build-policy rationale, credential env-var names, device gotchas.
- `index.md` — **generated and gitignored.** Rebuilt from the notes; never
  hand-edit it, and never commit it.

Notes are frontmatter plus one fact per line: `- [category] fact #flow`. The
`#flow` tag is what ties a screen or a failure to the flows it belongs to, and
it's what scoped recall filters on.

**The schema lives in exactly one place** — `references/memory-model.md` in the
`agentqa-write-test` skill. Categories, frontmatter keys, the identifier format
and the lifecycle are defined there rather than restated here, so there is never a
second copy to drift out of date.

The scripts that read and write this store (all in that skill's `scripts/`):

```bash
python3 memory-index.py .agentqa/memory                # rebuild index.md
python3 memory-index.py .agentqa/memory --flow login   # one flow's slice
python3 memory-index.py .agentqa/memory --stale        # what needs re-verifying
python3 memory-lint.py  .agentqa/memory                # validate the store
python3 memory-write.py propose ...                    # deduped capture
```
