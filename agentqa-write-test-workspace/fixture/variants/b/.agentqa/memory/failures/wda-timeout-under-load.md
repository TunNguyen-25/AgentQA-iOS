---
title: wda-timeout-under-load
type: failure
tags: [phantom, infra]
summary: WebDriverAgent session timeout when the host is CPU-saturated
last_verified: 2026-07-20
---

# wda-timeout-under-load

## Observations
- [symptom] `WebDriverAgent process failed to start` or a session that hangs for 60s then dies, with no app-side error #infra
- [cause] a CPU-heavy job (usually `codegraph init`) running while the simulator drives the suite #infra
- [remedy] stop the indexing job, wait for load to drop, re-run the suite once #infra
