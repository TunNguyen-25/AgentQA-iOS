#!/bin/bash
# Install basic-memory (markdown knowledge-graph MCP server) as a global tool.
# The agentqa memory MCP indexes .agentqa/memory/ (Phase 1). Usage: [--check]
set -uo pipefail
cd "$(dirname "$0")"
source ./common.sh
parse_check_flag "$@"

if command -v basic-memory >/dev/null 2>&1; then
  ok "basic-memory $(basic-memory --version 2>/dev/null)"
  exit 0
fi

if [ "$CHECK_ONLY" = 1 ]; then err "basic-memory not installed"; exit 1; fi

# Prefer uv, fall back to pipx.
if command -v uv >/dev/null 2>&1; then
  echo "Installing basic-memory via uv..."
  uv tool install basic-memory${BASIC_MEMORY_PIN:+==$BASIC_MEMORY_PIN} \
    || { err "uv tool install basic-memory failed"; exit 1; }
elif command -v pipx >/dev/null 2>&1; then
  echo "Installing basic-memory via pipx..."
  pipx install basic-memory${BASIC_MEMORY_PIN:+==$BASIC_MEMORY_PIN} \
    || { err "pipx install basic-memory failed"; exit 1; }
else
  err "need uv or pipx to install basic-memory — 'brew install uv' (or pipx), then re-run"
  exit 1
fi
command -v basic-memory >/dev/null 2>&1 \
  && ok "basic-memory $(basic-memory --version 2>/dev/null) installed" \
  || { err "basic-memory not on PATH after install (check your tool bin dir)"; exit 1; }
