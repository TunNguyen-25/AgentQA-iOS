#!/bin/bash
# Emit .agentqa/mcp.json in the host repo and wire the MCP servers to the
# selected harness. Claude Code -> auto-register; others -> print manifest + the
# harness's placement step. Usage: [--check]
set -uo pipefail
INVOKE_DIR="$PWD"
cd "$(dirname "$0")"
source ./common.sh
parse_check_flag "$@"
parse_harness_flag "$@"
resolve_harness || exit 1

ROOT="${AGENTQA_PROJECT_ROOT:-$(git -C "$INVOKE_DIR" rev-parse --show-toplevel 2>/dev/null || echo "$INVOKE_DIR")}"
MANIFEST="$ROOT/.agentqa/mcp.json"

# --- check mode: manifest must exist; for claude, servers must be registered ---
if [ "$CHECK_ONLY" = 1 ]; then
  [ -f "$MANIFEST" ] || { err "manifest missing: $MANIFEST"; exit 1; }
  if [ "$HARNESS" = claude ] && command -v claude >/dev/null 2>&1; then
    rc=0
    for s in codegraph appium; do
      claude mcp get "$s" >/dev/null 2>&1 || { err "MCP not registered: $s"; rc=1; }
    done
    [ $rc -eq 0 ] && ok "MCP manifest + servers registered (claude)"; exit $rc
  fi
  ok "MCP manifest present ($MANIFEST); non-Claude registration is manual"; exit 0
fi

# --- write the manifest from the template ---
mkdir -p "$ROOT/.agentqa"
sed -e "s/__APPIUM_MCP_VERSION__/${APPIUM_MCP_PIN}/g" \
    "../assets/mcp.template.json" > "$MANIFEST"
ok "wrote $MANIFEST (harness: $HARNESS)"

# --- deliver to the harness ---
method="$(harness_mcp_method "$HARNESS")"
case "$method" in
  claude-cli)
    if ! command -v claude >/dev/null 2>&1; then
      warn "claude CLI not found — import $MANIFEST manually"; exit 0
    fi
    claude mcp get codegraph >/dev/null 2>&1 || claude mcp add codegraph -s user -- codegraph serve --mcp
    claude mcp get appium    >/dev/null 2>&1 || claude mcp add appium    -s user -- npx "appium-mcp@${APPIUM_MCP_PIN}"
    ok "registered codegraph + appium with Claude Code (user scope)"
    ;;
  file:*)
    dest="${method#file:}"
    if [ "$HARNESS" = codex ]; then
      # Codex config is TOML, not JSON — emit ready-to-paste [mcp_servers.*] tables.
      warn "Add these MCP servers to $dest (Codex uses TOML [mcp_servers.*] tables):"
      echo "---- ~/.codex/config.toml ----"
      cat <<EOF
[mcp_servers.codegraph]
command = "codegraph"
args = ["serve", "--mcp"]

[mcp_servers.appium]
command = "npx"
args = ["appium-mcp@${APPIUM_MCP_PIN}"]
EOF
      echo "----"
    else
      warn "Point $HARNESS at the MCP servers by importing this manifest into: $dest"
      echo "---- $MANIFEST ----"; cat "$MANIFEST"; echo "----"
    fi
    ;;
  print|*)
    warn "Register these MCP servers with $HARNESS per its docs (manifest below):"
    echo "---- $MANIFEST ----"; cat "$MANIFEST"; echo "----"
    ;;
esac
