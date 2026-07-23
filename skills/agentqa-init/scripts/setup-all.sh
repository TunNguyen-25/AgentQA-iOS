#!/bin/bash
# Master setup: install + validate the whole agent-driven UI automation stack,
# one component at a time, then print a summary.
#
# Usage:
#   ./setup-all.sh           install anything missing, validate everything
#   ./setup-all.sh --check   validate only (CI-friendly), install nothing
#
# Run from anywhere; to target a specific app repo for the Python step, run
# from inside that repo or set AGENTQA_PROJECT_ROOT=/path/to/repo.
set -uo pipefail
cd "$(dirname "$0")"
source ./common.sh
parse_check_flag "$@"
MODE_FLAG=""; [ "$CHECK_ONLY" = 1 ] && MODE_FLAG="--check"
parse_harness_flag "$@"
resolve_harness || exit 1
echo "Target harness: $HARNESS"
HARNESS_FLAG="--harness $HARNESS"

declare -a NAMES RESULTS

run_step() { # run_step <name> <command...>
  local name="$1"; shift
  echo ""
  echo "── $name ─────────────────────────────"
  if "$@"; then
    NAMES+=("$name"); RESULTS+=("PASS")
  else
    NAMES+=("$name"); RESULTS+=("FAIL")
  fi
}

# --- Preflight: things this script can check but not install for you ---
preflight() {
  local rc=0
  if xcode-select -p >/dev/null 2>&1; then
    ok "Xcode command line tools ($(xcode-select -p))"
  else
    err "Xcode not configured — install Xcode from the App Store, then: xcode-select --install"
    rc=1
  fi
  if command -v xcrun >/dev/null 2>&1 && xcrun simctl list devices >/dev/null 2>&1; then
    ok "iOS simulators available"
  else
    err "simctl unavailable — open Xcode once and install an iOS simulator runtime"
    rc=1
  fi
  require_cmd node "brew install node" || rc=1
  return $rc
}

run_step "Preflight (Xcode, simulators, Node)" preflight
run_step "Appium MCP server"                   ./install-appium-mcp.sh $MODE_FLAG
run_step "Appium + xcuitest driver"            ./install-appium.sh $MODE_FLAG
run_step "agent-device"                        ./install-agent-device.sh $MODE_FLAG
run_step "CodeGraph CLI"                       ./install-codegraph.sh $MODE_FLAG
run_step "basic-memory"                        ./install-basic-memory.sh $MODE_FLAG
run_step "MCP registration"                    ./register-mcp.sh $MODE_FLAG $HARNESS_FLAG
run_step "Python test environment"             ./setup-python-env.sh $MODE_FLAG

echo ""
echo "══ Summary ═══════════════════════════"
FAILED=0
for i in "${!NAMES[@]}"; do
  if [ "${RESULTS[$i]}" = "PASS" ]; then
    ok "${NAMES[$i]}"
  else
    err "${NAMES[$i]}"
    FAILED=1
  fi
done

if [ "$FAILED" = 1 ]; then
  echo ""
  err "Setup incomplete — fix the failed components above and re-run. (Python step failing? Run '/agentqa-init init' in the app repo first.)"
  exit 1
fi
echo ""
ok "All components ready. Next: boot a simulator, install the app build, start 'appium', then run '/agentqa-write-test'."
[ "$HARNESS" != claude ] && echo "  (On $HARNESS: MCP servers aren't auto-registered — see the printed manifest steps above / .agentqa/mcp.json.)"
