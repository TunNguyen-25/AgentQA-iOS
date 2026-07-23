#!/bin/bash
# Validate the Android SDK toolchain agent-device + the uiautomator2 driver need.
# Usage: ./install-android-sdk.sh [--check] [--platform <ios|android|both>]
#
# This does NOT auto-install the multi-gigabyte Android SDK — that is a human
# decision (Android Studio, or the command-line tools via Homebrew). It checks
# what's present and prints exact install hints for what's missing, the same way
# the Xcode/Node preflight does. When the platform scope doesn't include Android
# it is a no-op PASS (skipped-with-note), so an iOS-only machine never fails here.
set -uo pipefail
cd "$(dirname "$0")"
source ./common.sh
parse_check_flag "$@"
parse_platform_flag "$@"
SCOPE="$(resolve_platform_scope)"

if ! platform_targets_android "$SCOPE"; then
  ok "Android SDK check skipped (platform scope: $SCOPE)"
  echo "  (Set --platform android/both, or install the Android SDK, to enable Android tests.)"
  exit 0
fi

rc=0

# ANDROID_HOME / ANDROID_SDK_ROOT — where the SDK lives.
if [ -n "${ANDROID_HOME:-}${ANDROID_SDK_ROOT:-}" ]; then
  ok "Android SDK root (${ANDROID_HOME:-$ANDROID_SDK_ROOT})"
else
  err "ANDROID_HOME/ANDROID_SDK_ROOT not set — install the SDK, then export it:"
  echo "    brew install --cask android-commandlinetools   # or Android Studio"
  echo "    export ANDROID_HOME=\"\$HOME/Library/Android/sdk\"   # add to your shell profile"
  rc=1
fi

# adb — the bridge agent-device and the reset path (pm clear) drive Android through.
if command -v adb >/dev/null 2>&1; then
  ok "adb ($(adb version 2>/dev/null | head -1))"
else
  err "adb not found — install platform-tools and add them to PATH:"
  echo "    sdkmanager \"platform-tools\"   # then: export PATH=\"\$ANDROID_HOME/platform-tools:\$PATH\""
  rc=1
fi

# emulator — needed to boot an AVD when no physical device is attached.
if command -v emulator >/dev/null 2>&1; then
  ok "emulator ($(emulator -version 2>/dev/null | head -1 | cut -c1-60))"
else
  warn "emulator not found — needed to boot an AVD (a connected device works without it):"
  echo "    sdkmanager \"emulator\" \"system-images;android-34;google_apis;arm64-v8a\""
  echo "    avdmanager create avd -n agentqa -k \"system-images;android-34;google_apis;arm64-v8a\""
fi

# A JDK — uiautomator2's server build and Gradle need it.
if command -v java >/dev/null 2>&1; then
  ok "java ($(java -version 2>&1 | head -1))"
else
  err "java (JDK 17+) not found — install one: brew install openjdk@17"
  rc=1
fi

# A booted device/emulator is a runtime concern, not a setup one, but surface it.
if command -v adb >/dev/null 2>&1; then
  if adb devices 2>/dev/null | awk 'NR>1 && $2=="device"{found=1} END{exit !found}'; then
    ok "an Android device/emulator is connected"
  else
    warn "no Android device/emulator connected yet — boot an AVD or attach a device before running tests"
  fi
fi

if [ "$rc" != 0 ] && [ "$CHECK_ONLY" = 1 ]; then
  err "Android SDK incomplete (see hints above)"
fi
exit $rc
