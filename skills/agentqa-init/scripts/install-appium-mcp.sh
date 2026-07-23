#!/bin/bash
# Install the official Appium MCP server (appium/appium-mcp). It exposes
# appium_get_page_source / appium_find_element and connects to a RUNNING Appium
# server at session time (remoteServerUrl). Usage: [--check]
set -uo pipefail
cd "$(dirname "$0")"
source ./common.sh
parse_check_flag "$@"

require_cmd npm "Install Node.js first: brew install node" || exit 1

if npm ls -g appium-mcp >/dev/null 2>&1; then
  ok "appium-mcp installed ($(npm ls -g appium-mcp 2>/dev/null | grep appium-mcp | head -1 | tr -d ' '))"
  exit 0
fi

if [ "$CHECK_ONLY" = 1 ]; then err "appium-mcp not installed"; exit 1; fi
echo "Installing appium-mcp..."
npm install -g "appium-mcp@${APPIUM_MCP_PIN}" \
  && ok "appium-mcp installed" \
  || { err "npm install -g appium-mcp failed"; exit 1; }
