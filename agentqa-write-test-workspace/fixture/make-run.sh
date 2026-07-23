#!/usr/bin/env bash
# make-run.sh <variant a|b|c> <run root>
#
# Assembles one isolated eval run:
#   <run root>/repo/        the mock app repo the agent works in (clean — no eval scaffolding)
#   <run root>/state/       shim state + call logs (outside the repo, so the agent never trips over it)
#   <run root>/env.sh       sourced by the runner to put the shims on PATH
#
# Shims stay in the shared fixture/bin so they are not discoverable by browsing
# the repo; only .venv/bin/pytest is a thin wrapper inside the repo, because the
# skill invokes it by that path.
set -euo pipefail

VARIANT="${1:?usage: make-run.sh <a|b|c> <run root>}"
ROOT="${2:?usage: make-run.sh <a|b|c> <run root>}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

REPO="$ROOT/repo"
STATE="$ROOT/state"

rm -rf "$ROOT"
mkdir -p "$REPO" "$STATE"
cp -R "$HERE/app-repo/." "$REPO/"
cp -R "$HERE/variants/$VARIANT/." "$REPO/"

# .venv/bin/pytest — the path the skill calls; delegates to the shared shim
mkdir -p "$REPO/AutomationTests/.venv/bin"
cat > "$REPO/AutomationTests/.venv/bin/pytest" <<EOF
#!/usr/bin/env bash
exec "$HERE/bin/pytest" "\$@"
EOF
chmod +x "$REPO/AutomationTests/.venv/bin/pytest"

# keep memory dirs present even when a variant seeds nothing into them
mkdir -p "$REPO/.agentqa/memory/flows" \
         "$REPO/.agentqa/memory/screens" \
         "$REPO/.agentqa/memory/failures"
for d in flows screens failures; do
  [ -e "$REPO/.agentqa/memory/$d/.gitkeep" ] || touch "$REPO/.agentqa/memory/$d/.gitkeep"
done

# a real git repo so step 4's `git diff --numstat` additive check works
git -C "$REPO" init -q
git -C "$REPO" add -A
git -C "$REPO" -c user.email=eval@local -c user.name=eval commit -qm "fixture baseline"

cat > "$ROOT/env.sh" <<EOF
export AGENTQA_EVAL_REPO="$REPO"
export AGENTQA_EVAL_STATE="$STATE"
export PATH="$HERE/bin:\$PATH"
export APP_TEST_USERNAME=mytv_qa
export APP_TEST_PASSWORD='Qa!2026pass'
EOF

echo "run ready: $REPO (variant $VARIANT), state in $STATE"
