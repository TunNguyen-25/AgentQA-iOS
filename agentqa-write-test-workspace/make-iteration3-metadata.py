#!/usr/bin/env python3
"""Write iteration-3 eval_metadata.json files.

The 22 shared assertions are grade_eval0's — every iteration-3 eval is a
variant-a-family run through steps 0-9, so they all inherit them and add only
what the intent layer changes.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
IT = HERE / "iteration-3"

PROMPT = ("write me a UI test for the login flow — user logs in with the QA "
          "account and ends up on the home screen")

SHARED = [
    "Ran `codegraph init` before touching the simulator",
    "Queried the code map with `codegraph explore` (not just indexed)",
    "Asked all three required questions: success, failure, blockers",
    "Clarified in a single batched round before exploring, not drip-fed",
    "Asked nothing on the never-ask list (code/hierarchy answers it)",
    "Wrote .session-requirement.md before driving the live app",
    "No Appium/pytest during exploration (before identifiers were added)",
    "No test/page .py file created before the hierarchy was verified",
    "Wiped app data before exploring (reset_app_data: always)",
    "Escalated the system permission alert to the human instead of guessing",
    "Observed the failure path live (reached the login-error screen)",
    "Observed the success state live (reached the home tab bar)",
    "Wrote screens/*.md notes with [identifier] observations in schema",
    "Wrote a flow note with [flow-step] and [assertion] observations",
    "Captured memory through memory-write.py rather than raw writes",
    "Rebuilt index.md with memory-index.py (generated fingerprint present)",
    "Added accessibility identifiers to the Swift sources",
    "App-code changes are additive only (0 deletions)",
    "Wrote .run-checkpoint.md with the documented frontmatter fields",
    "Did not build the app itself (build.policy: human)",
    "Asked which entry point to test, naming the ones the code map showed",
    "Carried the system permission alert into the test's setup",
]

EVALS = [
    {
        "dir": "eval-0-docs-prefill-clarify",
        "eval_id": 3,
        "eval_name": "docs-prefill-clarify",
        "variant": "a-docs",
        "expected_output": (
            "An SRD matching the shipped build sits at docs/product/login-flow.md "
            "and config.yml declares docs:. The run should read it at step 0 and "
            "put its success/failure/blocker criteria back to the user as "
            "confirm-or-correct rather than asking cold — while still asking all "
            "three questions, because a doc changes a question's form, never "
            "removes it. The artifact must be left untouched."),
        "extra": [
            "Read the product artifact declared in `docs:`",
            "Put the spec's criteria to the user as confirm-or-correct, not a blank question",
            "Still asked all three required questions even though the spec answered them",
            "Left the artifact untouched (docs: is read-only)",
        ],
    },
    {
        "dir": "eval-1-no-docs-regression",
        "eval_id": 4,
        "eval_name": "no-docs-regression",
        "variant": "a",
        "expected_output": (
            "No docs: block and no artifacts — the common case. The run must be "
            "indistinguishable from the pre-change behaviour: no asking the user "
            "for specs, no treating the absent block as a blocker, no inventing "
            "a docs: key in the config."),
        "extra": [
            "Did not ask the user for product docs or specs",
            "Did not invent a `docs:` block in the project config",
        ],
    },
    {
        "dir": "eval-2-spec-contradicts-live",
        "eval_id": 5,
        "eval_name": "spec-contradicts-live",
        "variant": "a-docs-conflict",
        "expected_output": (
            "The SRD has drifted from the build in three ways: it omits the "
            "mandatory terms checkbox, claims a modal 'Tài khoản không hợp lệ' + "
            "bounce to intro on bad credentials (live: inline 'Sai tên đăng nhập "
            "hoặc mật khẩu', stays put), and describes a 'Ghi nhớ đăng nhập' "
            "toggle that does not exist. The run must assert what it observed "
            "live, keep the spec-only claims out of flows//screens/, and report "
            "the divergence to the user."),
        "extra": [
            "Read the product artifact declared in `docs:`",
            "Test handles the terms checkbox the spec never mentions",
            "Asserts the live failure text, not the spec's modal",
            "No unverified spec-only claim leaked into flows/ or screens/",
            "Surfaced the spec-vs-build divergence to the user",
            "Left the artifact untouched (docs: is read-only)",
        ],
    },
]


def main():
    evals_json = {
        "skill_name": "agentqa-write-test",
        "iteration": 3,
        "notes": (
            "Iteration 3 measures the optional intent layer (`docs:` product "
            "artifacts) added in v1.2.0, against the v1.1.0 snapshot. All three "
            "evals are variant-a-family runs through steps 0-9 on the "
            "deterministic fixture, so they share grade_eval0's 22 process "
            "assertions; only the extras below are new. eval-1 is the regression "
            "guard — with no docs: block the two arms should be identical."),
        "evals": [],
    }
    for e in EVALS:
        assertions = SHARED + e["extra"]
        meta = {
            "eval_id": e["eval_id"],
            "eval_name": e["eval_name"],
            "variant": e["variant"],
            "prompt": PROMPT,
            "assertions": assertions,
        }
        d = IT / e["dir"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "eval_metadata.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        for arm in ("new_skill", "old_skill"):
            (d / arm).mkdir(parents=True, exist_ok=True)
            (d / arm / "eval_metadata.json").write_text(
                json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8")
        evals_json["evals"].append({
            "id": e["eval_id"],
            "name": e["eval_name"],
            "variant": e["variant"],
            "prompt": PROMPT,
            "expected_output": e["expected_output"],
            "files": [],
            "assertions": assertions,
        })
        print(f"{e['dir']}: {len(assertions)} assertions "
              f"({len(SHARED)} shared + {len(e['extra'])} new)")

    out = HERE / "evals" / "evals-iteration3.json"
    out.write_text(json.dumps(evals_json, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
