#!/usr/bin/env bash
# iteration 2: evals 0 and 1 only (the ones the v1.8.0 edits target),
# new_skill (v1.8.0) vs old_skill (v1.7.0 snapshot), both on the hardened fixture.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IT="$HERE/iteration-2"
for entry in "eval-0-new-flow-to-build-checkpoint:a" "eval-1-resume-after-build:b"; do
  name="${entry%%:*}"; variant="${entry##*:}"
  for arm in new_skill old_skill; do
    "$HERE/fixture/make-run.sh" "$variant" "$IT/$name/$arm/run" >/dev/null
  done
  echo "$name (variant $variant): new_skill + old_skill ready"
done
