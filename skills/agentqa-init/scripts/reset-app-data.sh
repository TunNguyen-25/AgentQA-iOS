#!/usr/bin/env bash
# Wipe an installed app's local data on the booted simulator, WITHOUT uninstalling
# it — a `build.policy: human` project keeps the build a person installed by hand.
#
# Usage: reset-app-data.sh [<bundle_id>]
#   bundle id resolution: argument > $AGENTQA_BUNDLE_ID > .agentqa/config.yml
#
# Wipes: the app's data container (Documents/, Library/ — incl. NSUserDefaults —,
#        tmp/, SystemData/) and its privacy grants (location, notifications, …).
# Does NOT wipe: the app binary, or the simulator-wide keychain (shared by all
#        apps; erase the whole simulator if a test needs that gone).
set -euo pipefail

ROOT="${AGENTQA_PROJECT_ROOT:-$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null || pwd)}"

BUNDLE_ID="${1:-${AGENTQA_BUNDLE_ID:-}}"
if [ -z "$BUNDLE_ID" ] && [ -f "$ROOT/.agentqa/config.yml" ]; then
  BUNDLE_ID="$(sed -n 's/^bundle_id:[[:space:]]*\([^#]*\).*/\1/p' "$ROOT/.agentqa/config.yml" \
    | head -1 | tr -d ' "')"
fi
if [ -z "$BUNDLE_ID" ]; then
  echo "reset-app-data: no bundle id (pass one, set AGENTQA_BUNDLE_ID, or configure .agentqa/config.yml)" >&2
  exit 1
fi

if ! xcrun simctl list devices booted | grep -q Booted; then
  echo "reset-app-data: no booted simulator" >&2
  exit 1
fi

# The app must not be running while its container is emptied.
xcrun simctl terminate booted "$BUNDLE_ID" >/dev/null 2>&1 || true

CONTAINER="$(xcrun simctl get_app_container booted "$BUNDLE_ID" data 2>/dev/null || true)"
case "$CONTAINER" in
  */Containers/Data/Application/*)
    # Empty the container, keep the container itself (its path is registered).
    find "$CONTAINER" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
    echo "reset-app-data: wiped data container for $BUNDLE_ID"
    ;;
  *)
    echo "reset-app-data: $BUNDLE_ID not installed on the booted simulator — nothing to wipe" >&2
    ;;
esac

xcrun simctl privacy booted reset all "$BUNDLE_ID" >/dev/null 2>&1 || true
