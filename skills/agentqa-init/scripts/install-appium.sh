#!/bin/bash
# Install Appium server + the platform driver(s) (pinned known-good versions).
# Usage: ./install-appium.sh [--check] [--platform <ios|android|both>]
#   --check              validate only, install nothing
#   --platform <scope>   which driver(s) to install (default: auto-detect —
#                        iOS on macOS, Android when its SDK is present)
set -uo pipefail
cd "$(dirname "$0")"
source ./common.sh
parse_check_flag "$@"
parse_platform_flag "$@"
SCOPE="$(resolve_platform_scope)"

require_cmd node "Install Node.js first: brew install node" || exit 1
require_cmd npm  "Install Node.js first: brew install node" || exit 1

# --- Appium server (shared by both drivers) ---
if command -v appium >/dev/null 2>&1; then
  APPIUM_VERSION="$(appium --version 2>/dev/null)"
  case "$APPIUM_VERSION" in
    2.*) ok "appium $APPIUM_VERSION (2.x — compatible)" ;;
    *)   warn "appium $APPIUM_VERSION found — this stack is validated on 2.x with xcuitest ${XCUITEST_DRIVER_PIN} / uiautomator2 ${UIAUTOMATOR2_DRIVER_PIN}. If drivers misbehave, install appium@${APPIUM_PIN}." ;;
  esac
else
  if [ "$CHECK_ONLY" = 1 ]; then err "appium not installed"; exit 1; fi
  echo "Installing appium@${APPIUM_PIN}..."
  npm install -g "appium@${APPIUM_PIN}" || { err "npm install appium failed"; exit 1; }
  ok "appium $(appium --version) installed"
fi

# install_driver <driver-name> <pin> — idempotent install/validate of one driver.
# (appium logs its list to stderr, hence 2>&1.)
install_driver() {
  local name="$1" pin="$2"
  if appium driver list --installed 2>&1 | grep -q "$name"; then
    ok "$name driver installed"
  else
    if [ "$CHECK_ONLY" = 1 ]; then err "$name driver not installed"; return 1; fi
    echo "Installing $name driver ${pin}..."
    appium driver install "${name}@${pin}" || { err "$name driver install failed"; return 1; }
    ok "$name driver installed"
  fi
}

echo "Driver scope: $SCOPE"
rc=0

# --- iOS: xcuitest ---
if platform_targets_ios "$SCOPE"; then
  install_driver xcuitest "$XCUITEST_DRIVER_PIN" || rc=1
else
  warn "xcuitest driver skipped (platform scope: $SCOPE)"
fi

# --- Android: uiautomator2 ---
if platform_targets_android "$SCOPE"; then
  install_driver uiautomator2 "$UIAUTOMATOR2_DRIVER_PIN" || rc=1
else
  warn "uiautomator2 driver skipped (platform scope: $SCOPE — set --platform android/both or install the Android SDK to include it)"
fi

exit $rc
