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
#
# Exits non-zero if it could not wipe — including when the app is not installed.
# A caller that genuinely does not care can `|| true`, but the default has to be
# loud: a reset that silently did nothing leaves the next test running against
# yesterday's state, and that surfaces later as a flaky test rather than as this
# script's problem.
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

  # Whether the app is installed is simctl's answer to give, not something to
  # infer from the shape of what it printed: those are different questions, and
  # conflating them meant any path simctl did not phrase as expected was read as
  # "not installed" and the wipe was skipped with a misleading message.
  local container status=0 errfile
  errfile="$(mktemp "${TMPDIR:-/tmp}/reset-app-data.XXXXXX")"
  container="$(xcrun simctl get_app_container booted "$bundle" data 2>"$errfile")" || status=$?
  if [ "$status" -ne 0 ]; then
    echo "reset-app-data: $bundle is not installed on the booted simulator" \
         "(simctl get_app_container exited $status) — install the build first" >&2
    # Pass simctl's own words through: "exited 4" and "xcrun: command not found"
    # need very different fixes, and only simctl can tell them apart.
    if [ -s "$errfile" ]; then
      sed 's/^/reset-app-data:   simctl: /' "$errfile" >&2
    fi
    rm -f "$errfile"
    exit 1
  fi
  rm -f "$errfile"

  # The shape check is now a safety guard on `rm -rf`, not an install probe. An
  # unexpected path means simctl told us something this script does not
  # understand, so stop rather than delete inside it — or quietly skip it.
  case "$container" in
    */Containers/Data/Application/*) ;;
    "")
      echo "reset-app-data: simctl reported no data container path for $bundle" \
           "(exit 0 with empty output) — refusing to guess" >&2
      exit 1
      ;;
    *)
      echo "reset-app-data: simctl reported an unexpected data container for $bundle:" >&2
      echo "reset-app-data:   $container" >&2
      echo "reset-app-data: expected a */Containers/Data/Application/* path;" \
           "refusing to delete anything under it. Wipe it by hand, or use" \
           "\`xcrun simctl uninstall\` if losing the build is acceptable." >&2
      exit 1
      ;;
  esac
  if [ ! -d "$container" ]; then
    echo "reset-app-data: data container for $bundle does not exist: $container" >&2
    exit 1
  fi

  find "$container" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
  echo "reset-app-data: wiped data container for $bundle ($container)"
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
    echo "reset-app-data: $pkg is not installed on the device — install the build first" >&2
    exit 1
  fi
  # pm clear empties data + cache and revokes runtime permissions; the APK stays.
  # `adb shell` reports the exit status of adb, not of the command it ran, so the
  # only trustworthy signal here is pm's own "Success" line — same failure mode as
  # the iOS branch above, one layer further out.
  local out
  out="$("${adb_target[@]}" shell pm clear "$pkg" 2>&1 || true)"
  case "$out" in
    *Success*)
      echo "reset-app-data: cleared data + permissions for $pkg"
      ;;
    *)
      echo "reset-app-data: pm clear did not report success for $pkg:" \
           "${out:-<no output>}" >&2
      exit 1
      ;;
  esac
}

case "$PLATFORM" in
  android) reset_android "${1:-}";;
  ios|"")  reset_ios "${1:-}";;
  *) echo "reset-app-data: unknown platform '$PLATFORM' (use ios or android)" >&2; exit 1;;
esac
