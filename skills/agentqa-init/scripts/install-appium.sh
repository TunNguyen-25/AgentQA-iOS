#!/bin/bash
# Install Appium server + xcuitest driver (pinned known-good versions).
# Usage: ./install-appium.sh [--check]   (--check = validate only, install nothing)
set -uo pipefail
cd "$(dirname "$0")"
source ./common.sh
parse_check_flag "$@"

require_cmd node "Install Node.js first: brew install node" || exit 1
require_cmd npm  "Install Node.js first: brew install node" || exit 1

# --- Appium server ---
if command -v appium >/dev/null 2>&1; then
  APPIUM_VERSION="$(appium --version 2>/dev/null)"
  case "$APPIUM_VERSION" in
    2.*) ok "appium $APPIUM_VERSION (2.x — compatible)" ;;
    *)   warn "appium $APPIUM_VERSION found — this stack is validated on 2.x with xcuitest ${XCUITEST_DRIVER_PIN}. If drivers misbehave, install appium@${APPIUM_PIN}." ;;
  esac
else
  if [ "$CHECK_ONLY" = 1 ]; then err "appium not installed"; exit 1; fi
  echo "Installing appium@${APPIUM_PIN}..."
  npm install -g "appium@${APPIUM_PIN}" || { err "npm install appium failed"; exit 1; }
  ok "appium $(appium --version) installed"
fi

# --- xcuitest driver --- (appium logs the list to stderr, hence 2>&1)
if appium driver list --installed 2>&1 | grep -q xcuitest; then
  ok "xcuitest driver installed"
else
  if [ "$CHECK_ONLY" = 1 ]; then err "xcuitest driver not installed"; exit 1; fi
  echo "Installing xcuitest driver ${XCUITEST_DRIVER_PIN}..."
  appium driver install "xcuitest@${XCUITEST_DRIVER_PIN}" || { err "driver install failed"; exit 1; }
  ok "xcuitest driver installed"
fi
