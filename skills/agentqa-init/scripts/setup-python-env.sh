#!/bin/bash
# Create the project's Appium test venv and install test dependencies.
# Reads test_dir from the host repo's .agentqa/config.yml (default: AutomationTests).
# Usage: ./setup-python-env.sh [--check]
set -uo pipefail
cd "$(dirname "$0")"
source ./common.sh
parse_check_flag "$@"

require_cmd python3 "Install Python 3: brew install python" || exit 1

REPO_ROOT="$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null)"
# When the skill lives inside the host repo (e.g. .claude/skills/agentqa), the
# toplevel found above is the skill repo itself if it was cloned as a git repo.
# Prefer the invoking directory's repo: honor AGENTQA_PROJECT_ROOT when set.
REPO_ROOT="${AGENTQA_PROJECT_ROOT:-$REPO_ROOT}"
[ -n "$REPO_ROOT" ] || { err "Not inside a git repo — set AGENTQA_PROJECT_ROOT to the app repository"; exit 1; }

CONFIG="$REPO_ROOT/.agentqa/config.yml"
TEST_DIR_NAME="$(grep -E '^test_dir:' "$CONFIG" 2>/dev/null | sed -E 's/^test_dir:[[:space:]]*//' | tr -d '"' || true)"
TESTS_DIR="$REPO_ROOT/${TEST_DIR_NAME:-AutomationTests}"

if [ ! -f "$TESTS_DIR/requirements.txt" ]; then
  err "$TESTS_DIR/requirements.txt not found — run '/agentqa-init init' in the project first"
  exit 1
fi

if [ -x "$TESTS_DIR/.venv/bin/pytest" ]; then
  ok "venv present ($("$TESTS_DIR/.venv/bin/pytest" --version 2>/dev/null | head -1))"
else
  if [ "$CHECK_ONLY" = 1 ]; then err "venv missing or incomplete at $TESTS_DIR/.venv"; exit 1; fi
  echo "Creating venv and installing requirements..."
  python3 -m venv "$TESTS_DIR/.venv" || { err "venv creation failed"; exit 1; }
  "$TESTS_DIR/.venv/bin/pip" install -q -r "$TESTS_DIR/requirements.txt" \
    || { err "pip install failed"; exit 1; }
  ok "venv ready"
fi

if (cd "$TESTS_DIR" && ./.venv/bin/pytest --collect-only -q >/dev/null 2>&1); then
  ok "pytest collects the test suite"
else
  err "pytest cannot collect tests — check requirements.txt / python version"
  exit 1
fi
