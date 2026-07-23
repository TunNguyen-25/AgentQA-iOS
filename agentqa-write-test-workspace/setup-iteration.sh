#!/usr/bin/env bash
# setup-iteration.sh <N>   — assemble all run dirs for iteration N
set -euo pipefail
N="${1:?usage: setup-iteration.sh <iteration number>}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IT="$HERE/iteration-$N"

declare -a EVALS=(
  "eval-0-new-flow-to-build-checkpoint:a"
  "eval-1-resume-after-build:b"
  "eval-2-diagnose-failing-test:c"
)

for entry in "${EVALS[@]}"; do
  name="${entry%%:*}"
  variant="${entry##*:}"
  for arm in with_skill without_skill; do
    # Deliberately no <arm>/outputs here: the viewer stops recursing at the first
    # outputs/ it finds, so an empty one would mask run-1/outputs. publish.py
    # creates the real one.
    "$HERE/fixture/make-run.sh" "$variant" "$IT/$name/$arm/run" >/dev/null
  done
  echo "$name (variant $variant): with_skill + without_skill ready"
done
