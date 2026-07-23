# /agentqa-init setup — install & validate the toolchain (any harness)

Run the master script from this skill's `scripts/` directory:

```bash
scripts/setup-all.sh                       # install what's missing, validate everything
scripts/setup-all.sh --check               # validate only (CI-friendly), non-zero on gaps
scripts/setup-all.sh --harness cursor      # target a specific harness (or set AGENTQA_HARNESS)
```

**Harness selection:** auto-detected (prefers Claude Code if the `claude` CLI is
present); override with `--harness <id>` or `AGENTQA_HARNESS=<id>`. Supported:
`claude cursor codex copilot opencode pi antigravity droid kimi goose`. Setup is
non-interactive, so `--check` stays CI-friendly.

It runs these and prints a pass/fail summary (a printed manual step is a
PASS-with-note, not a failure):

| Step | What |
|---|---|
| Preflight | Xcode CLT, simulator runtimes, Node.js (install hints only) |
| `install-appium-mcp.sh` | Official Appium MCP (`appium-mcp`) — page_source/verify reads |
| `install-appium.sh` | Appium server 2.x + pinned `xcuitest` driver |
| `install-agent-device.sh` | agent-device CLI |
| `install-codegraph.sh` | CodeGraph CLI (its MCP is registered by the manifest step) |
| `install-basic-memory.sh` | basic-memory MCP (indexes `.agentqa/memory/`) |
| `register-mcp.sh` | Write `.agentqa/mcp.json`; register a basic-memory project; register with Claude or print per-harness placement |
| `setup-python-env.sh` | Project venv + requirements |

## MCP servers & the portable manifest

Three MCP servers — `codegraph`, `basic-memory`, `appium` — are defined once in
`.agentqa/mcp.json` at the host repo root (committed, fully portable). On **Claude
Code**, `register-mcp.sh` registers them automatically (`claude mcp add`). On **any
other harness**, it prints the manifest plus where that harness reads MCP config
(e.g. Cursor → `.cursor/mcp.json`), for you to import. The Appium MCP connects to a
*running* Appium server at session time (`remoteServerUrl`, e.g.
`http://127.0.0.1:4723`), so start Appium before using it.

Notes:
- Each script is idempotent and runnable alone with `--check`.
- On Claude Code the MCP servers register at **user scope**, so `basic-memory`'s
  default project assumes **one app repo per machine**. For several repos on one
  machine, register `basic-memory` per-repo (project scope) — a planned
  enhancement; `codegraph`/`appium` are repo-agnostic and unaffected.
- The Python step needs the project initialized first (`/agentqa-init init`); from
  outside the app repo, set `AGENTQA_PROJECT_ROOT`.
- Never run CPU-heavy jobs (e.g. `codegraph init`) concurrently with simulator
  tests — WebDriverAgent waits time out and produce phantom failures.
