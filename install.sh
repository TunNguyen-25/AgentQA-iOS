#!/bin/bash
# agentqa installer — place the skill into your harness's skills directory.
#
# One-liner:  curl -fsSL https://raw.githubusercontent.com/TunNguyen-25/AgentQA-iOS/main/install.sh | bash
# Manual:     git clone https://github.com/TunNguyen-25/AgentQA-iOS.git && cd AgentQA-iOS && ./install.sh
#
# Flags: --global | --project (default) | --ref <tag|branch> | --harness <id> | --setup | -h
set -uo pipefail

REPO_URL="https://github.com/TunNguyen-25/AgentQA-iOS.git"
INIT_PAYLOAD="SKILL.md references scripts assets"
WRITE_TEST_PAYLOAD="SKILL.md references scripts assets"

SCOPE=project; REF=main; HARNESS_OVERRIDE=""; RUN_SETUP=0
usage() {
  cat <<'EOF'
Usage: install.sh [--global] [--project] [--ref <tag|branch>] [--harness <id>] [--setup]
  --project (default)  install into the current app repo's skills dir
  --global             install into your user-level skills dir ($HOME)
  --ref <tag|branch>   version to fetch when cloning (default: main)
  --harness <id>       override harness detection (or set AGENTQA_HARNESS)
  --setup              run scripts/setup-all.sh after installing (default: no)
EOF
}
while [ $# -gt 0 ]; do
  case "$1" in
    --global)  SCOPE=global;;
    --project) SCOPE=project;;
    --ref)     shift; REF="${1:-main}";;
    --harness) shift; HARNESS_OVERRIDE="${1:-}";;
    --setup)   RUN_SETUP=1;;
    -h|--help) usage; exit 0;;
    *) echo "unknown arg: $1" >&2; usage; exit 2;;
  esac
  shift
done

INVOKE_DIR="$PWD"

# --- resolve the source: explicit override, local checkout, or a temp clone ---
SELF_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ]; then
  SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || true)"
fi
if [ -n "${AGENTQA_INSTALL_SRC:-}" ]; then
  SRC="$AGENTQA_INSTALL_SRC"
elif [ -n "$SELF_DIR" ] && [ -f "$SELF_DIR/skills/agentqa-init/SKILL.md" ] && [ -d "$SELF_DIR/skills/agentqa-init/scripts" ]; then
  SRC="$SELF_DIR"
else
  command -v git >/dev/null 2>&1 || { echo "git is required to fetch the skill" >&2; exit 1; }
  TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
  echo "Fetching agentqa ($REF)…"
  if ! git clone --depth 1 --branch "$REF" "$REPO_URL" "$TMP" 2>/dev/null; then
    rm -rf "$TMP"; mkdir -p "$TMP"
    git clone --depth 1 "$REPO_URL" "$TMP" 2>/dev/null \
      || { echo "clone failed: $REPO_URL" >&2; exit 1; }
  fi
  SRC="$TMP"
fi
[ -f "$SRC/skills/agentqa-init/scripts/common.sh" ] || { echo "invalid source (no skills/agentqa-init/scripts/common.sh): $SRC" >&2; exit 1; }

# --- resolve harness + its skills subpath (reuse the skill's own table) ---
[ -n "$HARNESS_OVERRIDE" ] && export AGENTQA_HARNESS="$HARNESS_OVERRIDE"
# shellcheck source=/dev/null
source "$SRC/skills/agentqa-init/scripts/common.sh"
resolve_harness || exit 1
SUBPATH="$(harness_skills_dir "$HARNESS")"

# --- unsupported harness: print manual note, never fail ---
if [ -z "$SUBPATH" ]; then
  echo "agentqa isn't auto-installable for harness '$HARNESS' yet (marketplace support planned)."
  echo "Copy these from $SRC/skills/agentqa-init/ into your $HARNESS skills directory as a folder named 'agentqa-init/':"
  for i in $INIT_PAYLOAD; do echo "  $i"; done
  echo "…and these from $SRC/skills/agentqa-write-test/ into a sibling folder named 'agentqa-write-test/':"
  for i in $WRITE_TEST_PAYLOAD; do echo "  $i"; done
  exit 0
fi

# --- compute destination root ---
if [ "$SCOPE" = global ]; then
  ROOT="$HOME"
else
  ROOT="$(git -C "$INVOKE_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
  [ -n "$ROOT" ] || { echo "Not inside a git repo. Run from your app repo, or pass --global." >&2; exit 1; }
fi
DEST="$ROOT/$SUBPATH/agentqa-init"

# --- copy a skill's payload allowlist (idempotent, per-item replace) ---
install_skill() {  # $1=src_dir  $2=dest_dir  rest=payload items
  local src="$1" dest="$2"; shift 2
  local item
  mkdir -p "$dest"
  for item in "$@"; do
    if [ -e "$src/$item" ]; then
      rm -rf "$dest/$item"
      cp -R "$src/$item" "$dest/$item"
    fi
  done
}

install_skill "$SRC/skills/agentqa-init" "$DEST" $INIT_PAYLOAD
echo "Installed agentqa-init -> $DEST"

# agentqa-write-test is self-contained; it only needs a repo configured by agentqa-init.
WRITE_TEST_DEST="$ROOT/$SUBPATH/agentqa-write-test"
if [ -d "$SRC/skills/agentqa-write-test" ]; then
  install_skill "$SRC/skills/agentqa-write-test" "$WRITE_TEST_DEST" $WRITE_TEST_PAYLOAD
  echo "Installed agentqa-write-test -> $WRITE_TEST_DEST"
fi

# --- optional setup ---
if [ "$RUN_SETUP" = 1 ]; then
  echo "Running setup-all.sh…"
  if ! ( cd "$ROOT" && "$DEST/scripts/setup-all.sh" ); then
    echo "Note: setup-all.sh reported an issue — the skill itself is installed at $DEST." >&2
    [ "$SCOPE" = global ] && echo "  A global install has no app repo; run setup from inside your app repo (or '/agentqa-init setup')." >&2
  fi
else
  echo "Next: run '/agentqa-init setup' in your agent (or: $DEST/scripts/setup-all.sh)."
fi
exit 0
