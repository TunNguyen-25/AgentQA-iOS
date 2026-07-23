#!/bin/bash
# Install agent-device (CLI that lets an AI agent explore/drive the simulator).
# Usage: ./install-agent-device.sh [--check]
set -uo pipefail
cd "$(dirname "$0")"
source ./common.sh
parse_check_flag "$@"

require_cmd npm "Install Node.js first: brew install node" || exit 1

if command -v agent-device >/dev/null 2>&1; then
  ok "agent-device $(agent-device --version 2>/dev/null || echo '(installed)')"
else
  if [ "$CHECK_ONLY" = 1 ]; then err "agent-device not installed"; exit 1; fi
  echo "Installing agent-device@${AGENT_DEVICE_PIN}..."
  npm install -g "agent-device@${AGENT_DEVICE_PIN}" || { err "npm install agent-device failed"; exit 1; }
  ok "agent-device installed"
fi
