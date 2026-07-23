# Clarify — ask only what code and the app can't answer

Used by the `agentqa-write-test` skill (step 2) and by `explore`. This **replaces open-ended
brainstorming**: with the source code as a white-box tool and the live app as a
black-box tool, almost everything is discoverable. The human's time is spent on
the one thing neither can tell you — what "pass" means.

**Order matters.** Map the code (CodeGraph) and recall memory *first*, then ask.
A question you could have answered from the screen graph is a question you don't
get to ask.

**One batched round.** Use `AskUserQuestion` with structured options where the
answers are enumerable (environment, objective), free-text otherwise. Don't
drip-feed one question per turn.

**The one-round budget covers requirements, not discoveries.** Exploration will
surface things nobody could have named in advance — a permission prompt, an
unexpected paywall, a screen that contradicts memory. Step 3 *requires* you to
stop and ask when you hit those. That is an escalation, not a second clarify
round, and it does not count against this rule. What the rule forbids is
dribbling out requirement questions one at a time when you could have asked
them together.

## Required — always ask, every run

Never inferred, never skipped "because the request was clear". They are asked
together, in the same batched round.

> **1. When does this test succeed?** — what is the expected user outcome?

e.g. "user can successfully log in", "user can complete checkout and place an
order", "user can reset their password", "user can upload a profile picture".

This is the success criterion. Everything downstream — the assertion, the
edge cases worth covering — derives from it. Restate the answer as a
one-sentence assertion and confirm it before writing any code.

> **2. When does this test fail?** — what does a real failure look like?

e.g. "an inline error under the password field", "stays on the login screen",
"a toast, then back to the start". Two apps can pass the same success criterion
and disagree completely here, and this is what stops you from later "fixing" a
test by loosening its assertion: a failure that matches this answer is the app
telling the truth, not a flaky test.

> **3. What could block this test?**

e.g. an OTP/2FA code the agent can't read, a permission prompt, a paywall,
required backend/test data, a feature flag, a rate limit. Blockers are things
that stop the run without the feature being broken. Each one named here must be
observed live during exploration (step 3) and handled or declared out of scope
before the test is written — a blocker you discover mid-run costs a rewrite.

> **4. Which entry point should the test use?** — *only when step 0 found more
> than one*

A flow is usually reachable from several places: login from the welcome screen,
from an account tab, from a 401 bounce mid-session, from a deep link. Which one
the test should cover is a product decision the code can't make for you — but
*what the options are* is discoverable, so you only earn this question after
`codegraph explore` has shown you the callers. Ask it by listing what you found,
never open-ended:

> "`presentLogin` is called from `IntroductionContentViewController`,
> `ProfileViewController`, and `AppRouter`'s 401 handler. Which of those should
> the test enter through — or all three?"

One entry point in the code map → don't ask, just use it. Several, and the user
picks one → the others are worth a `[flow-step]` note as known-but-uncovered, so
the next run doesn't rediscover them.

### Write the requirement note

Immediately after the answers land, write
`.agentqa/memory/.session-requirement.md` — the ephemeral, one-session summary of
what the user asked for:

```markdown
---
title: Session requirement — <flow>
type: session-requirement
updated: <YYYY-MM-DD>
---
## Request
<the user's idea, verbatim>

## Success
<the confirmed one-sentence assertion>

## Failure
<what a real failure looks like>

## Blockers
- <blocker> → <how it will be handled, or "out of scope">

## Environment / preconditions
<environment, objective, preconditions as answered or sourced>
```

It is the Working-layer artifact steps 3–8 check themselves against — the
answers survive a context break (the build pause), so nothing gets re-asked or
quietly re-invented. Gitignored, never committed. **Delete it at step 9**, or
whenever the session ends without finishing; it describes one session's request
and must never be recalled by the next.

## High-priority — ask only if not already answered

Check `.agentqa/config.yml` and `.agentqa/memory/env.md` first; ask only for what
is genuinely missing or looks stale.

| Question | Examples | Usual source if not asked |
|---|---|---|
| **Which environment?** | production, staging, dev, mock backend, local | `config.yml`, `env.md` |
| **What's the testing objective?** | happy path, regression, exploratory, accessibility, performance, security | the user's request wording |
| **Any required preconditions?** | already logged in, premium account, verified account, feature flag on, specific test data | `env.md`, credential env-var names in `config.yml` |

## Optional — ask when cheap, skip when the user is terse

> **Any known risks or areas of concern?** — recent refactor, new API
> integration, past production bugs, high-priority user complaints.

Prioritizes coverage; never blocks. Record what you hear in the flow note.

## Discover, don't ask

**From source code (white-box):** navigation flows, feature flags, API
integrations, validation rules, business logic, error handling, loading states,
analytics events, permission requirements.

**From runtime exploration (black-box):** screens and UI hierarchy, available
interactions, navigation paths, disabled states, error message copy, edge cases,
accessibility gaps.

### Never ask these

- Where is the button?
- What screens exist?
- What fields are available?
- What happens after tapping X?
- What APIs are called?
- What validations exist?
- How does navigation work?

Each one has an answer in `codegraph explore` (step 0) or the live hierarchy
`agent-device snapshot` shows you (step 3). Asking it tells the user you didn't
look.

## Output of this step

- A one-sentence assertion, confirmed by the human.
- The failure criteria and the named blockers.
- Edge cases you intend to cover (derived from the code map + the outcome).
- Environment / preconditions pinned.
- All of it in `.agentqa/memory/.session-requirement.md`; the parts that outlive
  the session go to `flows/<flow>.md` at Capture, and the in-flight state to the
  run checkpoint at step 5.

## Red flags

- Asking anything on the never-ask list
- Asking about success but not failure and blockers
- Asking before step 0 (code map) and step 1 (recall) have run
- More than one round of **requirement** questions for a single flow —
  escalating a blocker or a memory divergence you hit live in step 3 is
  expected, and never counts as a second round
- Asking which entry point to use without first naming the ones you found
- Starting to write a test with no confirmed one-sentence outcome
- No `.session-requirement.md` written — or one still there after the session
