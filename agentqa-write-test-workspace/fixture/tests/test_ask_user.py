"""Routing tests for the `ask-user` shim.

The shim stands in for the human reviewer, so a misrouted answer is not a
cosmetic bug: the agent gets a reply to a question it did not ask, spends a turn
re-asking, and the run loses the batched-clarify assertion. Every iteration-3 run
hit that. These tests exist so a future edit to the signal tables cannot bring it
back silently.

Two layers:

* the rule tests below state the routing contract by hand — they are the spec;
* `routing-corpus.json` is every question the six iteration-3 runs actually
  asked, verbatim, pinned to the route it should get. Those expectations were
  checked against the transcripts one by one, so a diff there means routing
  moved for a real question and needs a look, not a rubber stamp.

Run with: python3 -m pytest fixture/tests
"""
import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURE = Path(__file__).resolve().parent.parent
SHIM = FIXTURE / "bin" / "ask-user"
CORPUS = Path(__file__).resolve().parent / "routing-corpus.json"


@pytest.fixture(scope="module")
def shim(tmp_path_factory):
    """Import the extensionless shim as a module (it has no .py suffix)."""
    import os
    os.environ.setdefault("AGENTQA_EVAL_STATE",
                          str(tmp_path_factory.mktemp("state")))
    loader = importlib.machinery.SourceFileLoader("ask_user", str(SHIM))
    spec = importlib.util.spec_from_loader("ask_user", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


# --------------------------------------------------------------- the two bugs
def test_permission_question_is_not_shadowed_by_the_block_bucket(shim):
    """The original fault: "block" was tested before "permission"."""
    q = ("Re-asking - your last answer restated the blockers but did not pick an "
         "action, and I must not guess at a system dialog. The notifications alert "
         "is on screen RIGHT NOW and blocks the flow. Answer with exactly one word: "
         "ALLOW or DENY.")
    assert shim.route(q)[0] == "permission"
    assert "Don't Allow" in shim.answer_for(q)


def test_blocker_labelled_question_that_asks_for_a_button_is_a_permission_question(shim):
    """The label is evidence, not a verdict — choose-a-button phrasing outweighs it."""
    q = ("BLOCKER ESCALATION (step 3, live): on launch of a freshly wiped app the "
         "SpringBoard alert '\"MyTV\" Would Like to Send You Notifications' is on "
         "screen with buttons 'Don't Allow' and 'Allow'. Which action should I take, "
         "both now while exploring and in the test's setup: 'Allow' or 'Don't Allow'?")
    assert shim.route(q)[0] == "permission"


def test_blockers_question_that_only_mentions_the_prompt_stays_in_blockers(shim):
    """The mirror image: describing the prompt is not asking which button to tap."""
    q = ("3) BLOCKERS — what could stop this test from running end-to-end? "
         "IntroductionContentViewController.viewDidLoad calls "
         "NotificationPermission.requestIfNeeded(), so a notification permission "
         "dialog appears on first launch. Any OTP/2FA or rate limiting on the QA "
         "account?")
    assert shim.route(q) == ["blockers"]


def test_success_question_quoting_credentials_is_not_answered_with_credentials(shim):
    """Every success question names the QA account; that must not decide the route."""
    q = ("1) SUCCESS — when does this test pass? I've mapped the code: "
         "LoginViewController.handle(result:) calls AppRouter.presentHome(guest:false). "
         "I'll sign in with the QA account from APP_TEST_USERNAME / APP_TEST_PASSWORD. "
         "Is landing on the MainTabBarController tab bar the assertion you want?")
    assert shim.route(q) == ["success"]
    assert "Success =" in shim.answer_for(q)


def test_build_handoff_listing_a_wrong_password_test_is_not_a_failure_question(shim):
    """Test names leak the neighbours' vocabulary into every handoff."""
    q = ("BUILD HANDOFF (build.policy: human — I will not run xcodebuild). I added 11 "
         "accessibility identifiers, additive only. The suite now has "
         "test_login_happy_path and test_login_wrong_password. Please build and "
         "install on the booted simulator and tell me when it's ready.")
    assert shim.route(q) == ["build"]


def test_review_checkpoint_is_an_approval_not_a_success_or_failure_question(shim):
    q = ("REVIEW CHECKPOINT — suite is green: 3 passed in 12.4s. APP-CODE DIFF "
         "(additions only, zero deletions): identifiers on LoginView, "
         "MainTabBarController. Tests: test_login_happy_path, "
         "test_login_wrong_password. Approve, or tell me what to change?")
    assert shim.route(q) == ["approval"]


# ------------------------------------------------------------- word matching
@pytest.mark.parametrize("phrase, decoy_bucket", [
    ("password", "success"),      # `pass` must not fire inside `password`
    ("not allowed to guess", "permission"),   # `allow` must not fire in `allowed`
])
def test_signals_match_words_not_substrings(shim, phrase, decoy_bucket):
    assert shim.scores(f"Some neutral sentence about {phrase}.")[decoy_bucket] == 0


@pytest.mark.parametrize("spelling", [
    "Don't Allow", "DONT_ALLOW", "dont-allow", "don’t allow",
])
def test_button_spellings_normalise_together(shim, spelling):
    q = f"The notifications alert is up. Which button: Allow, or {spelling}?"
    assert shim.route(q)[0] == "permission"


def test_a_question_matching_nothing_gets_the_neutral_reply(shim):
    q = "Quick one: do you take milk in your coffee?"
    assert shim.route(q) == []
    assert shim.answer_for(q) == shim.NEUTRAL


# ------------------------------------------------------------- the lede rules
def test_the_opening_clause_outweighs_the_body(shim):
    """Intent lives in the label; the body names every neighbouring topic."""
    q = ("ENVIRONMENT — APP_TEST_USERNAME (mytv_qa) and APP_TEST_PASSWORD are already "
         "exported in my shell. Is staging what this test should run against?")
    assert shim.route(q)[0] == "environment"
    assert shim.answer_for(q).startswith("staging")


@pytest.mark.parametrize("question, expected", [
    ("1. SUCCESS — when does this test pass? Details…", "1. SUCCESS "),
    ("1) SUCCESS — when does this test pass? Details…", "1) SUCCESS "),
    ("(2) BLOCKERS: what could stop this?", "(2) BLOCKERS"),
    ("SUCCESS — what counts as passing?", "SUCCESS "),
])
def test_the_opening_clause_is_the_label_and_nothing_more(shim, question, expected):
    """Numbering must not cut it short, and the body must not get folded in."""
    assert shim.lede_of(question) == expected


def test_a_short_label_does_not_leak_the_body_into_the_opening_clause(shim):
    """With too high a floor the dash here is skipped, the whole sentence becomes
    the label, and `APP_TEST_USERNAME` earns a boosted credentials hit."""
    q = ("1) SUCCESS — when does this test pass, given the QA account in "
         "APP_TEST_USERNAME?")
    assert shim.route(q) == ["success"]


def test_a_recap_opener_forfeits_the_lede_boost(shim):
    """A follow-up quotes the last answer; boosting that re-sends what was wrong."""
    q = ("Re-asking only Q1 (your answer covered the credentials, which I've noted - "
         "QA account comes from APP_TEST_USERNAME / APP_TEST_PASSWORD - but it didn't "
         "pin the SUCCESS criterion, and I must not invent it). Confirm or correct "
         "this one-sentence assertion: after entering the QA account credentials and "
         "ticking terms, the MainTabBarController home screen is shown.")
    assert shim.is_recap(q)
    assert shim.route(q)[0] == "success", "the re-ask wants the answer it did NOT get"


def test_a_passing_mention_of_you_said_is_not_a_recap(shim):
    """The marker only counts at the top, where a follow-up actually opens."""
    q = ("BUILD HANDOFF (build.policy: human). " + "Filler about identifiers. " * 12
         + "As you said earlier, I will not run xcodebuild.")
    assert not shim.is_recap(q)


# --------------------------------------------------- two-part questions
def test_a_two_part_label_gets_both_answers(shim):
    """"CREDENTIALS/ENV" announces two intents, so answer both — that is the
    whole point: a half-answered question comes straight back as a re-ask."""
    q = ("5) CREDENTIALS/ENV — config.yml names APP_TEST_USERNAME / APP_TEST_PASSWORD "
         "as the QA account env vars. Are those exported in the shell I'll run pytest "
         "in (I will not hardcode any value), and is staging the right backend?")
    assert shim.route(q) == ["credentials", "environment"]
    answer = shim.answer_for(q)
    assert "APP_TEST_USERNAME" in answer and "staging" in answer


def test_a_topic_merely_mentioned_does_not_earn_a_second_answer(shim):
    """Volunteering the failure criterion at a review checkpoint reads as the
    reviewer asking for changes. Silence is better than a non-sequitur."""
    q = ("REVIEW CHECKPOINT — 3 passed. Tests: test_login_happy_path, "
         "test_login_wrong_password, test_login_invalid_credentials, and the "
         "negative case for a bad password.")
    assert shim.route(q) == ["approval"]


def test_at_most_two_answers_come_back(shim):
    for entry in json.loads(CORPUS.read_text(encoding="utf-8")):
        assert len(entry["expected"]) <= 2, entry["id"]


# ------------------------------------------------------- no unanswered asks
def test_every_real_question_gets_a_routed_answer(shim):
    """A neutral reply reads as the reviewer dodging and invites a re-ask, so the
    signals have to cover everything the agent actually asked in iteration 3."""
    dodged = [e["id"] for e in json.loads(CORPUS.read_text(encoding="utf-8"))
              if not shim.route(e["question"])]
    assert dodged == []


def test_entry_point_questions_get_a_real_answer(shim):
    """Left neutral before this fix — a shrug on a question the skill requires
    the agent to ask is the reviewer refusing to play their part."""
    q = ("4) ENTRY POINT — AppRouter.presentLogin has exactly two callers: "
         "IntroductionContentViewController.didTapLogin on the cold-start intro "
         "screen, and ProfileViewController.didTapSignIn for a guest. Which should "
         "the test drive?")
    assert shim.route(q) == ["entry_point"]
    assert "intro screen" in shim.answer_for(q)


# ---------------------------------------------------------------- the corpus
CORPUS_CASES = [
    pytest.param(e["question"], e["expected"], id=e["id"])
    for e in json.loads(CORPUS.read_text(encoding="utf-8"))
]


@pytest.mark.parametrize("question, expected", CORPUS_CASES)
def test_routes_every_question_iteration_3_actually_asked(shim, question, expected):
    assert shim.route(question) == expected


# ------------------------------------------------------------------- the CLI
def test_cli_logs_the_question_verbatim_with_the_bucket_it_routed_to(tmp_path):
    """Grading replays questions.jsonl, so the log has to stay machine-readable."""
    env = {"AGENTQA_EVAL_STATE": str(tmp_path), "PATH": "/usr/bin:/bin",
           "AGENTQA_EVAL_REPO": str(tmp_path)}
    question = "3) BLOCKERS — what could stop this test from running end-to-end?"
    proc = subprocess.run([sys.executable, str(SHIM), question],
                          capture_output=True, text=True, env=env)
    assert proc.returncode == 0
    assert question in proc.stdout and "Blockers:" in proc.stdout

    logged = [json.loads(line)
              for line in (tmp_path / "questions.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(logged) == 1
    assert logged[0]["question"] == question          # verbatim, never normalised
    assert logged[0]["buckets"] == ["blockers"]
    calls = (tmp_path / "calls.jsonl").read_text(encoding="utf-8")
    assert '"tool": "ask-user"' in calls


def test_cli_answers_each_question_of_a_batched_round_separately(tmp_path):
    env = {"AGENTQA_EVAL_STATE": str(tmp_path), "PATH": "/usr/bin:/bin",
           "AGENTQA_EVAL_REPO": str(tmp_path)}
    proc = subprocess.run(
        [sys.executable, str(SHIM),
         "1) SUCCESS — when does this test pass?",
         "2) FAILURE — what does a real failure look like?",
         "3) BLOCKERS — what could stop this test?"],
        capture_output=True, text=True, env=env)
    assert proc.returncode == 0
    logged = [json.loads(line)
              for line in (tmp_path / "questions.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [entry["buckets"] for entry in logged] == [["success"], ["failure"], ["blockers"]]


def test_cli_without_arguments_explains_itself(tmp_path):
    env = {"AGENTQA_EVAL_STATE": str(tmp_path), "PATH": "/usr/bin:/bin"}
    proc = subprocess.run([sys.executable, str(SHIM)],
                          capture_output=True, text=True, env=env)
    assert proc.returncode == 2
    assert "usage:" in proc.stderr
