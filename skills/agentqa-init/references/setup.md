# /agentqa-init setup — install & validate the toolchain (any harness)

Run the master script from this skill's `scripts/` directory:

```bash
scripts/setup-all.sh                       # install what's missing, validate everything
scripts/setup-all.sh --check               # validate only (CI-friendly), non-zero on gaps
scripts/setup-all.sh --harness cursor      # target a specific harness (or set AGENTQA_HARNESS)
scripts/setup-all.sh --platform android    # ios | android | both (default: auto-detect)
```

**Harness selection:** auto-detected (prefers Claude Code if the `claude` CLI is
present); override with `--harness <id>` or `AGENTQA_HARNESS=<id>`. Supported:
`claude cursor codex copilot opencode pi antigravity droid kimi goose`. Setup is
non-interactive, so `--check` stays CI-friendly.

**Platform selection:** `--platform ios|android|both` (or `AGENTQA_PLATFORM`)
decides which driver + device toolchain to install/validate. The default is
**auto**: iOS whenever macOS + `xcrun` is present, Android added the moment its
SDK is detected (`adb` on PATH or `ANDROID_HOME`/`ANDROID_SDK_ROOT` set). So an
iOS-only Mac stays iOS-only with no flag, and an Android app repo just needs the
SDK installed. iOS preflight is skipped-with-note when the scope is android-only.

It runs these and prints a pass/fail summary (a printed manual step is a
PASS-with-note, not a failure):

| Step | What |
|---|---|
| Preflight | Xcode CLT + simulator runtimes (iOS scope), Node.js — install hints only |
| Android SDK *(android scope)* | `install-android-sdk.sh` — validate `adb`, `emulator`, a JDK, `ANDROID_HOME`; hints only (never auto-installs the multi-GB SDK) |
| `install-appium-mcp.sh` | Official Appium MCP (`appium-mcp`) — page_source/verify reads |
| `install-appium.sh` | Appium server 2.x + the pinned driver(s): `xcuitest` (iOS) and/or `uiautomator2` (Android) |
| `install-agent-device.sh` | agent-device CLI (drives both iOS sims and Android emulators/devices) |
| `install-codegraph.sh` | CodeGraph CLI (its MCP is registered by the manifest step) |
| `register-mcp.sh` | Write `.agentqa/mcp.json`; register with Claude or print per-harness placement |
| `setup-python-env.sh` | Project venv + requirements |

**Android note:** the SDK itself is a human install (Android Studio, or
`brew install --cask android-commandlinetools`). `install-android-sdk.sh` only
checks it and prints the exact `sdkmanager`/`avdmanager` commands for whatever is
missing — the same way the Xcode/Node preflight does for iOS.

## MCP servers & the portable manifest

Two MCP servers — `codegraph` and `appium` — are defined once in
`.agentqa/mcp.json` at the host repo root (committed, fully portable). On **Claude
Code**, `register-mcp.sh` registers them automatically (`claude mcp add`). On **any
other harness**, it prints the manifest plus where that harness reads MCP config
(e.g. Cursor → `.cursor/mcp.json`), for you to import. The Appium MCP connects to a
*running* Appium server at session time (`remoteServerUrl`, e.g.
`http://127.0.0.1:4723`), so start Appium before using it.

Behavioral memory needs no server: `.agentqa/memory/` is plain Markdown that
`agentqa-write-test`'s own scripts read, scope, and validate. Both MCP servers here
are repo-agnostic, so Claude Code's user-scope registration is fine however many
app repos share a machine.

Notes:
- Each script is idempotent and runnable alone with `--check`.
- The Python step needs the project initialized first (`/agentqa-init init`); from
  outside the app repo, set `AGENTQA_PROJECT_ROOT`.
- Never run CPU-heavy jobs (e.g. `codegraph init`) concurrently with device
  tests — on iOS the WebDriverAgent waits time out, and on Android a busy host
  slows the UiAutomator2 server the same way; both surface as phantom failures.
