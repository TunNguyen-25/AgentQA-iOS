#!/bin/bash
# Shared helpers for the agentqa setup scripts.
# Source this file; do not execute it directly.

# Known-good versions (validated together on 2026-07-11, macOS + iOS 26.4 sim).
# Appium 2.x requires the xcuitest 7.x driver line; the latest driver needs Appium 3.
APPIUM_PIN="2.19.0"
XCUITEST_DRIVER_PIN="7.35.1"
AGENT_DEVICE_PIN="0.19.1"
CODEGRAPH_PKG="@colbymchenry/codegraph"

# Phase 2 MCP server pins (confirm exact versions at install time; record here).
BASIC_MEMORY_PIN="0.22.1" # pypi basic-memory; latest, pinned 2026-07-12
APPIUM_MCP_PIN="1.87.4" # npm appium-mcp; validated 2026-07-12

ok()   { printf '\033[32m✔ %s\033[0m\n' "$*"; }
warn() { printf '\033[33m⚠ %s\033[0m\n' "$*"; }
err()  { printf '\033[31m✖ %s\033[0m\n' "$*" >&2; }

# require_cmd <cmd> <hint> — fail fast with an install hint
require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    err "$1 not found. $2"
    return 1
  fi
}

# CHECK_ONLY=1 means validate without installing (set by --check)
parse_check_flag() {
  CHECK_ONLY=0
  for arg in "$@"; do
    [ "$arg" = "--check" ] && CHECK_ONLY=1
  done
}

# Parse --harness <id> into AGENTQA_HARNESS (the flag value wins over any prior env).
parse_harness_flag() {
  local prev=""
  for arg in "$@"; do
    if [ "$prev" = "--harness" ]; then export AGENTQA_HARNESS="$arg"; prev=""; continue; fi
    [ "$arg" = "--harness" ] && prev="--harness"
  done
}
# shellcheck source=harness.sh
source "$(dirname "${BASH_SOURCE[0]}")/harness.sh"
