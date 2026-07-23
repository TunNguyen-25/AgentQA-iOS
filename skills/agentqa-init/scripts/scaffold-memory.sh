#!/usr/bin/env bash
# Scaffold .agentqa/memory/ in the host repo. Idempotent; keeps existing files.
# Usage: scaffold-memory.sh [--check]   (--check: validate only, non-zero on gaps)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSETS_DIR="$SCRIPT_DIR/../assets/memory-scaffold"
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

if [ "$CHECK" = 1 ]; then
  if [ ${#missing[@]} -eq 0 ]; then
    echo "memory scaffold: OK ($MEM)"
    exit 0
  fi
  echo "memory scaffold: MISSING"
  printf '  %s\n' "${missing[@]}"
  exit 1
fi

mkdir -p "$MEM/flows" "$MEM/screens" "$MEM/failures"
for d in flows screens failures; do
  [ -f "$MEM/$d/.gitkeep" ] || : > "$MEM/$d/.gitkeep"
done
[ -f "$MEM/env.md" ]     || cp "$ASSETS_DIR/env.md"     "$MEM/env.md"
[ -f "$MEM/README.md" ]  || cp "$ASSETS_DIR/README.md"  "$MEM/README.md"
[ -f "$MEM/.gitignore" ] || cp "$ASSETS_DIR/.gitignore" "$MEM/.gitignore"
echo "memory scaffold: ready at $MEM"
