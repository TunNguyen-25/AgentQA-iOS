#!/bin/bash
# Install CodeGraph (codebase index + memory graph) CLI so agents can query call
# chains / blast radius. MCP registration is handled by register-mcp.sh.
# Usage: ./install-codegraph.sh [--check]
set -uo pipefail
cd "$(dirname "$0")"
source ./common.sh
parse_check_flag "$@"

require_cmd npm "Install Node.js first: brew install node" || exit 1

# --- CLI ---
if command -v codegraph >/dev/null 2>&1; then
  ok "codegraph $(codegraph --version 2>/dev/null)"
else
  if [ "$CHECK_ONLY" = 1 ]; then err "codegraph not installed"; exit 1; fi
  echo "Installing ${CODEGRAPH_PKG}..."
  npm install -g "${CODEGRAPH_PKG}" || { err "npm install codegraph failed"; exit 1; }
  ok "codegraph $(codegraph --version) installed"
fi

# MCP registration is handled centrally by register-mcp.sh (see .agentqa/mcp.json).

# --- Per-repo index (only when run from inside a repo without one) ---
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -n "$REPO_ROOT" ]; then
  if ls "$REPO_ROOT/.codegraph/"*.db >/dev/null 2>&1 || ls "$REPO_ROOT/.codegraph/"*.sqlite* >/dev/null 2>&1; then
    ok "repo already indexed (.codegraph present)"
  else
    warn "repo not indexed yet. Run 'codegraph init' in $REPO_ROOT (takes minutes on large repos; do NOT run while simulator tests are running)."
  fi
fi
