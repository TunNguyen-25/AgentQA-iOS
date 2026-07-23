#!/usr/bin/env bash
# Wipe an installed app's local data on the booted device, WITHOUT uninstalling
# it — a `build.policy: human` project keeps the build a person installed by hand.
#
# Usage: reset-app-data.sh [<app_id>]
#   app id resolution: argument > $AGENTQA_BUNDLE_ID/$AGENTQA_APP_PACKAGE >
#                      .agentqa/config.yml (bundle_id on iOS, app_package on Android)
#   platform resolution: $AGENTQA_PLATFORM > `platform:` in config.yml > ios
#
# iOS: empties the data container (Documents/, Library/ — incl. NSUserDefaults —,
#      tmp/, SystemData/) and resets privacy grants.
# Android: `adb shell pm clear` — clears the app's data + cache and revokes its
#      runtime permissions. Keeps the APK, so a human-installed build survives.
# Neither wipes the app binary or the shared keychain/keystore.
set -euo pipefail

ROOT="${AGENTQA_PROJECT_ROOT:-$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null || pwd)}"
CONFIG="$ROOT/.agentqa/config.yml"

# Read a top-level scalar from config.yml (comment/quote-stripped).
config_get() {
  [ -f "$CONFIG" ] || return 0
  sed -n "s/^$1:[[:space:]]*\([^#]*\).*/\1/p" "$CONFIG" | head -1 | tr -d ' "'
}

PLATFORM="${AGENTQA_PLATFORM:-$(config_get platform)}"
PLATFORM="${PLATFORM:-ios}"

reset_ios() {
  local bundle="${1:-${AGENTQA_BUNDLE_ID:-$(config_get bundle_id)}}"
  if [ -z "$bundle" ]; then
    echo "reset-app-data: no bundle id (pass one, set AGENTQA_BUNDLE_ID, or configure .agentqa/config.yml)" >&2
    exit 1
  fi
  if ! xcrun simctl list devices booted | grep -q Booted; then
    echo "reset-app-data: no booted simulator" >&2
    exit 1
  fi
  # The app must not be running while its container is emptied.
  xcrun simctl terminate booted "$bundle" >/dev/null 2>&1 || true
  local container
  container="$(xcrun simctl get_app_container booted "$bundle" data 2>/dev/null || true)"
  case "$container" in
    */Containers/Data/Application/*)
      find "$container" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
      echo "reset-app-data: wiped data container for $bundle"
      ;;
    *)
      echo "reset-app-data: $bundle not installed on the booted simulator — nothing to wipe" >&2
      ;;
  esac
  xcrun simctl privacy booted reset all "$bundle" >/dev/null 2>&1 || true
}

reset_android() {
  local pkg="${1:-${AGENTQA_APP_PACKAGE:-$(config_get app_package)}}"
  if [ -z "$pkg" ]; then
    echo "reset-app-data: no app package (pass one, set AGENTQA_APP_PACKAGE, or configure .agentqa/config.yml)" >&2
    exit 1
  fi
  command -v adb >/dev/null 2>&1 || { echo "reset-app-data: adb not found (install the Android SDK platform-tools)" >&2; exit 1; }
  # Target a single connected device; if several are attached, $ANDROID_SERIAL picks one.
  # Build the -s flag as an array, expanded safely so an empty array is fine under
  # `set -u` on macOS's bash 3.2 (the ${arr[@]+…} guard).
  local serial_flag=()
  [ -n "${ANDROID_SERIAL:-}" ] && serial_flag=(-s "$ANDROID_SERIAL")
  local adb_target=(adb ${serial_flag[@]+"${serial_flag[@]}"})
  if ! "${adb_target[@]}" get-state >/dev/null 2>&1; then
    echo "reset-app-data: no Android device/emulator connected (set ANDROID_SERIAL if several are attached)" >&2
    exit 1
  fi
  if ! "${adb_target[@]}" shell pm list packages 2>/dev/null | grep -qx "package:$pkg"; then
    echo "reset-app-data: $pkg not installed on the device — nothing to wipe" >&2
    return 0
  fi
  # pm clear empties data + cache and revokes runtime permissions; the APK stays.
  "${adb_target[@]}" shell pm clear "$pkg" >/dev/null
  echo "reset-app-data: cleared data + permissions for $pkg"
}

case "$PLATFORM" in
  android) reset_android "${1:-}";;
  ios|"")  reset_ios "${1:-}";;
  *) echo "reset-app-data: unknown platform '$PLATFORM' (use ios or android)" >&2; exit 1;;
esac
