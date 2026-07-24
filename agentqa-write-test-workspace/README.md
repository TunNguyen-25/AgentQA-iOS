# agentqa-write-test eval harness

Measures whether `skills/agentqa-write-test` actually changes behaviour, against
a deterministic mock of an iOS app instead of a real simulator.

Live runs were not usable for a tight loop: the real project's backend is
404-blocked, `build.policy: human` stalls an unattended run at step 5, and each
attempt costs 10–30 minutes with non-deterministic results. This fixture keeps
the parts that decide skill quality — ordering, the clarify contract, memory
hygiene, cleanup — and makes them checkable in about seven minutes a run.

## Layout

| Path | What it is |
|---|---|
| `fixture/app-repo/` | Mock MyTV repo: Swift/UIKit sources, `.agentqa/config.yml`, `AutomationTests/` |
| `fixture/bin/` | Shims on PATH: `agent-device`, `codegraph`, `xcrun`, `adb`, `page-source`, `pytest`, `ask-user` |
| `fixture/bin/appstate.py` | The screen graph every shim shares, plus the call log |
| `fixture/variants/{a,b,c}/` | Overlays: new flow · post-build resume · failing test |
| `fixture/variants/a-docs/` | = `a` + a `docs:` block and an SRD that **matches** the build |
| `fixture/variants/a-docs-conflict/` | = `a` + a `docs:` block and an SRD that has **drifted** from the build |
| `fixture/make-run.sh` | Assembles one isolated run (`repo/`, `state/`, `env.sh`) |
| `setup-iteration.sh N` | Builds all six run dirs for iteration N |
| `setup-iteration3.sh` | Builds iteration 3 (the intent layer) + its eval metadata |
| `watch-runs.py` | Records file create/delete events — ordering claims need a timeline |
| `grade.py` | The assertions; writes `grading.json` |
| `publish.py` | Builds review artifacts and the layout the viewer/aggregator expect |
| `evals/evals.json` | Prompts, expected outputs, assertion lists |
| `evals/evals-iteration3.json` | The same, for the intent-layer evals |
| `skill-snapshot-v1.7.0/` | Previous skill version, used as the iteration-2 baseline |
| `skill-snapshot-v1.1.0/` | v1.1.0 of both skills, the iteration-3 baseline |

## Running an iteration

```bash
./setup-iteration.sh 3
nohup python3 watch-runs.py iteration-3 1.5 > watch.log 2>&1 &
```

Then spawn one subagent per run. Each prompt must: point at the skill, tell the
agent to `source <run>/env.sh` at the start of every bash call, and state the
harness facts — `ask-user "<q>"` is the only channel to the human, `page-source`
replaces the Appium MCP, and `xcodebuild` is off limits. Both arms get identical
wording apart from the skill path.

Afterwards, per run:

```bash
python3 grade.py iteration-3/<eval>/<arm> <eval_id>
python3 publish.py iteration-3/<eval>/<arm> '{"total_tokens":N,"duration_ms":M,"total_duration_seconds":S}'
```

Timing comes from the subagent completion notification and is not recorded
anywhere else — capture it when the notification arrives or it is lost.

Then aggregate and review (skill-creator scripts need Python ≥3.10):

```bash
SC=~/.claude/plugins/cache/claude-plugins-official/skill-creator/unknown/skills/skill-creator
(cd "$SC" && python3.12 -m scripts.aggregate_benchmark <abs>/iteration-3 --skill-name agentqa-write-test)
python3.12 "$SC/eval-viewer/generate_review.py" <abs>/iteration-3 \
  --skill-name agentqa-write-test --benchmark <abs>/iteration-3/benchmark.json \
  --previous-workspace <abs>/iteration-2
```

## Two things that make it work

**Identifiers resolve from the Swift sources.** `page-source` and `pytest` read
whatever `accessibilityIdentifier` the code assigns, so add → verify → locate is
a real loop; a locator for an identifier nobody added fails like Appium would.

**Everything is timestamped.** Shims log to `state/calls.jsonl`, questions to
`state/questions.jsonl`, the watcher to `fs-timeline.jsonl`. Ordering assertions
read those, because a file written at step 2 and deleted at step 9 leaves no
trace in the final tree.

## Reading the numbers

Iteration 1 (v1.7.0 vs no skill) scored 100% against 64%, but only **18 of 45
assertions discriminate**. The other 27 are things a competent agent does
unprompted — page objects, env-var credentials, refusing to weaken an assertion
— and they inflate the headline without saying anything about the skill. Judge
changes on the discriminating subset.

Iteration 2 (v1.8.0 vs v1.7.0, same fixture) moved exactly one assertion: the
entry-point question. That is the honest size of that change.

Iteration 3 (v1.2.0 vs v1.1.0) measures the **intent layer** — the optional
`docs:` block that lets the skill read SRDs / PM scenarios as *intent, never
truth*. Three evals, all variant-a-family runs through steps 0-9, sharing
`grade_eval0`'s 22 process assertions:

| Eval | Variant | What it isolates |
|---|---|---|
| `eval-0-docs-prefill-clarify` | `a-docs` | An accurate SRD should turn the clarify round from blank questions into confirm-or-correct — without dropping any of the three required questions. |
| `eval-1-no-docs-regression` | `a` | No `docs:` block: the two arms should be **identical**. This is the regression guard, and a delta here is a bug, not a win. |
| `eval-2-spec-contradicts-live` | `a-docs-conflict` | The SRD omits the mandatory terms checkbox, claims a modal + bounce on bad credentials, and invents a "Ghi nhớ đăng nhập" toggle. The live build must win, the spec-only claims must stay out of `flows/`/`screens/`, and the divergence must be reported. |

**Result: new 77/78, old 75/78 — and 0 of the 12 new intent-layer assertions
discriminate.** All twelve passed in *both* arms. The only two differing
assertions were pre-existing shared ones, at n=1 each, and neither concerns
artifacts: eval-0's batched-round (the old arm re-asked because the `ask-user`
shim misrouted an answer) and eval-2's screens/*.md schema. The headline
"99% vs 96%" is noise.

Why the baseline kept pace, in both directions:

- It **read the artifact anyway.** A capable agent browsing the repo finds a
  visible `docs/` folder whether or not the skill mentions one. The premise that
  `docs:` is what makes the agent read the docs does not hold when the docs are
  sitting in the working tree.
- It **already refused to trust it.** "Code reading lies; only the live hierarchy
  is truth" generalises to specs unaided. The drifted SRD was built so that
  trusting it yields a test that *cannot pass* (it omits the terms checkbox that
  gates submit), and the baseline caught all three planted divergences, asserted
  live behaviour, and kept the spec-only claims out of `flows/`/`screens/`.

So v1.2.0 shipped the **plumbing** (config surface, init detection, provenance
model) and the guardrail prose was **trimmed back out** — 5 rationalization rows
and 3 red flags that earned nothing measurable, because the creed already covered
them. What this fixture cannot measure, and what the plumbing is actually for:
discoverability when the specs live somewhere the agent would never browse,
scoping across a large doc set (there is one small doc here), and behaviour on
weaker models where the creed may not generalise as reliably.

Two harness faults this iteration exposed, both deferred as separate work:

- **`ask-user` misroutes answers** — bucket ordering. `"block"` is tested before
  `"permission"`, so a permission question mentioning "blocks the flow" gets the
  blockers answer; success questions phrased with "username/password" fall
  through to the credentials bucket. Every one of the six runs hit it, and it
  costs both arms the batched-round assertion. Reorder the buckets and match on
  intent, not substrings.
- **`reset-app-data.sh` infers "not installed" from path *shape***
  (`*/Containers/Data/Application/*`) rather than `get_app_container`'s exit
  code, so an unexpected shape silently skips the wipe while printing a
  misleading message. On a real simulator the path does match, so this is
  primarily a fixture-fidelity gap — the shim returns an unrealistic path — that
  exposed a latent robustness flaw in the shipped script.

## Known limits

- `memory-write.py` runs by absolute path, so it never reaches the shim log.
  Assertions about it lean on the run's own summary or on note contents.
- The mock app is one flow. It exercises process discipline, not Appium breadth.
- `ask-user` answers are keyword-routed; a question phrased unusually gets a
  neutral reply, which reads as the reviewer dodging. Widen `ANSWERS` when that
  shows up in a transcript.
- Assertions have been the fragile part, not the skill: six graders bugs were
  found and fixed across two iterations, every one a false positive. Treat a new
  failure as suspect until you have read the evidence behind it.
- **Android coverage is partial by design.** The `adb` shim + the platform-aware
  `reset-app-data.sh`/`conftest.py` make the *deterministic* Android plumbing
  (green-loop preconditions, `pm clear` reset) exercisable without an emulator,
  and `skills/agentqa-init/tests/test_conftest_reset.py` unit-tests both driver
  branches. A full Android *exploration* fixture (a mock Kotlin/Compose app with
  its own state machine) is deferred — the current `appstate` screen graph is the
  iOS/Swift app, so an end-to-end Android behaviour eval still needs a real
  device. Adding Android was validated by the unit tests + shim smoke tests, not
  a live green run.
