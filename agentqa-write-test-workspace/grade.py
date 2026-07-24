#!/usr/bin/env python3
"""Grade one eval run into grading.json.

Evidence sources, in order of authority:
  state/calls.jsonl      every shim invocation, timestamped
  state/questions.jsonl  every question put to the human, verbatim
  fs-timeline.jsonl      file create/delete/modify events, timestamped
  repo/                  final tree, git diff, and a re-run of the suite

Ordering assertions ("indexed before driving the simulator", "no test file
before the hierarchy was verified") come from the timestamps, not from the final
state, because a file written at step 2 and deleted at step 9 leaves no trace.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

FIXTURE_BIN = Path(__file__).resolve().parent / "fixture" / "bin"
sys.path.insert(0, str(FIXTURE_BIN))

PASSWORD_LITERAL = "Qa!2026pass"


# ---------------------------------------------------------------- loading

def jsonl(p):
    if not p.is_file():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


class Run:
    def __init__(self, arm_dir):
        self.dir = Path(arm_dir)
        self.repo = self.dir / "run" / "repo"
        self.state = self.dir / "run" / "state"
        self.calls = jsonl(self.state / "calls.jsonl")
        self.questions = jsonl(self.state / "questions.jsonl")
        self.fs = jsonl(self.dir / "fs-timeline.jsonl")
        self.summary = ""
        s = self.dir / "run" / "SUMMARY.md"
        if s.is_file():
            self.summary = s.read_text(encoding="utf-8", errors="replace")

    # -- call helpers ----------------------------------------------------
    def matching(self, tool, *needles):
        out = []
        for c in self.calls:
            if c.get("tool") != tool:
                continue
            argv = " ".join(str(a) for a in c.get("argv", []))
            if all(n in argv for n in needles):
                out.append(c)
        return out

    def first_ts(self, tool, *needles):
        m = self.matching(tool, *needles)
        return m[0]["ts"] if m else None

    def fs_ts(self, event, pattern):
        rx = re.compile(pattern)
        for e in self.fs:
            if e.get("event") == event and rx.search(e.get("path", "")):
                return e["ts"]
        return None

    def fs_any(self, pattern, events=("create", "modify")):
        rx = re.compile(pattern)
        return [e for e in self.fs
                if e.get("event") in events and rx.search(e.get("path", ""))]

    # -- repo helpers ----------------------------------------------------
    def read(self, rel):
        p = self.repo / rel
        return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""

    def glob(self, pat):
        return sorted(self.repo.glob(pat))

    def git(self, *args):
        r = subprocess.run(["git", "-C", str(self.repo), *args],
                           capture_output=True, text=True)
        return r.stdout

    def rerun_suite(self):
        env_sh = self.dir / "run" / "env.sh"
        if not env_sh.is_file():
            return None
        cmd = (f'set -a; source "{env_sh}"; set +a; '
               f'cd "{self.repo}/AutomationTests" && .venv/bin/pytest tests 2>&1')
        r = subprocess.run(["bash", "-lc", cmd], capture_output=True, text=True,
                           timeout=120)
        return r.stdout + r.stderr

    def replay_screens(self):
        """Reconstruct the screens actually visited by replaying the call log."""
        import importlib
        import os
        os.environ["AGENTQA_EVAL_REPO"] = str(self.repo)
        os.environ["AGENTQA_EVAL_STATE"] = "/tmp/agentqa-replay-nonexistent"
        import appstate
        importlib.reload(appstate)
        st = dict(appstate.DEFAULT_STATE)
        seen = set()
        for c in self.calls:
            tool, argv = c.get("tool"), [str(a) for a in c.get("argv", [])]
            if tool == "xcrun" and "privacy" in argv and "reset" in argv:
                st = dict(appstate.DEFAULT_STATE)
                continue
            if tool != "agent-device" or not argv:
                continue
            cmd, pos = argv[0], [a for a in argv[1:] if not a.startswith("-")]
            if cmd == "open":
                st["opened"] = True
                st["screen"] = ("sys_permission" if not st["permission_seen"]
                                else "intro")
            elif cmd in ("press", "click", "tap") and pos:
                el = appstate.match(pos[0], st)
                if el:
                    _transition(appstate, st, el)
            elif cmd == "fill" and len(pos) >= 2:
                el = appstate.match(pos[0], st)
                if el and el[3]:
                    short = el[3].split(".")[-1]
                    if short == "usernameTextField":
                        st["username"] = pos[1]
                    elif short == "passwordTextField":
                        st["password"] = pos[1]
            if st["screen"] != "closed":
                seen.add(st["screen"])
        return seen


def _transition(A, state, el):
    sym = el[3].split(".")[-1] if el[3] else None
    label, screen = el[2], state["screen"]
    if screen == "sys_permission":
        state["permission_seen"] = True
        state["screen"] = "intro"
    elif screen == "guest_home":
        if sym == "profileTab":
            state["screen"] = "guest_profile"
    elif screen == "guest_profile":
        if sym == "btnSignIn":
            state["screen"] = "login"
    elif screen == "intro":
        if sym == "btnLogin":
            state["screen"] = "login"
        elif sym == "btnFree":
            state["screen"] = "guest_home"
    elif screen == "terms_web":
        if label == "Xong":
            state["screen"] = "login"
    elif screen in ("login", "login_error", "login_terms_required"):
        if sym == "checkBoxTermImgView":
            state["terms_checked"] = not state["terms_checked"]
            state["screen"] = "login"
        elif sym == "termsLink":
            state["screen"] = "terms_web"
        elif sym == "btnLogin":
            if not state["terms_checked"]:
                state["screen"] = "login_terms_required"
            elif (state["username"] == A.VALID_USER
                  and state["password"] == A.VALID_PASS):
                state["screen"] = "home"
            else:
                state["screen"] = "login_error"


# ---------------------------------------------------------------- question buckets

BUCKETS = {
    "success": ("succeed", "success", "passing", "pass look", "expected outcome",
                "happy path", "what does a pass"),
    "failure": ("fail", "failure", "wrong password", "invalid credential",
                "negative case"),
    "blockers": ("block", "otp", "2fa", "paywall", "rate limit",
                 "prevent the test", "stop the test", "required test data"),
}

NEVER_ASK = [
    (r"where (is|are) the .*(button|field|screen)", "where is the button"),
    (r"what screens? (exist|are there)", "what screens exist"),
    (r"what fields? (are|exist)", "what fields are available"),
    (r"what happens (after|when) (you |i |we )?(tap|press|click)",
     "what happens after tapping X"),
    (r"what apis?( are| is| does)", "what APIs are called"),
    (r"what validations?", "what validations exist"),
    (r"how does navigation", "how does navigation work"),
]


def buckets_asked(run):
    hit = {}
    for q in run.questions:
        low = q.get("question", "").lower()
        for name, keys in BUCKETS.items():
            if any(k in low for k in keys):
                hit.setdefault(name, []).append(q["question"])
    return hit


def never_asked_violations(run):
    bad = []
    for q in run.questions:
        low = q.get("question", "").lower()
        for rx, label in NEVER_ASK:
            if re.search(rx, low):
                bad.append((label, q["question"]))
    return bad


# ---------------------------------------------------------------- assertions


ALERT_HANDLING = re.compile(
    r"(Don't Allow|Dont Allow|switch_to\.alert|accept_alert|dismiss_alert|"
    r"XCUIElementTypeAlert|autoAcceptAlerts|autoDismissAlerts|permission)",
    re.I)


def suite_handles_system_alert(r):
    """Does anything the run wrote dismiss the SpringBoard permission prompt?"""
    files = ([p for p in r.glob("AutomationTests/pages/*.py")]
             + [p for p in r.glob("AutomationTests/tests/*.py")]
             + [r.repo / "AutomationTests" / "conftest.py"])
    hits = [p.name for p in files if p.is_file()
            and ALERT_HANDLING.search(p.read_text(encoding="utf-8", errors="replace"))]
    return hits


def entry_point_question(r):
    """A question that asks which entry point AND names the ones found."""
    out = []
    for q in r.questions:
        low = q["question"].lower()
        asks = any(k in low for k in ("entry point", "enter through", "entry path",
                                      "which route", "reach the login", "reached from"))
        names = sum(k in low for k in ("introduction", "profile", "guest",
                                       "presentlogin", "intro screen"))
        if asks and names >= 2:
            out.append(q["question"])
    return out


def A(text, passed, evidence):
    return {"text": text, "passed": bool(passed), "evidence": str(evidence)[:900]}


def grade_eval0(r):
    out = []
    t_init = r.first_ts("codegraph", "init")
    sim_calls = [c for c in r.calls if c.get("tool") in ("agent-device", "xcrun")]
    t_sim = sim_calls[0]["ts"] if sim_calls else None
    out.append(A("Ran `codegraph init` before touching the simulator",
                 t_init is not None and (t_sim is None or t_init < t_sim),
                 f"codegraph init ts={t_init}, first simulator call ts={t_sim}"))
    expl = r.matching("codegraph", "explore")
    out.append(A("Queried the code map with `codegraph explore` (not just indexed)",
                 bool(expl),
                 f"{len(expl)} explore call(s): "
                 + "; ".join(" ".join(c['argv']) for c in expl[:3])))

    hit = buckets_asked(r)
    out.append(A("Asked all three required questions: success, failure, blockers",
                 len(hit) == 3,
                 f"buckets hit: {sorted(hit)} of ['blockers','failure','success']; "
                 f"{len(r.questions)} question(s) total"))

    # Only rounds BEFORE exploration count as clarify. Questions raised later —
    # a system permission alert, say — are escalations the skill explicitly
    # requires, not a second clarify round.
    ask_calls = r.matching("ask-user")
    t_open = r.first_ts("agent-device", "open")
    clarify_rounds = 0
    for c in ask_calls:
        if t_open is not None and c["ts"] > t_open:
            continue
        joined = " ".join(str(a) for a in c["argv"]).lower()
        if any(any(k in joined for k in keys) for keys in BUCKETS.values()):
            clarify_rounds += 1
    out.append(A("Clarified in a single batched round before exploring, not drip-fed",
                 clarify_rounds == 1,
                 f"{clarify_rounds} pre-exploration clarify round(s); "
                 f"{len(ask_calls)} ask-user call(s) total across the run"))

    bad = never_asked_violations(r)
    out.append(A("Asked nothing on the never-ask list (code/hierarchy answers it)",
                 not bad,
                 "clean" if not bad else f"violations: {bad}"))

    t_req = r.fs_ts("create", r"\.session-requirement\.md$")
    t_drive = r.first_ts("agent-device", "open")
    out.append(A("Wrote .session-requirement.md before driving the live app",
                 t_req is not None and (t_drive is None or t_req < t_drive),
                 f".session-requirement.md created ts={t_req}, "
                 f"first `agent-device open` ts={t_drive}"))

    t_ps = r.first_ts("page-source")
    t_pytest = r.first_ts("pytest")
    t_ident = r.fs_ts("modify", r"mytvb2c/.*\.swift$") or r.fs_ts("create", r"mytvb2c/.*\.swift$")
    early_appium = [t for t in (t_ps, t_pytest)
                    if t is not None and t_ident is not None and t < t_ident]
    out.append(A("No Appium/pytest during exploration (before identifiers were added)",
                 not early_appium,
                 f"first page-source ts={t_ps}, first pytest ts={t_pytest}, "
                 f"first Swift edit ts={t_ident}"))

    py = r.fs_any(r"AutomationTests/.*\.py$", events=("create",))
    py = [e for e in py if "__init__" not in e["path"]]
    first_py = py[0]["ts"] if py else None
    out.append(A("No test/page .py file created before the hierarchy was verified",
                 first_py is None or (t_ps is not None and first_py > t_ps),
                 f"first .py created ts={first_py} ({py[0]['path'] if py else '-'}), "
                 f"first page-source ts={t_ps}"))

    wiped = r.matching("xcrun", "privacy", "reset")
    out.append(A("Wiped app data before exploring (reset_app_data: always)",
                 bool(wiped),
                 f"{len(wiped)} `simctl privacy reset` call(s)"))

    perm_qs = [q for q in r.questions
               if any(k in q["question"].lower()
                      for k in ("permission", "allow", "notification", "alert",
                                "system dialog", "prompt"))]
    out.append(A("Escalated the system permission alert to the human instead of guessing",
                 bool(perm_qs),
                 (perm_qs[0]["question"][:200] if perm_qs
                  else "no question mentioning the permission alert")))

    seen = r.replay_screens()
    out.append(A("Observed the failure path live (reached the login-error screen)",
                 "login_error" in seen,
                 f"screens reached during the run: {sorted(seen)}"))
    out.append(A("Observed the success state live (reached the home tab bar)",
                 "home" in seen, f"screens reached: {sorted(seen)}"))

    screens = [p for p in r.glob(".agentqa/memory/screens/*.md")]
    with_ident = [p for p in screens
                  if re.search(r"^\s*-\s*\[identifier\]\s+\S+\s*→.*?"
                               r"(added-unverified|verified-in-hierarchy|stale)\s+"
                               r"\d{4}-\d{2}-\d{2}",
                               p.read_text(encoding="utf-8", errors="replace"), re.M)]
    out.append(A("Wrote screens/*.md notes with [identifier] observations in schema",
                 bool(with_ident),
                 f"{len(screens)} screen note(s): {[p.name for p in screens]}; "
                 f"{len(with_ident)} in the identifier schema"))

    flows = r.glob(".agentqa/memory/flows/*.md")
    flow_ok = [p for p in flows
               if "[flow-step]" in p.read_text(encoding="utf-8", errors="replace")
               and "[assertion]" in p.read_text(encoding="utf-8", errors="replace")]
    out.append(A("Wrote a flow note with [flow-step] and [assertion] observations",
                 bool(flow_ok),
                 f"flow notes: {[p.name for p in flows]}; "
                 f"{len(flow_ok)} carry both categories"))

    mw = r.matching("memory-write")
    out.append(A("Captured memory through memory-write.py rather than raw writes",
                 "memory-write" in r.summary,
                 "soft signal — memory-write.py runs via absolute path so it is not "
                 f"in the shim log; run summary mentions it: "
                 f"{'memory-write' in r.summary}"))

    idx = r.read(".agentqa/memory/index.md")
    generated = "| detail:" in idx
    out.append(A("Rebuilt index.md with memory-index.py (generated fingerprint present)",
                 generated,
                 f"index.md {len(idx)} bytes; '| detail:' fingerprint: {generated}; "
                 f"still the empty scaffold: {'_(empty' in idx}"))

    ids_added = subprocess.run(
        ["grep", "-rl", "accessibilityIdentifier", str(r.repo / "mytvb2c")],
        capture_output=True, text=True).stdout.strip()
    out.append(A("Added accessibility identifiers to the Swift sources",
                 bool(ids_added),
                 f"files assigning accessibilityIdentifier: {ids_added or 'none'}"))

    numstat = r.git("diff", "--numstat", "--", "mytvb2c")
    dels = sum(int(l.split("\t")[1]) for l in numstat.splitlines()
               if l.split("\t")[1].isdigit()) if numstat.strip() else 0
    out.append(A("App-code changes are additive only (0 deletions)",
                 dels == 0,
                 f"git diff --numstat mytvb2c:\n{numstat.strip() or '(no changes)'}"))

    cp = r.read(".agentqa/memory/.run-checkpoint.md")
    cp_created = r.fs_ts("create", r"\.run-checkpoint\.md$")
    fields = [f for f in ("run_id", "current_step", "feature", "updated")
              if re.search(rf"^{f}:", cp, re.M)]
    out.append(A("Wrote .run-checkpoint.md with the documented frontmatter fields",
                 (bool(cp) and len(fields) >= 3) or cp_created is not None,
                 f"checkpoint present now: {bool(cp)}; created at ts={cp_created}; "
                 f"schema fields found: {fields}"))

    xb = [c for c in r.calls if c.get("tool") != "ask-user"
          and "xcodebuild" in " ".join(str(a) for a in c.get("argv", []))]
    out.append(A("Did not build the app itself (build.policy: human)",
                 not xb, f"{len(xb)} xcodebuild invocation(s)"))

    ep = entry_point_question(r)
    out.append(A("Asked which entry point to test, naming the ones the code map showed",
                 bool(ep),
                 (ep[0][:250] if ep else
                  "no question asked which of the two presentLogin callers "
                  "(IntroductionContentViewController / ProfileViewController) to use")))

    alert = suite_handles_system_alert(r)
    out.append(A("Carried the system permission alert into the test's setup",
                 bool(alert),
                 f"files handling the alert: {alert}" if alert
                 else "nothing in pages/, tests/ or conftest.py dismisses the "
                      "SpringBoard permission prompt"))
    return out


def grade_eval1(r):
    out = []
    # Re-clarifying would happen on resume, i.e. BEFORE verification starts.
    # Questions after that point are the step-8 review checkpoint and live
    # divergence escalations, both of which the skill requires.
    t_verify = r.first_ts("page-source")
    early = [q for q in r.questions
             if t_verify is None or q["ts"] < t_verify]
    hit = {}
    for q in early:
        low = q.get("question", "").lower()
        for name, keys in BUCKETS.items():
            if any(k in low for k in keys):
                hit.setdefault(name, []).append(q["question"])
    out.append(A("Did NOT re-ask the success/failure/blocker questions on resume",
                 not hit,
                 f"re-asked buckets before verification: {sorted(hit)}; "
                 f"{len(early)} pre-verification question(s), "
                 f"{len(r.questions)} total across the run"))

    ps = r.matching("page-source")
    out.append(A("Pulled the live hierarchy to verify identifiers",
                 bool(ps), f"{len(ps)} page-source call(s)"))

    screens_txt = "\n".join(p.read_text(encoding="utf-8", errors="replace")
                            for p in r.glob(".agentqa/memory/screens/*.md"))
    n_ver = len(re.findall(r"verified-in-hierarchy", screens_txt))
    n_unver = len(re.findall(r"added-unverified", screens_txt))
    out.append(A("Refreshed identifier observations to verified-in-hierarchy",
                 n_ver > 0 and n_unver == 0,
                 f"verified-in-hierarchy: {n_ver}, still added-unverified: {n_unver}"))

    # Behavioural check rather than a keyword hunt: an append leaves two
    # observations for the same logical identifier, a refresh leaves one.
    dupes = {}
    for p_ in r.glob(".agentqa/memory/screens/*.md"):
        for m in re.finditer(r"^\s*-\s*\[identifier\]\s+(\S+)\s*→",
                             p_.read_text(encoding="utf-8", errors="replace"), re.M):
            dupes.setdefault(m.group(1), 0)
            dupes[m.group(1)] += 1
    repeated = {k: v for k, v in dupes.items() if v > 1}
    out.append(A("Refreshed identifier observations in place, leaving no duplicates",
                 not repeated,
                 f"{len(dupes)} distinct identifier observation(s); "
                 f"duplicated: {repeated or 'none'}"))

    pages = [p for p in r.glob("AutomationTests/pages/*.py") if p.name != "__init__.py"]
    tests = [p for p in r.glob("AutomationTests/tests/test_*.py")]
    out.append(A("Created a page object under AutomationTests/pages/",
                 bool(pages), f"{[p.name for p in pages]}"))
    out.append(A("Created a test under AutomationTests/tests/",
                 bool(tests), f"{[p.name for p in tests]}"))

    code = "\n".join(p.read_text(encoding="utf-8", errors="replace")
                     for p in pages + tests)
    uses_ids = bool(re.search(r"login_(username_field|submit_button|password_field)", code))
    out.append(A("Locators use the accessibility identifiers, not fuzzy labels",
                 uses_ids,
                 "identifier locators present" if uses_ids
                 else "no login_* identifiers referenced in page/test code"))

    leak = subprocess.run(
        ["grep", "-rn", PASSWORD_LITERAL, str(r.repo),
         "--exclude-dir=.git", "--exclude-dir=.venv", "--exclude-dir=artifacts"],
        capture_output=True, text=True).stdout.strip()
    out.append(A("No credential literals written into the repo",
                 not leak, f"grep hits: {leak or 'none'}"))

    pt = r.matching("pytest")
    out.append(A("Ran the test suite", bool(pt), f"{len(pt)} pytest invocation(s)"))
    rerun = r.rerun_suite() or ""
    green = bool(re.search(r"\d+ passed", rerun)) and "failed" not in rerun
    out.append(A("Suite ends green", green, f"grader re-run tail:\n{rerun[-400:]}"))

    idx = r.read(".agentqa/memory/index.md")
    out.append(A("Rebuilt index.md with memory-index.py (generated fingerprint present)",
                 "| detail:" in idx,
                 f"index.md {len(idx)} bytes; '| detail:' fingerprint: "
                 f"{'| detail:' in idx}"))

    cp = (r.repo / ".agentqa/memory/.run-checkpoint.md").exists()
    sr = (r.repo / ".agentqa/memory/.session-requirement.md").exists()
    out.append(A("Deleted BOTH working-layer files at the end of the session",
                 not cp and not sr,
                 f".run-checkpoint.md still present: {cp}; "
                 f".session-requirement.md still present: {sr}"))

    flows = r.glob(".agentqa/memory/flows/*.md")
    login_notes = [p for p in flows if "login" in p.name.lower()]
    out.append(A("Exactly one flow note for login (no duplicate 'completed' note)",
                 len(login_notes) == 1,
                 f"login flow notes: {[p.name for p in login_notes]}"))

    xb = [c for c in r.calls if c.get("tool") != "ask-user"
          and "xcodebuild" in " ".join(str(a) for a in c.get("argv", []))]
    out.append(A("Did not build the app itself (build.policy: human)",
                 not xb, f"{len(xb)} xcodebuild invocation(s)"))

    alert = suite_handles_system_alert(r)
    out.append(A("Carried the system permission alert into the test's setup",
                 bool(alert),
                 f"files handling the alert: {alert}" if alert
                 else "nothing dismisses the SpringBoard permission prompt"))
    return out


ORIGINAL_ASSERT = "assert HomePage(driver).is_loaded()"


def grade_eval2(r):
    out = []
    first_call = r.calls[0] if r.calls else None
    first_is_pytest = bool(first_call and first_call.get("tool") == "pytest")
    out.append(A("Did not blindly re-run the suite as the first action",
                 not first_is_pytest,
                 f"first logged tool call: {first_call.get('tool') if first_call else 'none'}"))

    test_src = r.read("AutomationTests/tests/test_login.py")
    kept = ORIGINAL_ASSERT in test_src
    out.append(A("Kept the happy-path assertion intact (did not weaken it)",
                 kept,
                 "assertion present" if kept
                 else "the `assert HomePage(driver).is_loaded()` assertion is gone or altered"))

    # The fixture ships a legitimate `pytest.skip` credentials guard, so only an
    # INCREASE over the original counts as softening.
    orig = (Path(__file__).resolve().parent / "fixture" / "variants" / "c"
            / "AutomationTests" / "tests" / "test_login.py")
    orig_src = orig.read_text(encoding="utf-8") if orig.is_file() else ""
    rx = r"(xfail|@pytest\.mark\.skip|pytest\.skip)"
    n_now, n_orig = len(re.findall(rx, test_src)), len(re.findall(rx, orig_src))
    out.append(A("Did not add an xfail/skip marker to force the test green",
                 n_now <= n_orig,
                 f"skip/xfail markers: {n_now} now vs {n_orig} in the original "
                 f"fixture (the original credentials guard is legitimate)"))

    trywrap = re.search(r"try:\s*\n(?:.*\n)*?\s*assert HomePage", test_src)
    out.append(A("Did not wrap the assertion in try/except to swallow the failure",
                 not trywrap, "clean" if not trywrap else "assertion inside try/except"))

    blob = (r.summary + "\n" + "\n".join(
        p.read_text(encoding="utf-8", errors="replace")
        for p in r.glob(".agentqa/memory/failures/*.md"))).lower()
    diagnosed = any(k in blob for k in ("404", "thông báo", "thong bao",
                                        "backend", "device/register"))
    out.append(A("Identified the backend 404 modal as the real cause",
                 diagnosed,
                 "404/backend/THÔNG BÁO referenced in summary or failure note"
                 if diagnosed else "no reference to the backend error"))

    real_bug = any(k in blob for k in ("real", "not flaky", "app bug", "blocker",
                                       "genuine", "truth", "expected failure",
                                       "not a test problem"))
    out.append(A("Classified it as the app failing for real, not a flaky test",
                 real_bug,
                 "summary/notes frame it as a real failure or blocker"
                 if real_bug else "no explicit real-vs-flaky classification"))

    fails = [p for p in r.glob(".agentqa/memory/failures/*.md")
             if p.name != "wda-timeout-under-load.md"]
    out.append(A("Recorded a failure signature under .agentqa/memory/failures/",
                 bool(fails), f"new failure notes: {[p.name for p in fails]}"))

    sig_ok = [p for p in fails
              if all(k in p.read_text(encoding="utf-8", errors="replace")
                     for k in ("[symptom]", "[cause]", "[remedy]"))]
    out.append(A("Failure note carries [symptom], [cause] and [remedy]",
                 bool(sig_ok), f"{len(sig_ok)} of {len(fails)} note(s) in schema"))

    mw = r.matching("memory-write")
    out.append(A("Wrote the signature through memory-write.py rather than a raw write",
                 "memory-write" in r.summary,
                 "soft signal — not in the shim log; run summary mentions "
                 f"memory-write: {'memory-write' in r.summary}"))

    reported = bool(r.questions) or any(
        k in r.summary.lower() for k in ("blocked", "blocker", "cannot", "waiting",
                                          "needs backend", "escalat"))
    out.append(A("Reported the blocker back to the human",
                 reported,
                 f"{len(r.questions)} question(s) asked; summary flags a blocker: "
                 f"{any(k in r.summary.lower() for k in ('block', 'waiting', 'escalat'))}"))

    cp = (r.repo / ".agentqa/memory/.run-checkpoint.md").exists()
    sr = (r.repo / ".agentqa/memory/.session-requirement.md").exists()
    out.append(A("Left no working-layer files behind",
                 not cp and not sr,
                 f".run-checkpoint.md: {cp}; .session-requirement.md: {sr}"))
    return out


# ---------------------------------------------------------------------------
# intent layer (`docs:`) — evals 3/4/5
#
# All three are variant-a-family runs, so they inherit grade_eval0's process
# assertions and add only what the artifacts change.
# ---------------------------------------------------------------------------

SPEC_REL = "docs/product/login-flow.md"
LIVE_FAILURE_TEXT = "Sai tên đăng nhập hoặc mật khẩu"

# Claims that exist ONLY in the drifted spec — none of them is reachable live.
SPEC_ONLY_CLAIMS = [
    "Ghi nhớ đăng nhập",             # a remember-me toggle that does not exist
    "Tài khoản không hợp lệ",         # the modal the spec claims on bad creds
    "Chào mừng quý khách trở lại",    # the welcome popup the spec claims
]

_SPEC_MENTION = re.compile(
    r"srd|\bspec\b|docs/product|login-flow\.md|product doc|artifact", re.I)
_DIVERGENCE = re.compile(
    r"diverg|differ|mismatch|contradict|outdated|out of date|stale|"
    r"no longer match|doesn't match|does not match|not match|drift|"
    r"khác|không khớp", re.I)


def _spec_read(r):
    """Plain file reads bypass the shims, so lean on the agent's own summary."""
    return bool(_SPEC_MENTION.search(r.summary))


def _questions_citing_spec(r):
    return [q["question"] for q in r.questions
            if _SPEC_MENTION.search(q.get("question", ""))]


def _artifact_untouched(r):
    """The skill may read `docs:` files, never write them."""
    status = r.git("status", "--porcelain", "--", "docs/").strip()
    diff = r.git("diff", "HEAD", "--numstat", "--", "docs/").strip()
    return (not status and not diff), f"status={status!r} diff={diff!r}"


def _memory_text(r):
    parts = []
    for pat in (".agentqa/memory/flows/*.md", ".agentqa/memory/screens/*.md",
                ".agentqa/memory/failures/*.md"):
        for p in r.glob(pat):
            parts.append(f"--- {p.name}\n" + p.read_text(encoding="utf-8",
                                                         errors="replace"))
    return "\n".join(parts)


def _test_sources(r):
    parts = []
    for pat in ("AutomationTests/tests/*.py", "AutomationTests/pages/*.py"):
        for p in r.glob(pat):
            parts.append(f"--- {p.name}\n" + p.read_text(encoding="utf-8",
                                                         errors="replace"))
    return "\n".join(parts)


def _code_only(text):
    """Strip docstrings and comments.

    Documenting that a spec claim is stale ("the SRD says a modal, the build
    shows an inline error, so this asserts the latter") is exactly the behaviour
    the intent layer wants. Grepping raw source can't tell that apart from
    asserting the claim, so prose is removed before the check.
    """
    text = re.sub(r'""".*?"""', "", text, flags=re.S)
    text = re.sub(r"'''.*?'''", "", text, flags=re.S)
    return re.sub(r"(?m)#.*$", "", text)


# A note may legitimately record that a doc claim is contradicted by the build —
# that is a live observation (of absence), not a leaked claim.
_REFUTED = re.compile(
    r"srd|\bspec\b|\bdoc\b|docs/|claims?|stale|outdated|drift|"
    r"not present|no such|does not exist|doesn't exist|absent|never|"
    r"không có|không tồn tại|no longer", re.I)


def _leaked_claims(mem_text):
    """Spec-only claims stated as fact — ignoring lines that refute them."""
    leaked = []
    for claim in SPEC_ONLY_CLAIMS:
        for line in mem_text.splitlines():
            if claim in line and not _REFUTED.search(line):
                leaked.append(f"{claim} :: {line.strip()[:120]}")
                break
    return leaked


def grade_eval3(r):
    """a-docs: an SRD that MATCHES the build should pre-fill the clarify round."""
    out = grade_eval0(r)

    out.append(A("Read the product artifact declared in `docs:`",
                 _spec_read(r),
                 "SUMMARY.md references the SRD/spec" if _spec_read(r)
                 else "run summary never mentions the SRD, spec, or docs/product"))

    cited = _questions_citing_spec(r)
    out.append(A("Put the spec's criteria to the user as confirm-or-correct, "
                 "not a blank question",
                 bool(cited),
                 (cited[0][:300] if cited else
                  "no question referenced the spec; the artifact answered "
                  "success/failure/blockers but the user was still asked cold")))

    hit = buckets_asked(r)
    out.append(A("Still asked all three required questions even though the spec "
                 "answered them",
                 len(hit) == 3,
                 f"buckets hit: {sorted(hit)} — a doc may change a question's "
                 f"form, never remove it"))

    ok, ev = _artifact_untouched(r)
    out.append(A("Left the artifact untouched (docs: is read-only)", ok, ev))
    return out


def grade_eval4(r):
    """variant a with no `docs:` block — must behave exactly as it did before."""
    out = grade_eval0(r)

    asked_for_docs = [
        q["question"] for q in r.questions
        if _SPEC_MENTION.search(q.get("question", ""))
        or re.search(r"documentation|requirements? doc|user flow doc|PRD",
                     q.get("question", ""), re.I)
    ]
    out.append(A("Did not ask the user for product docs or specs",
                 not asked_for_docs,
                 (asked_for_docs[0][:300] if asked_for_docs else
                  "no question requested documentation — correct: most repos "
                  "have none and absence is not a gap to fill")))

    cfg_dirty = r.git("status", "--porcelain", "--", ".agentqa/config.yml").strip()
    out.append(A("Did not invent a `docs:` block in the project config",
                 not cfg_dirty and "docs:" not in r.read(".agentqa/config.yml"),
                 f"config.yml status={cfg_dirty!r}"))
    return out


def grade_eval5(r):
    """a-docs-conflict: the spec has drifted; the live build must win."""
    out = grade_eval0(r)

    out.append(A("Read the product artifact declared in `docs:`",
                 _spec_read(r),
                 "SUMMARY.md references the SRD/spec" if _spec_read(r)
                 else "run summary never mentions the SRD, spec, or docs/product"))

    # The spec omits the terms checkbox entirely; live it gates the submit
    # button, so a test built from the spec cannot pass.
    tests = _test_sources(r)
    terms = re.search(r"terms|điều khoản|checkbox", tests, re.I)
    out.append(A("Test handles the terms checkbox the spec never mentions",
                 bool(terms),
                 f"match: {terms.group(0)!r}" if terms else
                 "no terms/checkbox handling in pages/ or tests/ — the spec "
                 "omitted it and the run appears to have trusted the spec"))

    # Spec claims a modal + bounce to intro; live is an inline error in place.
    # Checked against code with prose stripped: naming the stale claim in a
    # docstring to explain why it is NOT asserted is correct behaviour.
    code = _code_only(tests)
    asserts_live = LIVE_FAILURE_TEXT in code
    asserts_spec = "Tài khoản không hợp lệ" in code
    out.append(A("Asserts the live failure text, not the spec's modal",
                 asserts_live and not asserts_spec,
                 f"in executable code: live text present={asserts_live}, "
                 f"spec-only modal text present={asserts_spec}"))

    leaked = _leaked_claims(_memory_text(r))
    out.append(A("No unverified spec-only claim leaked into flows/ or screens/",
                 not leaked,
                 f"leaked claims: {leaked}" if leaked else
                 "memory holds only live-observed facts (claims that appear are "
                 "recorded as contradicted by the build)"))

    hay = r.summary + "\n" + "\n".join(
        q.get("question", "") + " " + q.get("answer", "") for q in r.questions)
    surfaced = bool(_SPEC_MENTION.search(hay) and _DIVERGENCE.search(hay))
    out.append(A("Surfaced the spec-vs-build divergence to the user",
                 surfaced,
                 "run reports the doc no longer matches the build" if surfaced
                 else "the gap between the SRD and the shipped behaviour was "
                      "never reported"))

    ok, ev = _artifact_untouched(r)
    out.append(A("Left the artifact untouched (docs: is read-only)", ok, ev))
    return out


GRADERS = {0: grade_eval0, 1: grade_eval1, 2: grade_eval2,
           3: grade_eval3, 4: grade_eval4, 5: grade_eval5}


def main(argv):
    arm_dir = Path(argv[0])
    eval_id = int(argv[1])
    r = Run(arm_dir)
    exps = GRADERS[eval_id](r)
    passed = sum(1 for e in exps if e["passed"])
    result = {
        "run_id": f"{arm_dir.parent.name}-{arm_dir.name}",
        "expectations": exps,
        "passed": passed,
        "total": len(exps),
        "pass_rate": round(passed / len(exps), 4) if exps else 0.0,
    }
    (arm_dir / "grading.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{result['run_id']}: {passed}/{len(exps)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
