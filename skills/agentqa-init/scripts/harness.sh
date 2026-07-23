#!/bin/bash
# Per-harness capability table + selection. Source this; do not execute.
# bash 3.2 compatible (no associative arrays). VERIFY seed data against upstream:
#   Each harness's own MCP config path.

# Supported harness ids.
harness_known() {
  case "${1:-}" in
    claude|cursor|codex|copilot|opencode|pi|antigravity|droid|kimi|goose) return 0;;
    *) return 1;;
  esac
}

# How MCP servers get registered for <id>.
harness_mcp_method() {
  case "${1:-}" in
    claude)      echo "claude-cli";;
    cursor)      echo "file:.cursor/mcp.json";;
    codex)       echo "file:~/.codex/config.toml";;   # VERIFY path/format
    opencode)    echo "file:opencode.json";;           # VERIFY
    goose)       echo "file:~/.config/goose/config.yaml";;
    copilot|pi|antigravity|kimi) echo "print";;
    *)           echo "print";;
  esac
}

# Skills-dir subpath (relative to repo root for --project, or $HOME for --global)
# where the agentqa/ folder is placed. Empty => not a known raw-skill harness
# (installer prints a manual/marketplace note). VERIFY non-claude paths upstream.
#
# codex reads the Agent Skills open standard from `.agents/skills` (repo) and
# `~/.agents/skills` (user) — the same subpath serves both scopes here, matching
# claude's `.claude/skills`. Other agentskills.io-compatible harnesses may read
# the same `.agents/skills` path; wire them here as their paths are confirmed.
harness_skills_dir() {
  case "${1:-}" in
    claude) echo ".claude/skills";;
    codex)  echo ".agents/skills";;
    *)      echo "";;
  esac
}

# Best-effort auto-detect; prefer Claude Code.
detect_harness() {
  if command -v claude >/dev/null 2>&1; then echo claude; return; fi
  command -v codex   >/dev/null 2>&1 && { echo codex; return; }
  command -v agy     >/dev/null 2>&1 && { echo antigravity; return; }
  command -v droid   >/dev/null 2>&1 && { echo droid; return; }
  command -v copilot >/dev/null 2>&1 && { echo copilot; return; }
  command -v pi      >/dev/null 2>&1 && { echo pi; return; }
  echo unknown
}

# Resolve to $HARNESS: explicit AGENTQA_HARNESS wins, else auto-detect.
resolve_harness() {
  if [ -n "${AGENTQA_HARNESS:-}" ]; then
    if harness_known "$AGENTQA_HARNESS" || [ "$AGENTQA_HARNESS" = unknown ]; then HARNESS="$AGENTQA_HARNESS"; return 0; fi
    err "unknown AGENTQA_HARNESS='$AGENTQA_HARNESS' (supported: claude cursor codex copilot opencode pi antigravity droid kimi goose)"
    return 1
  fi
  HARNESS="$(detect_harness)"
}
