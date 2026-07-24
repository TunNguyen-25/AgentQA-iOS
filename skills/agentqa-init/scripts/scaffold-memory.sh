#!/usr/bin/env bash
# Scaffold .agentqa/memory/ in the host repo. Idempotent; keeps existing files.
# Usage: scaffold-memory.sh [--check]   (--check: validate only, non-zero on gaps)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSETS_DIR="$SCRIPT_DIR/../assets/memory-scaffold"
LINT="$SCRIPT_DIR/../../agentqa-write-test/scripts/memory-lint.py"
ROOT="${AGENTQA_PROJECT_ROOT:-$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null || pwd)}"
MEM="$ROOT/.agentqa/memory"

CHECK=0
[ "${1:-}" = "--check" ] && CHECK=1

missing=()
for d in flows screens failures; do
  [ -d "$MEM/$d" ] || missing+=("dir:$MEM/$d")
done
for f in env.md README.md .gitignore; do
  [ -f "$MEM/$f" ] || missing+=("file:$MEM/$f")
done
# index.md is generated, so its absence is fine — but it must be ignored, or it
# lands in every commit and conflicts on every parallel branch.
if [ -f "$MEM/.gitignore" ] && ! grep -qx 'index.md' "$MEM/.gitignore"; then
  missing+=("gitignore-entry:index.md")
fi

if [ "$CHECK" = 1 ]; then
  if [ ${#missing[@]} -ne 0 ]; then
    echo "memory scaffold: MISSING"
    printf '  %s\n' "${missing[@]}"
    exit 1
  fi
  echo "memory scaffold: OK ($MEM)"
  # Structure is only half of healthy — a note with no summary or a mistyped
  # category passes every check above and still answers nothing at Recall.
  if [ -f "$LINT" ] && command -v python3 >/dev/null 2>&1; then
    python3 "$LINT" "$MEM" || exit 1
  else
    echo "memory lint: skipped (agentqa-write-test's memory-lint.py not found)"
  fi
  exit 0
fi

mkdir -p "$MEM/flows" "$MEM/screens" "$MEM/failures"
for d in flows screens failures; do
  [ -f "$MEM/$d/.gitkeep" ] || : > "$MEM/$d/.gitkeep"
done
[ -f "$MEM/env.md" ]     || cp "$ASSETS_DIR/env.md"     "$MEM/env.md"
[ -f "$MEM/README.md" ]  || cp "$ASSETS_DIR/README.md"  "$MEM/README.md"
[ -f "$MEM/.gitignore" ] || cp "$ASSETS_DIR/.gitignore" "$MEM/.gitignore"

# Upgrade path for stores scaffolded before index.md became generated-only.
if ! grep -qx 'index.md' "$MEM/.gitignore"; then
  printf '\n# Generated view, rebuilt from the notes; never committed.\nindex.md\n' \
    >> "$MEM/.gitignore"
  echo "memory scaffold: added index.md to $MEM/.gitignore"
fi
if git -C "$ROOT" ls-files --error-unmatch ".agentqa/memory/index.md" >/dev/null 2>&1; then
  echo "memory scaffold: index.md is still tracked by git — untrack it once with:"
  echo "  git rm --cached .agentqa/memory/index.md"
fi

echo "memory scaffold: ready at $MEM"
