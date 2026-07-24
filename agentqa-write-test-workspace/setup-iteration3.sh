#!/usr/bin/env bash
# iteration 3: the intent layer (`docs:` product artifacts).
#   new_skill = v1.2.0 (reads docs:)   old_skill = v1.1.0 snapshot (no such concept)
#
#   eval-0  a-docs           accurate SRD  -> should pre-fill the clarify round
#   eval-1  a                no docs       -> must behave exactly as before
#   eval-2  a-docs-conflict  drifted SRD   -> the live build must win
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IT="$HERE/iteration-3"

for entry in "eval-0-docs-prefill-clarify:a-docs" \
             "eval-1-no-docs-regression:a" \
             "eval-2-spec-contradicts-live:a-docs-conflict"; do
  name="${entry%%:*}"; variant="${entry##*:}"
  for arm in new_skill old_skill; do
    "$HERE/fixture/make-run.sh" "$variant" "$IT/$name/$arm/run" >/dev/null
  done
  echo "$name (variant $variant): new_skill + old_skill ready"
done

python3 "$HERE/make-iteration3-metadata.py"
