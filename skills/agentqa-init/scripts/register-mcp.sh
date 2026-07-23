#!/bin/bash
# Emit .agentqa/mcp.json in the host repo and wire the three MCP servers to the
# selected harness. Claude Code -> auto-register; others -> print manifest + the
# harness's placement step. Registers a per-repo basic-memory project. Usage: [--check]
set -uo pipefail
INVOKE_DIR="$PWD"
cd "$(dirname "$0")"
source ./common.sh
parse_check_flag "$@"
parse_harness_flag "$@"
resolve_harness || exit 1

ROOT="${AGENTQA_PROJECT_ROOT:-$(git -C "$INVOKE_DIR" rev-parse --show-toplevel 2>/dev/null || echo "$INVOKE_DIR")}"
MEM="$ROOT/.agentqa/memory"
MANIFEST="$ROOT/.agentqa/mcp.json"
BM_PROJECT="${AGENTQA_BM_PROJECT:-agentqa-$(basename "$ROOT")}"

# --- check mode: manifest must exist; for claude, servers must be registered ---
if [ "$CHECK_ONLY" = 1 ]; then
  [ -f "$MANIFEST" ] || { err "manifest missing: $MANIFEST"; exit 1; }
  if [ "$HARNESS" = claude ] && command -v claude >/dev/null 2>&1; then
    rc=0
    for s in codegraph basic-memory appium; do
      claude mcp get "$s" >/dev/null 2>&1 || { err "MCP not registered: $s"; rc=1; }
    done
    [ $rc -eq 0 ] && ok "MCP manifest + servers registered (claude)"; exit $rc
  fi
  ok "MCP manifest present ($MANIFEST); non-Claude registration is manual"; exit 0
fi

# --- write the manifest from the template ---
mkdir -p "$ROOT/.agentqa"
sed -e "s/__BM_PROJECT__/$BM_PROJECT/g" \
    -e "s/__APPIUM_MCP_VERSION__/${APPIUM_MCP_PIN}/g" \
    "../assets/mcp.template.json" > "$MANIFEST"
ok "wrote $MANIFEST (harness: $HARNESS)"

# --- register the basic-memory project (idempotent) ---
if command -v basic-memory >/dev/null 2>&1; then
  if basic-memory project list 2>/dev/null | grep -qE "(^|[[:space:]])$(printf '%s' "$BM_PROJECT" | sed 's/[][^$.*/\\]/\\&/g')([[:space:]]|\$)"; then
    ok "basic-memory project '$BM_PROJECT' exists"
  else
    basic-memory project add "$BM_PROJECT" "$MEM" \
      && ok "basic-memory project '$BM_PROJECT' -> $MEM" \
      || warn "could not add basic-memory project (add later: basic-memory project add $BM_PROJECT $MEM)"
  fi
else
  warn "basic-memory not installed yet — run install-basic-memory.sh, then re-run register-mcp.sh"
fi

# --- deliver to the harness ---
method="$(harness_mcp_method "$HARNESS")"
case "$method" in
  claude-cli)
    if ! command -v claude >/dev/null 2>&1; then
      warn "claude CLI not found — import $MANIFEST manually"; exit 0
    fi
    claude mcp get codegraph    >/dev/null 2>&1 || claude mcp add codegraph    -s user -- codegraph serve --mcp
    claude mcp get basic-memory >/dev/null 2>&1 || claude mcp add basic-memory -s user -- basic-memory --project="$BM_PROJECT" mcp
    claude mcp get appium       >/dev/null 2>&1 || claude mcp add appium       -s user -- npx "appium-mcp@${APPIUM_MCP_PIN}"
    ok "registered codegraph + basic-memory + appium with Claude Code (user scope)"
    ;;
  file:*)
    dest="${method#file:}"
    warn "Point $HARNESS at the MCP servers by importing this manifest into: $dest"
    echo "---- $MANIFEST ----"; cat "$MANIFEST"; echo "----"
    ;;
  print|*)
    warn "Register these MCP servers with $HARNESS per its docs (manifest below):"
    echo "---- $MANIFEST ----"; cat "$MANIFEST"; echo "----"
    ;;
esac
