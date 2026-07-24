#!/bin/bash
# Shared helpers for the agentqa setup scripts.
# Source this file; do not execute it directly.

# Known-good versions (validated together on 2026-07-11, macOS + iOS 26.4 sim).
# Appium 2.x requires the xcuitest 7.x driver line; the latest driver needs Appium 3.
APPIUM_PIN="2.19.0"
XCUITEST_DRIVER_PIN="7.35.1"     # iOS driver — pairs with Appium 2.x
# Android driver. Same story as xcuitest: the uiautomator2 5.x+ line requires
# Appium 3, so on this Appium-2.x stack pin the last 4.x (peer ^2.4.1 || ^3.0.0-beta.0).
UIAUTOMATOR2_DRIVER_PIN="4.2.9"
AGENT_DEVICE_PIN="0.19.1"         # cross-platform: drives iOS sims AND Android emulators/devices
CODEGRAPH_PKG="@colbymchenry/codegraph"

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

# Parse --platform <ios|android|both> into AGENTQA_PLATFORM (flag value wins).
parse_platform_flag() {
  local prev=""
  for arg in "$@"; do
    if [ "$prev" = "--platform" ]; then export AGENTQA_PLATFORM="$arg"; prev=""; continue; fi
    [ "$arg" = "--platform" ] && prev="--platform"
  done
}

# Decide which platform(s) this machine should be set up for, printing one of
# `ios`, `android`, or `both`. Order of precedence:
#   1. AGENTQA_PLATFORM (from --platform or the env) — explicit wins.
#   2. Auto: iOS whenever macOS + xcrun is present; add Android when an SDK is
#      detected (adb on PATH or ANDROID_HOME/ANDROID_SDK_ROOT set). This keeps a
#      pure-iOS machine iOS-only and lights up Android the moment its SDK exists,
#      without forcing anyone to pass a flag.
resolve_platform_scope() {
  local want="${AGENTQA_PLATFORM:-auto}"
  case "$want" in
    ios|android|both) echo "$want"; return 0 ;;
  esac
  local has_ios=0 has_android=0
  { [ "$(uname -s)" = "Darwin" ] && command -v xcrun >/dev/null 2>&1; } && has_ios=1
  { command -v adb >/dev/null 2>&1 || [ -n "${ANDROID_HOME:-}${ANDROID_SDK_ROOT:-}" ]; } && has_android=1
  if [ "$has_ios" = 1 ] && [ "$has_android" = 1 ]; then echo both
  elif [ "$has_android" = 1 ]; then echo android
  else echo ios; fi   # default when nothing is detected: the original iOS behavior
}

# platform_targets_ios <scope> / platform_targets_android <scope> — 0 if in scope.
platform_targets_ios()     { case "$1" in ios|both) return 0;; *) return 1;; esac; }
platform_targets_android() { case "$1" in android|both) return 0;; *) return 1;; esac; }
# shellcheck source=harness.sh
source "$(dirname "${BASH_SOURCE[0]}")/harness.sh"
