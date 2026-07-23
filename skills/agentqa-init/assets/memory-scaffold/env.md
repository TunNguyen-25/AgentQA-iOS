---
title: Environment & project knowledge
type: env
tags: [env]
---
# Environment & project knowledge

Narrative knowledge for this app's UI tests. Structured facts live in
`.agentqa/config.yml`; this file holds the *why* and the gotchas. No secrets —
credential env-var **names** only.

## Observations
- [gotcha] Never run CPU-heavy jobs (e.g. `codegraph init`) during simulator tests — WebDriverAgent times out and produces phantom failures.
- [credential-env] <fill from config.yml — env-var NAMES only, e.g. APP_TEST_USERNAME / APP_TEST_PASSWORD>
- [gotcha] <build-policy rationale — e.g. builds are signed & slow → build.policy: human>
