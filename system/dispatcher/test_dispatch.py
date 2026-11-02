"""Tests for the Dispatcher: its snapshot parsing, its plan, its notices and one dry-run pass."""

import base64
import tomllib
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from system.dispatcher import dispatch, github_state, merge_rules, notify, plan
from system.tools import post

ROOT = Path(__file__).resolve().parents[2]
IDENTITY = post.load_identity()
CAPS = tomllib.loads((ROOT / "system" / "caps.toml").read_text())

# These tests check the caps' logic at the sizing's concurrency (2 runs, 1 per role), not the Owner's
# temporary setting in caps.toml for the G1-1 push (#84).
CAPS["concurrency"] = {"max_runs": 2, "max_runs_per_role": 1}
NOW = datetime(2026, 10, 27, 3, 0, tzinfo=timezone.utc)
BOT, SECOND = IDENTITY["reviewer_app"]["bot_login"], IDENTITY["second_login"]
# A protected file SR3 leaves to the Owner (#221), for the tests of what the Owner is asked.
OWNERS = ["blueprint.md"]


def issue(n, *labels, title="t"):
    return {"number": n, "title": title, "labels": set(labels), "body": "", "url": f"u/{n}"}


def pr(n, role="developer", gate="SUCCESS", head="h2", merge_state="BLOCKED", decision="REVIEW_REQUIRED",
       reviews=(), labels=(), protected=False, auto_merge=False, draft=False, resolves=(), files=()):
    return {"number": n, "title": "p", "draft": draft, "head": head, "branch": "b", "merge_state": merge_state,
            "resolves": list(resolves),
            "review_decision": decision, "auto_merge": auto_merge, "author_role": role, "labels": set(labels),
            "files": list(files), "protected": protected, "gate": gate,
            "reviews": [{"login": login, "state": s, "commit": c, "at": None} for login, s, c in reviews]}


def snap(issues=(), prs=(), order=()):
    return {"issues": list(issues), "prs": list(prs), "work_order": list(order)}


class SnapshotParsingTest(unittest.TestCase):
    def test_work_order_rows_in_order_with_parallel_safety(self):
        body = "note\n\n| Order | Item | Parallel-safe | Note |\n| --- | --- | --- | --- |\n| 1 | #23 | yes | a |\n| 2 | #9 | no | |\n"
        self.assertEqual(github_state.work_order(body), [(23, True), (9, False)])

    def test_protected_paths_follow_codeowners(self):
        patterns = github_state.protected_patterns((ROOT / ".github" / "CODEOWNERS").read_text())
        self.assertTrue(github_state.is_protected("system/caps.toml", patterns))
        self.assertTrue(github_state.is_protected("blueprint.md", patterns))
        self.assertTrue(github_state.is_protected(".github/workflows/gate.yml", patterns))
        self.assertFalse(github_state.is_protected("src/app.py", patterns))
        self.assertFalse(github_state.is_protected("design/internal/x.md", patterns))

    def test_pr_author_role_is_trusted_only_from_the_owners_account(self):
        body = "<!-- role:developer run:r -->\nResolves #3"
        self.assertEqual(github_state.author_role("aray4702", body, IDENTITY), "developer")
        self.assertIsNone(github_state.author_role("stranger", body, IDENTITY))
        self.assertIsNone(github_state.author_role("aray4702", "plain", IDENTITY))

    def test_gate_comes_from_github_actions_only(self):
        def node(*suites):
            return {"commits": {"nodes": [{"commit": {"checkSuites": {"nodes": list(suites)}}}]}}
        suite = lambda app, status, conclusion: {"app": {"databaseId": app}, "checkRuns": {"nodes": [{"status": status, "conclusion": conclusion}]}}
        self.assertEqual(github_state.gate_of(node(suite(15368, "COMPLETED", "SUCCESS")), 15368), "SUCCESS")
        self.assertEqual(github_state.gate_of(node(suite(15368, "COMPLETED", "CANCELLED")), 15368), "FAILURE")
        self.assertIsNone(github_state.gate_of(node(suite(15368, "IN_PROGRESS", None)), 15368))
        self.assertIsNone(github_state.gate_of(node(suite(999, "COMPLETED", "SUCCESS")), 15368))

    def test_app_reviews_are_matched_by_the_bot_login_identity_uses(self):
        # GraphQL reports the App's review author as login "aray4702-reviewer-app", __typename "Bot";
        # REST and identity.toml say "aray4702-reviewer-app[bot]". Missing this made every App review invisible.
        node = {"number": 23, "title": "t", "body": "<!-- role:architect run:a -->\nx", "isDraft": False,
                "headRefOid": "h", "headRefName": "b", "mergeStateStatus": "BLOCKED", "reviewDecision": "CHANGES_REQUESTED",
                "author": {"login": "aray4702"}, "autoMergeRequest": None, "files": {"nodes": []},
                "commits": {"nodes": []},
                "reviews": {"nodes": [
                    {"author": {"login": "aray4702-reviewer-app", "__typename": "Bot"}, "state": "CHANGES_REQUESTED", "commit": {"oid": "h"}},
                    {"author": {"login": "sloan3165", "__typename": "User"}, "state": "APPROVED", "commit": {"oid": "h"}},
                ]}}
        p = github_state.pull_request(node, set(), IDENTITY, [])
        self.assertEqual([r["login"] for r in p["reviews"]], [BOT, SECOND])
        self.assertEqual((p["author"], p["author_role"]), ("aray4702", "architect"))
        got = plan.candidates({"issues": [], "prs": [p], "work_order": []}, set(), IDENTITY)
        self.assertEqual([(c[0], c[1], c[3]) for c in got], [("architect", 23, "pr-work")])


class CandidatesTest(unittest.TestCase):
    def test_dispatch_order(self):
        s = snap(
            issues=[issue(1, "type:fix", "sev:1"), issue(2, "type:fix", "needs-decision:architect"), issue(3),
                    issue(4, "type:feature", "state:ready"), issue(11, "record:work-order")],
            prs=[pr(20, gate="FAILURE"), pr(21)],
            order=[(4, False)],
        )
        got = [(role, item, why) for role, item, _, why in plan.candidates(s, set(), IDENTITY)]
        self.assertEqual(got, [
            ("developer", 1, "sev:1"), ("developer", 20, "pr-work"), ("reviewer", 21, "review"),
            ("architect", 2, "decision"), ("coordinator", None, "triage"), ("developer", 4, "work-order"),
        ])

    def test_closing_events_and_plan_reviews(self):
        s = snap(issues=[issue(3), issue(21, "record:goal", "state:review")])
        s["closed"] = [20]
        got = [(r, i, t, w) for r, i, t, w in plan.candidates(s, set(), IDENTITY)]
        self.assertEqual([(r, i, w) for r, i, _, w in got], [("reviewer", 21, "plan-review"), ("coordinator", None, "triage+closed")])
        self.assertEqual(got[1][2], "Triage these issues: #3. Items closed since your last run: #20. "
                                    "Record their goals' progress, close what is done, and chart and schedule what comes next.")

    def test_a_plan_reviews_changes_on_a_goal_issue_start_the_coordinator(self):
        # #30: the Reviewer escalates a plan's changes with needs-decision:coordinator on the goal issue.
        goal = issue(21, "record:goal", "needs-decision:coordinator")
        got = plan.candidates(snap([goal]), set(), IDENTITY)
        self.assertEqual([(r, i, w) for r, i, _, w in got], [("coordinator", 21, "decision")])
        # The Coordinator resolves it and removes the label: nothing on the next pass.
        self.assertEqual(plan.candidates(snap([issue(21, "record:goal")]), set(), IDENTITY), [])

    def test_an_owner_answer_starts_the_role_that_asked(self):
        goal = issue(21, "record:goal", "needs-decision:owner")
        got = plan.candidates(snap([goal]), set(), IDENTITY, answered={21: "coordinator"})
        self.assertEqual([(r, i, w) for r, i, _, w in got], [("coordinator", 21, "answered")])
        self.assertIn("remove needs-decision:owner", got[0][2])
        claimed = issue(21, "record:goal", "needs-decision:owner", "state:claimed")
        self.assertEqual(plan.candidates(snap([claimed]), set(), IDENTITY, answered={21: "coordinator"}), [])

    def test_a_new_goal_in_the_requirements_starts_the_coordinator(self):
        text = ("## 2. Goals\n\n| ID  | Goal | Outcome | Deadline |\n| --- | --- | --- | --- |\n"
                "| G0  | the starting point (§0) | its done-check |  |\n| ~~S1~~ | ~~seed~~ | ~~x~~ | none |\n"
                "| G1  | Transcribe calls | WER < 10 % | 2026-12-01 |\n| G2  |  |  |  |\n\n## 3. Use cases\n| U1 | x |\n")
        self.assertEqual(github_state.requirement_goals(text), ["G1"])
        s = snap()
        s["new_goals"] = ["G1"]
        got = plan.candidates(s, set(), IDENTITY)
        self.assertEqual([(r, i, w) for r, i, _, w in got], [("coordinator", None, "new-goal")])
        self.assertIn("New goals in the requirements without a goal issue: G1.", got[0][2])

    def test_the_snapshot_offers_only_goals_on_main_without_a_goal_issue(self):
        gh = FakeGitHub()
        gh.requirements += "| G1 | Transcribe calls | WER < 10 % | 2026-12-01 |\n"
        self.assertEqual(github_state.snapshot(gh, IDENTITY)["new_goals"], ["G1"])
        self.assertEqual(github_state.snapshot(FakeGitHub(), IDENTITY)["new_goals"], [])

    def test_a_red_gate_shared_with_main_does_not_restart_the_author(self):
        # #336: while main's gate was red, the Dispatcher restarted #304's author about every two minutes, for nothing.
        gh = FakeGitHub()
        gh.graphql = lambda q, **v: {"repository": {"pullRequests": {"nodes": []}, "defaultBranchRef": {"target": {
            "checkSuites": {"nodes": [{"app": {"databaseId": IDENTITY["gate_app_id"]},
                                       "checkRuns": {"nodes": [{"status": "COMPLETED", "conclusion": "FAILURE"}]}}]}}}}}
        self.assertEqual(github_state.snapshot(gh, IDENTITY)["main_gate"], "FAILURE")
        self.assertIsNone(github_state.snapshot(FakeGitHub(), IDENTITY)["main_gate"])
        prs = [pr(20, gate="FAILURE"), pr(22, gate="FAILURE", merge_state="DIRTY")]
        red = dict(snap(prs=prs), main_gate="FAILURE")
        self.assertEqual([(r, i, t) for r, i, t, _ in plan.candidates(red, set(), IDENTITY)],
                         [("developer", 22, "PR #22 needs work: it conflicts with main.")])
        green = dict(snap(prs=prs), main_gate="SUCCESS")
        self.assertEqual([(i, w) for _, i, _, w in plan.candidates(green, set(), IDENTITY)], [(20, "pr-work"), (22, "pr-work")])
        # The PR that fixes main is red for its own reason: it is still offered, or main stays red with no run on it.
        fix = dict(snap(issues=[issue(5, "type:fix", "sev:1")], prs=[pr(24, gate="FAILURE", resolves=[5])]), main_gate="FAILURE")
        self.assertEqual([(r, i, t) for r, i, t, _ in plan.candidates(fix, set(), IDENTITY)],
                         [("developer", 24, "PR #24 needs work: its gate is red.")])

    def test_claimed_running_and_records_are_never_offered(self):
        s = snap(issues=[issue(1, "type:fix", "sev:1", "state:claimed"), issue(2, "type:fix", "sev:1"), issue(13, "record:decision-log")])
        self.assertEqual(plan.candidates(s, {2}, IDENTITY), [])

    def test_a_reviewed_head_is_not_reviewed_again_until_it_changes(self):
        s = snap(prs=[pr(5, reviews=[(BOT, "APPROVED", "h2")])])
        self.assertEqual(plan.candidates(s, set(), IDENTITY), [])
        s = snap(prs=[pr(5, reviews=[(BOT, "APPROVED", "h1")])])
        self.assertEqual([c[3] for c in plan.candidates(s, set(), IDENTITY)], ["review"])
        self.assertEqual(plan.candidates(s, set(), IDENTITY, skip_review={5}), [])

    def test_a_pr_held_for_a_decision_starts_the_decider_not_the_reviewer(self):
        # #192: the Reviewer escalated #188 to the Architect; the review candidate came first on the same
        # item, so each tick restarted the Reviewer and the Architect never started.
        held = snap(prs=[pr(5, labels=["needs-decision:architect"])])
        got = plan.choose(held, [], CAPS, IDENTITY, NOW)[0]
        self.assertEqual([(r, i, w) for r, i, _, w in got], [("architect", 5, "decision")])
        self.assertEqual(plan.candidates(snap(prs=[pr(5, labels=["needs-decision:owner"])]), set(), IDENTITY), [])
        # The Architect answers and removes the label: the Reviewer picks it up again.
        self.assertEqual([c[3] for c in plan.candidates(snap(prs=[pr(5)]), set(), IDENTITY)], ["review"])

    def test_goal_work_goes_ahead_of_the_systems_own_upkeep(self):
        # #229: at 18:20 PT on 10-28 the builder took SR3 approvals of system PRs #199 and #201 before G1's #217.
        sr3 = lambda n, role: pr(n, role=role, protected=True, labels=["needs-decision:builder"], reviews=[(BOT, "APPROVED", "h2")])
        s = snap(prs=[sr3(199, "builder"), sr3(201, "builder"), sr3(217, "developer")])
        self.assertEqual([c[1] for c in plan.candidates(s, set(), IDENTITY)], [217, 199, 201], "the order within each group stays")
        self.assertEqual([(r, i) for r, i, _, _ in plan.choose(s, [], CAPS, IDENTITY, NOW)[0]], [("builder", 217)])
        # 14:24 PT: the Architect's decision on G1's #188 waited behind builder rework of system PRs.
        rework = pr(193, role="builder", gate="FAILURE")
        decision = pr(188, labels=["needs-decision:architect"], reviews=[(BOT, "APPROVED", "h2")])
        self.assertEqual([(c[0], c[1]) for c in plan.candidates(snap(prs=[rework, decision]), set(), IDENTITY)],
                         [("architect", 188), ("builder", 193)])
        # A system item's own decision waits behind a goal item's too.
        items = [issue(5, "type:system", "needs-decision:builder"), issue(6, "type:feature", "needs-decision:architect")]
        self.assertEqual([c[1] for c in plan.candidates(snap(issues=items), set(), IDENTITY)], [6, 5])

    def test_severe_system_work_and_the_daily_run_keep_their_place(self):
        # A sev:2 system fix isn't starved by goal work (#196 fixed the sev:2 #192).
        fix = pr(196, role="builder", gate="FAILURE", resolves=[192])
        decision = pr(188, labels=["needs-decision:architect"], reviews=[(BOT, "APPROVED", "h2")])
        s = snap(issues=[issue(192, "type:system", "sev:2")], prs=[fix, decision])
        self.assertEqual([c[1] for c in plan.candidates(s, set(), IDENTITY)], [196, 188])
        s = snap(issues=[issue(192, "type:system", "sev:2", "needs-decision:builder"), issue(6, "type:feature", "needs-decision:architect")])
        self.assertEqual([c[1] for c in plan.candidates(s, set(), IDENTITY)], [192, 6])
        # The builder's overdue daily run stays ahead of triage (#186).
        s = snap(issues=[issue(2, "state:triage")])
        self.assertEqual([c[3] for c in plan.candidates(s, set(), IDENTITY, daily="Daily run")], ["daily-catch-up", "triage"])

    def test_an_answered_review_goes_back_to_the_reviewer_not_the_author(self):
        # #257: on #250 the Developer answered a requested change by comment, with the head unchanged, and was
        # restarted every poll (7 runs) while the Reviewer never was.
        at = lambda m: (NOW + timedelta(minutes=m)).isoformat()
        p = pr(250, reviews=[(BOT, "CHANGES_REQUESTED", "h2")])
        p["reviews"][0]["at"] = at(0).replace("+00:00", "Z")
        started = lambda runs: [(r, w) for r, i, _, w in plan.choose(snap(prs=[p]), runs, CAPS, IDENTITY, NOW + timedelta(minutes=30))[0] if i == 250]
        self.assertEqual(started([]), [("developer", "pr-work")], "not answered yet: the author works on it")
        before = [{"event": "start", "run_id": "d-0", "role": "developer", "item": 250, "at": at(-5)},
                  {"event": "end", "run_id": "d-0", "role": "developer", "item": 250, "at": at(3)}]
        self.assertEqual(started(before), [("developer", "pr-work")], "a run that started before the review didn't see it")
        answered = [{"event": "start", "run_id": "d-1", "role": "developer", "item": 250, "at": at(10)},
                    {"event": "end", "run_id": "d-1", "role": "developer", "item": 250, "at": at(12)}]
        self.assertEqual(started(answered), [("reviewer", "review")], "answered: the Reviewer reads the answer")
        running = [{"event": "start", "run_id": "d-2", "role": "developer", "item": 250, "at": at(10)}]
        self.assertEqual(started(running), [], "still working on it: nothing else starts on the PR")
        p["reviews"].append({"login": BOT, "state": "CHANGES_REQUESTED", "commit": "h2", "at": at(20).replace("+00:00", "Z")})
        self.assertEqual(started(answered), [("developer", "pr-work")], "the Reviewer asked again: back to the author")

    def test_changes_requested_on_the_head_sends_it_back_to_its_author(self):
        s = snap(prs=[pr(5, role="builder", reviews=[(BOT, "CHANGES_REQUESTED", "h2")])])
        self.assertEqual([(c[0], c[3]) for c in plan.candidates(s, set(), IDENTITY)], [("builder", "pr-work")])

    def test_owner_prs_and_drafts_are_left_alone(self):
        s = snap(prs=[pr(5, role=None, gate="FAILURE"), pr(6, draft=True, gate="FAILURE")])
        self.assertEqual(plan.candidates(s, set(), IDENTITY), [])

    def test_an_item_whose_pr_is_open_is_in_review_not_dispatched_again(self):
        items = [issue(20, "type:definition", "state:ready"), issue(30, "type:fix", "state:ready")]
        prs = [pr(23, role="architect", resolves=[20], reviews=[(BOT, "APPROVED", "h2")])]
        got = plan.candidates(snap(items, prs, order=[(20, True), (30, False)]), set(), IDENTITY)
        self.assertEqual(got, [], "#20 is in review, and while it is, only parallel-safe items may start")
        got = plan.candidates(snap(items, prs, order=[(20, True), (30, True)]), set(), IDENTITY)
        self.assertEqual([c[1] for c in got], [30])

    def test_resolves_is_read_from_the_pr_body(self):
        node_body = "<!-- role:architect run:a -->\nResolves #20. Also fixes #7; closes #7."
        self.assertEqual(sorted({int(n) for n in github_state.RESOLVES.findall(node_body)}), [7, 20])

    def test_only_parallel_safe_items_start_while_one_is_busy(self):
        items = [issue(4, "type:fix", "state:ready", "state:claimed"), issue(5, "type:fix", "state:ready"),
                 issue(6, "type:fix", "state:ready")]
        got = plan.candidates(snap(items, order=[(4, False), (5, False), (6, True)]), set(), IDENTITY)
        self.assertEqual([c[1] for c in got], [6])
        free = [issue(5, "type:fix", "state:ready"), issue(6, "type:definition", "state:ready")]
        got = plan.candidates(snap(free, order=[(5, False), (6, False)]), set(), IDENTITY)
        self.assertEqual([c[1] for c in got], [5])


class ChooseTest(unittest.TestCase):
    def test_caps_hold_the_rest(self):
        s = snap(issues=[issue(1, "type:fix", "sev:1"), issue(2, "type:fix", "sev:1"), issue(3)], prs=[pr(21)])
        starts, skipped = plan.choose(s, [], CAPS, IDENTITY, NOW)
        self.assertEqual([(r, i) for r, i, _, _ in starts], [("developer", 1), ("reviewer", 21)])
        self.assertEqual([(r, i) for r, i, _, _ in skipped], [("developer", 2), ("coordinator", None)])


class DailyCatchUpTest(unittest.TestCase):
    """#186: the 08:00 builder job is refused while another builder run is active; the poll starts it later."""
    SCHEDULE = tomllib.loads((ROOT / "system" / "runner.toml").read_text())["schedules"]["builder-daily"]
    TASK = SCHEDULE["command"][-1]

    def at(self, hour, minute=0):  # PT, 2026-10-28 (PDT, UTC-7)
        return datetime(2026, 10, 28, hour + 7, minute, tzinfo=timezone.utc)

    def start(self, role, hour, task, run_id="r"):
        return {"event": "start", "run_id": run_id, "role": role, "item": None, "at": self.at(hour).isoformat(), "task": task}

    def test_due_after_the_grace_until_it_starts_today(self):
        zone = IDENTITY["time_zone"]
        self.assertIsNone(plan.daily_due(self.SCHEDULE, [], self.at(8, 29), zone), "the launchd job goes first")
        self.assertEqual(plan.daily_due(self.SCHEDULE, [], self.at(8, 30), zone), self.TASK)
        yesterday = {**self.start("builder", 9, self.TASK), "at": (self.at(9) - timedelta(days=1)).isoformat()}
        self.assertEqual(plan.daily_due(self.SCHEDULE, [yesterday], self.at(14), zone), self.TASK)
        other = self.start("builder", 7, "Item #186 needs your decision (needs-decision:builder).")
        self.assertEqual(plan.daily_due(self.SCHEDULE, [other], self.at(14), zone), self.TASK)
        self.assertIsNone(plan.daily_due(self.SCHEDULE, [self.start("builder", 8, self.TASK)], self.at(14), zone))
        self.assertIsNone(plan.daily_due({**self.SCHEDULE, "enabled": False}, [], self.at(14), zone))
        self.assertIsNone(plan.daily_due(None, [], self.at(14), zone))

    def test_held_while_a_builder_run_is_active_then_started(self):
        busy = [self.start("builder", 7, "Item #186 needs your decision (needs-decision:builder).", "b1")]
        starts, skipped = plan.choose(snap(), busy, CAPS, IDENTITY, self.at(9), daily_schedule=self.SCHEDULE)
        self.assertEqual(starts, [])
        self.assertEqual([(r, i, w) for r, i, w, _ in skipped], [("builder", None, "daily-catch-up")])
        done = busy + [{"event": "end", "run_id": "b1", "role": "builder", "item": None, "at": self.at(9).isoformat()}]
        starts, _ = plan.choose(snap(), done, CAPS, IDENTITY, self.at(9, 2), daily_schedule=self.SCHEDULE)
        self.assertEqual(starts, [("builder", None, self.TASK, "daily-catch-up")])
        self.assertTrue(self.TASK.startswith(dispatch.audit.BUILDER_DAILY), "the audit must count the catch-up as a daily run")


class MergePlanTest(unittest.TestCase):
    def test_one_pr_at_a_time_refreshing_then_merging(self):
        app = [(BOT, "APPROVED", "h2")]
        s = snap(prs=[pr(8, merge_state="BEHIND", decision="APPROVED", reviews=app), pr(9, merge_state="CLEAN", decision="APPROVED", reviews=app)])
        self.assertEqual(merge_rules.merge_plan(s, IDENTITY), [("refresh", 8, "behind main")])
        s = snap(prs=[pr(9, merge_state="CLEAN", decision="APPROVED", reviews=app)])
        self.assertEqual(merge_rules.merge_plan(s, IDENTITY), [("auto-merge", 9, "h2")])
        s = snap(prs=[pr(9, merge_state="CLEAN", decision="APPROVED", protected=True, files=OWNERS, reviews=app)])
        self.assertEqual(merge_rules.merge_plan(s, IDENTITY), [("ask-owner-to-approve", 9, "h2")], "protected, no Owner approval yet (#127)")
        s = snap(prs=[pr(9, merge_state="CLEAN", decision="APPROVED", protected=True, files=["system/standing-rules.md"],
                         reviews=app + [(SECOND, "APPROVED", "h2")])])
        self.assertEqual(merge_rules.merge_plan(s, IDENTITY), [("ask-owner-to-merge", 9, "h2")], "both current, but SR1 leaves it to the Owner")
        s = snap(prs=[pr(7, merge_state="CLEAN", decision="APPROVED", auto_merge=True, reviews=app),
                      pr(9, merge_state="CLEAN", decision="APPROVED", reviews=app)])
        self.assertEqual(merge_rules.merge_plan(s, IDENTITY), [])
        s = snap(prs=[pr(9, merge_state="CLEAN", decision="APPROVED")])
        self.assertEqual(merge_rules.merge_plan(s, IDENTITY), [], "GitHub's APPROVED alone isn't enough: the Reviewer App's must be current (#118)")

    def test_a_protected_pr_is_refreshed_before_the_owner_is_asked_once(self):
        # Behind main and waiting only on the Owner: refresh first, ask nothing yet.
        s = snap(prs=[pr(23, role="architect", protected=True, files=OWNERS, merge_state="BEHIND", reviews=[(BOT, "APPROVED", "h1")], head="h1")])
        self.assertEqual(merge_rules.merge_plan(s, IDENTITY), [("refresh", 23, "behind main")])
        # Refreshed: the App's approval is on the old head, so renew it, and still don't ask the Owner.
        s = snap(prs=[pr(23, role="architect", protected=True, files=OWNERS, merge_state="BLOCKED", reviews=[(BOT, "APPROVED", "h1")], head="h2")])
        self.assertEqual(merge_rules.merge_plan(s, IDENTITY), [("renew", 23, "h1")])
        # Renewed on the new head and up to date: now ask the Owner, once.
        s = snap(prs=[pr(23, role="architect", protected=True, files=OWNERS, merge_state="BLOCKED", reviews=[(BOT, "APPROVED", "h2")], head="h2")])
        self.assertEqual(merge_rules.merge_plan(s, IDENTITY), [("ask-owner-to-approve", 23, "h2")])
        # The Owner approved the same head: SR1 merges it (#116).
        s = snap(prs=[pr(23, role="architect", protected=True, merge_state="CLEAN", decision="APPROVED",
                         reviews=[(BOT, "APPROVED", "h2"), (SECOND, "APPROVED", "h2")], head="h2")])
        self.assertEqual(merge_rules.merge_plan(s, IDENTITY), [("auto-merge", 23, "h2")])

    def test_sr1_merges_a_protected_pr_only_with_both_approvals_on_its_head(self):
        both = [(BOT, "APPROVED", "h2"), (SECOND, "APPROVED", "h2")]
        ready = lambda **kw: snap(prs=[pr(40, protected=True, merge_state="CLEAN", decision="APPROVED", **kw)])
        self.assertEqual(merge_rules.merge_plan(ready(reviews=both), IDENTITY), [("auto-merge", 40, "h2")])
        owner_only = [(SECOND, "APPROVED", "h2")]
        self.assertEqual(merge_rules.merge_plan(ready(reviews=owner_only), IDENTITY), [],
                         "the Owner approved before the Reviewer: nothing merges, and nothing is asked, until the Reviewer approves")
        asked_again = [(BOT, "APPROVED", "h2"), (BOT, "CHANGES_REQUESTED", "h2"), (SECOND, "APPROVED", "h2")]
        self.assertEqual(merge_rules.merge_plan(ready(reviews=asked_again), IDENTITY), [], "the latest review counts")
        old_head = [(BOT, "APPROVED", "h1"), (SECOND, "APPROVED", "h2")]
        self.assertNotIn(("auto-merge", 40, "h2"), merge_rules.merge_plan(ready(reviews=old_head), IDENTITY))
        rules = ready(reviews=both)
        rules["prs"][0]["files"] = ["system/standing-rules.md"]
        self.assertEqual(merge_rules.merge_plan(rules, IDENTITY), [("ask-owner-to-merge", 40, "h2")], "SR1 never merges a change to itself")
        rules["prs"][0]["files"] = ["system/dispatcher/merge_rules.py"]
        self.assertEqual(merge_rules.merge_plan(rules, IDENTITY), [("ask-owner-to-merge", 40, "h2")])
        rules["prs"][0]["files"] = ["system/dispatcher/plan.py"]
        self.assertEqual(merge_rules.merge_plan(rules, IDENTITY), [("auto-merge", 40, "h2")],
                         "the dispatch order is an ordinary protected file now: SR1 covers it (#150)")

    def test_a_conflict_free_refresh_keeps_both_approvals_and_a_real_push_does_not(self):
        # GitHub no longer dismisses stale approvals; the Dispatcher marks those followed only by merges (#118).
        old = [(BOT, "APPROVED", "h1"), (SECOND, "APPROVED", "h1")]
        refreshed = pr(50, protected=True, merge_state="CLEAN", decision="APPROVED", reviews=old)
        refreshed["fresh"] = {BOT: True, SECOND: True}
        self.assertEqual(merge_rules.merge_plan(snap(prs=[refreshed]), IDENTITY), [("auto-merge", 50, "h2")], "SR1, no re-approval")
        pushed = pr(50, protected=True, merge_state="CLEAN", decision="APPROVED", reviews=old)
        pushed["fresh"] = {BOT: False, SECOND: False}
        acts = merge_rules.merge_plan(snap(prs=[pushed]), IDENTITY)
        self.assertNotIn("auto-merge", [a for a, *_ in acts], "real changes after the approvals: no merge")
        unprotected = pr(51, merge_state="CLEAN", decision="APPROVED", reviews=[(BOT, "APPROVED", "h1")])
        unprotected["fresh"] = {BOT: False}
        self.assertEqual(merge_rules.merge_plan(snap(prs=[unprotected]), IDENTITY), [], "unprotected too: the Reviewer must see the new code")
        unprotected["fresh"] = {BOT: True}
        self.assertEqual(merge_rules.merge_plan(snap(prs=[unprotected]), IDENTITY), [("auto-merge", 51, "h2")])

    def test_an_owner_held_pr_goes_behind_one_sr1_can_merge_and_is_asked_to_reapprove(self):
        # #113 waited on the Owner's re-approval and held #115, which SR1 could merge (#127).
        held = pr(113, protected=True, files=OWNERS, merge_state="CLEAN", decision="APPROVED", reviews=[(BOT, "APPROVED", "h2"), (SECOND, "APPROVED", "h1")])
        held["fresh"] = {SECOND: False}
        ready = pr(115, protected=True, merge_state="CLEAN", decision="APPROVED", reviews=[(BOT, "APPROVED", "h2"), (SECOND, "APPROVED", "h2")])
        acts = merge_rules.merge_plan(snap(prs=[held, ready]), IDENTITY)
        self.assertEqual(acts, [("auto-merge", 115, "h2"), ("ask-owner-to-reapprove", 113, "h2")])
        acts = merge_rules.merge_plan(snap(prs=[held]), IDENTITY)
        self.assertEqual(acts, [("ask-owner-to-reapprove", 113, "h2")], "re-approve, never merge, while the approval isn't current")

    def test_no_new_review_while_the_reviewers_approval_still_covers_the_pr(self):
        refreshed = pr(60, reviews=[(BOT, "APPROVED", "h1")])
        refreshed["fresh"] = {BOT: True}
        self.assertNotIn("reviewer", [c[0] for c in plan.candidates(snap(prs=[refreshed]), set(), IDENTITY)])
        refreshed["fresh"] = {BOT: False}
        self.assertIn("reviewer", [c[0] for c in plan.candidates(snap(prs=[refreshed]), set(), IDENTITY)])

    def test_same_changes_compares_the_prs_own_diff_not_its_commits(self):
        def gh_for(files_by_ref):
            gh = mock.Mock(repo="o/r")
            gh.api.side_effect = lambda method, path, body=None, paginate=False: {"files": files_by_ref[path.rsplit("...", 1)[1]]}
            return gh

        def patch(text):
            return [{"filename": "a.py", "status": "modified", "patch": text}]
        gh = gh_for({
            "A": patch("@@ -1,4 +1,4 @@ def f():\n ctx\n-old\n+new\n+    return True\n     check()"),
            "B": patch("@@ -9,4 +9,4 @@ def f():\n ctx\n-old\n+new\n+    return True\n     check()"),
            "C": patch("@@ -1,4 +1,4 @@ def f():\n ctx\n-old\n+newer\n+    return True\n     check()"),
            "M": patch("@@ -1,4 +1,4 @@ def f():\n ctx\n-old\n+new\n     check()\n+    return True"),
            "S": patch("@@ -1,4 +1,4 @@ def f():\n ctx\n-old\n+    return True\n+new\n     check()"),
            "X": patch("@@ -1,4 +1,4 @@ def f():\n other ctx\n-old\n+new\n+    return True\n     check()"),
        })
        self.assertTrue(merge_rules.same_changes(gh, "A", "B"), "main added lines above: the hunk only shifted")
        self.assertFalse(merge_rules.same_changes(gh, "A", "C"), "a changed line")
        self.assertFalse(merge_rules.same_changes(gh, "A", "M"), "a line moved below its context")
        self.assertFalse(merge_rules.same_changes(gh, "A", "S"), "two added lines swapped")
        self.assertFalse(merge_rules.same_changes(gh, "A", "X"), "main edited the context: ask again, the safe way")
        binary = [{"filename": "m.bin", "status": "modified", "sha": "s1"}]
        gh = gh_for({"D": binary, "E": binary})
        self.assertTrue(merge_rules.same_changes(gh, "D", "E"))
        self.assertFalse(merge_rules.same_changes(gh_for({"D": binary, "F": [dict(binary[0], sha="s2")]}), "D", "F"))

    def test_a_commit_that_shares_no_history_with_main_is_never_fresh_and_stops_nothing(self):
        # After main's history is rewritten, GitHub's compare answers 404 for a PR still on the old history (#635).
        def gh_for(unrelated, error="gh: No common ancestor between main and {ref}. (HTTP 404)"):
            gh = mock.Mock(repo="o/r")

            def api(method, path, body=None, paginate=False):
                ref = path.rsplit("...", 1)[1]
                if ref in unrelated:
                    raise SystemExit(f"gh api GET {path} failed: {error.format(ref=ref)}")
                return {"files": [{"filename": "a.py", "status": "modified", "patch": "@@ -1 +1 @@\n-a\n+b"}]}
            gh.api.side_effect = api
            return gh
        for unrelated in ({"h1"}, {"h2"}, {"h1", "h2"}):
            self.assertFalse(merge_rules.same_changes(gh_for(unrelated), "h1", "h2"), unrelated)
            old = pr(70, protected=True, reviews=[(BOT, "APPROVED", "h1"), (SECOND, "APPROVED", "h1")])
            merge_rules.annotate(gh_for(unrelated), snap(prs=[old]), [], IDENTITY, post.MARKER)
            self.assertEqual(old["fresh"], {BOT: False, SECOND: False}, unrelated)
            self.assertNotIn("same_lines", old, "no SR2 sign-off can carry the approval")
        self.assertTrue(merge_rules.same_changes(gh_for(set()), "h1", "h2"))
        with self.assertRaises(SystemExit, msg="any other error still stops the pass"):
            merge_rules.same_changes(gh_for({"h1"}, error="HTTP 502"), "h1", "h2")

    def test_auto_merge_is_turned_off_when_the_approvals_stop_covering_the_pr(self):
        stale = pr(52, merge_state="CLEAN", decision="APPROVED", auto_merge=True, reviews=[(BOT, "APPROVED", "h1")])
        stale["fresh"] = {BOT: False}
        self.assertEqual(merge_rules.merge_plan(snap(prs=[stale]), IDENTITY), [("cancel-auto-merge", 52, "h2")])
        stale["fresh"] = {BOT: True}
        self.assertEqual(merge_rules.merge_plan(snap(prs=[stale]), IDENTITY), [], "still covered: leave it to GitHub")

    def test_the_owner_is_not_asked_while_github_is_still_working_out_the_merge_state(self):
        # Right after main moves, GitHub reports mergeStateStatus UNKNOWN; #34 was really 12 commits behind.
        s = snap(prs=[pr(34, protected=True, files=OWNERS, merge_state="UNKNOWN", reviews=[(BOT, "APPROVED", "h2")])])
        self.assertEqual(merge_rules.merge_plan(s, IDENTITY), [])
        s = snap(prs=[pr(34, protected=True, files=OWNERS, merge_state="BLOCKED", reviews=[(BOT, "APPROVED", "h2")])])
        self.assertEqual(merge_rules.merge_plan(s, IDENTITY), [("ask-owner-to-approve", 34, "h2")])

    def test_renewals_and_owner_approvals(self):
        s = snap(prs=[pr(9, reviews=[(BOT, "APPROVED", "h1")])])
        self.assertEqual(merge_rules.merge_plan(s, IDENTITY), [("renew", 9, "h1")])
        s = snap(prs=[pr(9, protected=True, files=OWNERS, reviews=[(BOT, "APPROVED", "h2")])])
        self.assertEqual(merge_rules.merge_plan(s, IDENTITY), [("ask-owner-to-approve", 9, "h2")])
        s = snap(prs=[pr(9, protected=True, files=OWNERS, reviews=[(BOT, "APPROVED", "h1"), (SECOND, "APPROVED", "h1")])])
        self.assertEqual(merge_rules.merge_plan(s, IDENTITY), [("renew", 9, "h1"), ("ask-owner-to-reapprove", 9, "h2")])


class SR2Test(unittest.TestCase):
    """#150: a refreshed PR whose own lines are unchanged goes to the Coordinator, not straight back to the Owner."""
    A, H = "a" * 40, "c" * 40

    def refreshed(self, n=113, labels=(), files=OWNERS, merge_state="BLOCKED", same_lines=True, sign_off=None, fresh_sign_off=None,
                  role="developer"):
        p = pr(n, role=role, protected=True, merge_state=merge_state, decision="APPROVED", head=self.H, labels=labels, files=files,
               reviews=[(BOT, "APPROVED", self.H), (SECOND, "APPROVED", self.A)])
        p["fresh"], p["same_lines"], p["sign_off"] = {SECOND: False}, same_lines, sign_off
        if fresh_sign_off is not None:
            p["fresh"]["sign-off"] = fresh_sign_off
        return p

    def test_the_coordinator_is_asked_once_instead_of_the_owner(self):
        ask = [("ask-coordinator-to-sign-off", 113, self.A)]
        self.assertEqual(merge_rules.merge_plan(snap(prs=[self.refreshed()]), IDENTITY), ask)
        held, ready = self.refreshed(merge_state="BEHIND"), pr(115, merge_state="BEHIND", decision="APPROVED", reviews=[(BOT, "APPROVED", "h2")])
        self.assertEqual(merge_rules.merge_plan(snap(prs=[held, ready]), IDENTITY), [("refresh", 115, "behind main")] + ask,
                         "behind main and at the back of the queue: asked anyway, so it isn't stuck there (#113)")
        for level in ("coordinator", "builder", "owner"):
            self.assertEqual(merge_rules.merge_plan(snap(prs=[self.refreshed(labels=[f"needs-decision:{level}"])]), IDENTITY), [],
                             f"already with the {level}")

    def test_changed_own_lines_go_to_the_builder_unless_it_wrote_the_pr(self):
        self.assertEqual(merge_rules.merge_plan(snap(prs=[self.refreshed(same_lines=False)]), IDENTITY),
                         [("ask-builder-to-sign-off", 113, self.A)])
        self.assertEqual(merge_rules.merge_plan(snap(prs=[self.refreshed(same_lines=False, files=OWNERS + ["system/dispatcher/plan.py"])]), IDENTITY),
                         [("ask-builder-to-sign-off", 113, self.A)], "a change to the dispatch order too (#150)")
        self.assertEqual(merge_rules.merge_plan(snap(prs=[self.refreshed(same_lines=False, files=["system/dispatcher/plan.py"])]), IDENTITY),
                         [("ask-builder-to-approve", 113, self.H)], "a PR SR3 covers goes to SR3 instead (#221)")
        self.assertEqual(merge_rules.merge_plan(snap(prs=[self.refreshed(same_lines=False, role="builder")]), IDENTITY),
                         [("ask-owner-to-reapprove", 113, self.H)], "the builder never judges its own changes for the Owner")
        self.assertEqual(merge_rules.merge_plan(snap(prs=[self.refreshed(same_lines=True, role="builder")]), IDENTITY),
                         [("ask-coordinator-to-sign-off", 113, self.A)], "only main changed: the Coordinator judges, whoever wrote it")

    def test_a_change_to_the_standing_rules_or_their_check_stays_with_the_owner(self):
        for same in (True, False):
            self.assertEqual(merge_rules.merge_plan(snap(prs=[self.refreshed(same_lines=same, files=["system/dispatcher/merge_rules.py"])]), IDENTITY),
                             [("ask-owner-to-reapprove", 113, self.H)])

    def test_a_sign_off_carries_the_owners_approval_and_survives_a_conflict_free_refresh(self):
        self.assertEqual(merge_rules.merge_plan(snap(prs=[self.refreshed(merge_state="CLEAN", sign_off=self.H)]), IDENTITY),
                         [("auto-merge", 113, self.H)])
        self.assertEqual(merge_rules.merge_plan(snap(prs=[self.refreshed(merge_state="CLEAN", sign_off="d" * 40, fresh_sign_off=True)]), IDENTITY),
                         [("auto-merge", 113, self.H)])
        self.assertEqual(merge_rules.merge_plan(snap(prs=[self.refreshed(merge_state="CLEAN", sign_off="d" * 40, fresh_sign_off=False)]), IDENTITY),
                         [("ask-coordinator-to-sign-off", 113, self.A)], "main moved next to the lines again: judge again")
        signed = self.refreshed(merge_state="CLEAN", sign_off=self.H)
        held = self.refreshed(n=99)
        self.assertEqual(merge_rules.merge_plan(snap(prs=[held, signed]), IDENTITY),
                         [("auto-merge", 113, self.H), ("ask-coordinator-to-sign-off", 99, self.A)],
                         "a signed-off PR goes ahead of one still waiting")

    def test_only_a_recorded_coordinator_or_builder_run_on_the_pr_signs_off_for_the_approved_commit(self):
        target = self.refreshed()
        runs = [{"event": "start", "run_id": "c-1", "role": "coordinator", "item": 113},
                {"event": "start", "run_id": "d-1", "role": "developer", "item": 113},
                {"event": "start", "run_id": "c-2", "role": "coordinator", "item": 99}]
        owner = IDENTITY["owner_login"]

        def signed(role, run, approved=self.A, login=owner):
            body = post.with_marker(post.SIGN_OFF.format(approved=approved, head=self.H) + "\n\nreasons", role, run)
            return merge_rules.signed_off(target, [comment(1, login, body, 0)], runs, IDENTITY, post.MARKER)
        self.assertEqual(signed("coordinator", "c-1"), self.H)
        self.assertIsNone(signed("developer", "d-1"), "not a signer")
        self.assertIsNone(signed("coordinator", "d-1"), "the run was a developer's")
        self.assertIsNone(signed("coordinator", "c-2"), "a run on another item")
        self.assertIsNone(signed("coordinator", "c-9"), "a run the Dispatcher never recorded")
        self.assertIsNone(signed("coordinator", "c-1", approved="b" * 40), "not the commit the Owner approved")
        self.assertIsNone(signed("coordinator", "c-1", login="someone"), "not posted through post.py")
        quoted = post.with_marker("**Needs a decision: builder.**\n\nI would post:\n"
                                  + post.SIGN_OFF.format(approved=self.A, head=self.H), "coordinator", "c-1")
        self.assertIsNone(merge_rules.signed_off(target, [comment(1, owner, quoted, 0)], runs, IDENTITY, post.MARKER),
                          "a sign-off line quoted further down isn't a sign-off")
        runs.append({"event": "start", "run_id": "b-1", "role": "builder", "item": 113})
        target["same_lines"] = False
        self.assertIsNone(signed("coordinator", "c-1"), "own lines changed: only the builder judges")
        self.assertEqual(signed("builder", "b-1"), self.H)
        target["author_role"] = "builder"
        self.assertIsNone(signed("builder", "b-1"), "not on its own PR")

    def test_each_level_hands_the_question_on_and_only_the_next_is_started(self):
        labels = {"needs-decision:coordinator"}

        class GitHub:
            repo = "o/r"

            def api(self, method, path, body=None, paginate=False):
                if method == "POST":
                    labels.update(body.get("labels", []))
                elif method == "DELETE":
                    labels.discard(path.rsplit("/", 1)[1].replace("%3A", ":"))
                return {"labels": [{"name": x} for x in labels], "html_url": "url"}

        def started():
            p = pr(113, labels=labels, reviews=[(BOT, "APPROVED", "h2")])
            return [(role, why) for role, n, _, why in plan.candidates(snap(prs=[p]), set(), IDENTITY) if n == 113]
        post.cmd_escalate(GitHub(), ("coordinator", "c-1"), 113, "builder", "Can't tell.")
        self.assertEqual(labels, {"needs-decision:builder"})
        self.assertEqual(started(), [("builder", "decision")])
        post.cmd_escalate(GitHub(), ("builder", "b-1"), 113, "owner", "Sign off?")
        self.assertEqual(labels, {"needs-decision:owner"})
        self.assertEqual(started(), [], "waiting on the Owner: no run is restarted")

    def test_own_lines_ignore_the_code_around_them_but_not_their_order(self):
        changes = lambda patch: {"a.py": ("modified", patch)}
        before = merge_rules.own_lines(changes("@@ @@ def f():\n ctx\n-old\n+new\n+more\n tail"))
        self.assertEqual(before, merge_rules.own_lines(changes("@@ @@ def g():\n other ctx\n-old\n+new\n+more\n changed tail")))
        self.assertNotEqual(before, merge_rules.own_lines(changes("@@ @@ def f():\n ctx\n-old\n+more\n+new\n tail")))
        self.assertEqual(merge_rules.own_lines({"m.bin": ("modified", "s1")}), {"m.bin": ("modified", "s1")})

    def test_the_coordinator_is_started_on_the_pr(self):
        p = pr(113, labels=["needs-decision:coordinator"], reviews=[(BOT, "APPROVED", "h2")])
        self.assertIn(("coordinator", 113, "Item #113 needs your decision (needs-decision:coordinator).", "decision"),
                      plan.candidates(snap(prs=[p]), set(), IDENTITY))


class SR3Test(unittest.TestCase):
    """#221: the builder approves a protected PR in the Owner's place; the Owner keeps a few files."""
    H, OLD = "c" * 40, "d" * 40

    def waiting(self, files=("system/rules.md",), labels=(), merge_state="BLOCKED", approval=None, fresh=None, app=None):
        p = pr(120, role="developer", protected=True, merge_state=merge_state, decision="APPROVED", head=self.H, labels=labels,
               files=files, reviews=[(BOT, "APPROVED", app or self.H)])
        p["fresh"], p["builder_approval"] = {}, approval
        if fresh is not None:
            p["fresh"]["sr3"] = fresh
        return p

    def plan(self, *prs):
        return merge_rules.merge_plan(snap(prs=list(prs)), IDENTITY)

    @staticmethod
    def reviewed(p, at):
        p["reviews"][0]["at"] = at.isoformat().replace("+00:00", "Z")
        return p

    def test_the_builder_is_asked_once_instead_of_the_owner(self):
        ask = [("ask-builder-to-approve", 120, self.H)]
        self.assertEqual(self.plan(self.waiting()), ask)
        self.assertEqual(self.plan(self.waiting(files=["system/dispatcher/plan.py", ".github/workflows/product.yml", "spec/acceptance.md"])), ask)
        self.assertEqual(self.plan(self.waiting(merge_state="BEHIND")), [("refresh", 120, "behind main")] + ask)
        for level in ("builder", "owner"):
            self.assertEqual(self.plan(self.waiting(labels=[f"needs-decision:{level}"])), [], f"already with the {level}")
        self.assertEqual(self.plan(self.waiting(app="e" * 40)), [], "the Reviewer's approval isn't current: nobody is asked")

    def test_the_owner_keeps_the_blueprint_requirements_caps_and_the_rules_check(self):
        for f in merge_rules.SR3_EXCLUDED:
            self.assertEqual(self.plan(self.waiting(files=["system/rules.md", f])), [("ask-owner-to-approve", 120, self.H)], f)
            self.assertEqual(self.plan(self.waiting(files=[f], merge_state="CLEAN", approval=self.H)), [("ask-owner-to-approve", 120, self.H)],
                             f"{f}: a builder approval doesn't count")
        for f in ("blueprint.md", "project_requirements.md", "system/standing-rules.md", "system/caps.toml"):
            self.assertIn(f, merge_rules.SR3_EXCLUDED, "the Owner kept it")

    def test_a_builder_approval_merges_and_survives_a_conflict_free_refresh(self):
        self.assertEqual(self.plan(self.waiting(merge_state="CLEAN", approval=self.H)), [("auto-merge", 120, self.H)])
        self.assertEqual(self.plan(self.waiting(merge_state="CLEAN", approval=self.OLD, fresh=True)), [("auto-merge", 120, self.H)])
        self.assertEqual(self.plan(self.waiting(merge_state="CLEAN", approval=self.OLD, fresh=False)), [("ask-builder-to-approve", 120, self.H)],
                         "the PR changed after the approval: judge again")
        unprotected = self.waiting(approval=None)
        unprotected["protected"] = False
        self.assertFalse(merge_rules.sr3_covers(unprotected))

    def test_only_a_recorded_builder_run_that_started_after_the_reviewers_approval_approves(self):
        reviewed = NOW
        target = self.reviewed(self.waiting(), reviewed)
        runs = [{"event": "start", "run_id": "b-new", "role": "builder", "item": 120, "at": (reviewed + timedelta(minutes=5)).isoformat()},
                {"event": "start", "run_id": "b-wrote", "role": "builder", "item": 120, "at": (reviewed - timedelta(minutes=5)).isoformat()},
                {"event": "start", "run_id": "c-1", "role": "coordinator", "item": 120, "at": (reviewed + timedelta(minutes=5)).isoformat()},
                {"event": "start", "run_id": "b-other", "role": "builder", "item": 99, "at": (reviewed + timedelta(minutes=5)).isoformat()}]
        owner = IDENTITY["owner_login"]

        def approved(role, run, head=self.H, login=owner, pr_=target):
            body = post.with_marker(post.SR3_APPROVAL.format(head=head) + "\n\nchecked", role, run)
            return merge_rules.builder_approved(pr_, [comment(1, login, body, 0)], runs, IDENTITY, post.MARKER)
        self.assertEqual(approved("builder", "b-new"), self.H)
        self.assertIsNone(approved("builder", "b-wrote"), "the run that wrote the PR: never its own approver")
        self.assertIsNone(approved("builder", "b-new", pr_=self.reviewed(self.waiting(), reviewed + timedelta(minutes=10))),
                          "the Reviewer approved again after the run started: it may have pushed what was approved")
        self.assertIsNone(approved("builder", "b-new", pr_=self.waiting()), "no time on the review: nothing counts")
        self.assertIsNone(approved("coordinator", "c-1"), "only the builder")
        self.assertIsNone(approved("builder", "c-1"), "the run was a Coordinator's")
        self.assertIsNone(approved("builder", "b-other"), "a run on another item")
        self.assertIsNone(approved("builder", "b-9"), "a run the Dispatcher never recorded")
        self.assertIsNone(approved("builder", "b-new", login="someone"), "not posted through post.py")
        self.assertIsNone(approved("builder", "b-new", pr_=self.waiting(files=["blueprint.md"])), "a file the Owner kept")
        quoted = post.with_marker("**Needs a decision: owner.**\n\nI would post:\n" + post.SR3_APPROVAL.format(head=self.H), "builder", "b-new")
        self.assertIsNone(merge_rules.builder_approved(target, [comment(1, owner, quoted, 0)], runs, IDENTITY, post.MARKER),
                          "an approval line quoted further down isn't an approval")

    def test_a_writer_that_backdates_its_commit_still_cant_approve_it(self):
        # The run that wrote the PR pushes a commit dated before its own start, then approves it. GitHub's time of
        # the Reviewer's approval decides, not the date the writer set.
        reviewed, owner = NOW, IDENTITY["owner_login"]
        target = self.reviewed(self.waiting(), reviewed)
        runs = [{"event": "start", "run_id": "b-wrote", "role": "builder", "item": 120, "at": (reviewed - timedelta(minutes=5)).isoformat()}]
        approval = post.with_marker(post.SR3_APPROVAL.format(head=self.H) + "\n\nchecked", "builder", "b-wrote")
        asked = []

        class GitHub:
            repo = "o/r"

            def api(self, method, path, body=None, paginate=False):
                asked.append(path)
                if "/comments" in path:
                    return [comment(1, owner, approval, 0)]
                backdated = (reviewed - timedelta(days=1)).isoformat().replace("+00:00", "Z")
                return {"commit": {"committer": {"date": backdated}}}
        merge_rules.annotate(GitHub(), snap(prs=[target]), runs, IDENTITY, post.MARKER)
        self.assertIsNone(target["builder_approval"])
        self.assertEqual(asked, ["repos/o/r/issues/120/comments?per_page=100"], "no commit's own date is read")
        self.assertEqual(merge_rules.merge_plan(snap(prs=[target]), IDENTITY), [("ask-builder-to-approve", 120, self.H)])

    def test_the_builder_is_started_on_the_pr_and_its_escalation_reaches_the_owner(self):
        p = pr(120, protected=True, labels=["needs-decision:builder"], reviews=[(BOT, "APPROVED", "h2")])
        self.assertIn(("builder", 120, "Item #120 needs your decision (needs-decision:builder).", "decision"),
                      plan.candidates(snap(prs=[p]), set(), IDENTITY))
        question = dispatch.approval_question(self.waiting())
        self.assertIn(f"post.py builder-approve 120 --head {self.H}", question)
        self.assertIn("post.py escalate 120 --level owner", question)


def comment(cid, login, body, minutes):
    at = (NOW + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")
    return {"id": cid, "user": {"login": login}, "body": body, "created_at": at, "html_url": f"c/{cid}"}


class NotifyTest(unittest.TestCase):
    ASK = "<!-- role:coordinator run:c1 -->\n**Needs a decision: owner.**\n\nShip it?\n1. Yes (recommended)\n2. No"

    def test_a_question_is_sent_once_then_reminded_once_until_answered(self):
        item = {"number": 7, "title": "Release"}
        comments = [comment(1, "aray4702", self.ASK, 0)]
        got = notify.owner_questions(item, comments, IDENTITY, [], NOW, post.MARKER)
        self.assertEqual([k for k, _ in got], ["ask:1"])
        self.assertIn("Ship it?", got[0][1])
        self.assertNotIn("Needs a decision", got[0][1])
        sent = [{"key": "ask:1", "at": NOW.isoformat()}]
        self.assertEqual(notify.owner_questions(item, comments, IDENTITY, sent, NOW + timedelta(hours=1), post.MARKER), [])
        later = NOW + timedelta(hours=25)
        self.assertEqual([k for k, _ in notify.owner_questions(item, comments, IDENTITY, sent, later, post.MARKER)], ["remind:1"])
        sent.append({"key": "remind:1", "at": later.isoformat()})
        self.assertEqual(notify.owner_questions(item, comments, IDENTITY, sent, later + timedelta(days=3), post.MARKER), [])

    def test_only_the_owner_answers(self):
        item = {"number": 7, "title": "Release"}
        outsider = [comment(1, "aray4702", self.ASK, 0), comment(2, "stranger", "1", 5)]
        self.assertTrue(notify.owner_questions(item, outsider, IDENTITY, [], NOW, post.MARKER))
        answered = [comment(1, "aray4702", self.ASK, 0), comment(2, "aray4702", "1", 5)]
        self.assertEqual(notify.owner_questions(item, answered, IDENTITY, [], NOW, post.MARKER), [])

    def test_latest_ask_names_the_asker_and_whether_the_owner_answered(self):
        ask = comment(1, "aray4702", self.ASK, 0)
        self.assertEqual(notify.latest_ask([ask], IDENTITY, post.MARKER)[1:], ("coordinator", False))
        self.assertEqual(notify.latest_ask([ask, comment(2, "sloan3165", "1", 5)], IDENTITY, post.MARKER)[1:], ("coordinator", True))
        self.assertEqual(notify.latest_ask([ask, comment(2, "stranger", "1", 5)], IDENTITY, post.MARKER)[1:], ("coordinator", False))
        self.assertIsNone(notify.latest_ask([comment(3, "aray4702", "plain", 0)], IDENTITY, post.MARKER))

    def test_an_item_closed_while_held_for_the_owner_is_reopened_until_answered(self):
        ask = comment(1, "aray4702", self.ASK, 0)
        def gh_with(labels, comments):
            responses = {"closed": [{"number": 81, "labels": [{"name": n} for n in labels]},
                                    {"number": 89, "pull_request": {}, "labels": [{"name": "needs-decision:owner"}]}],
                         "comments": comments}
            gh = mock.Mock(repo="o/r")
            gh.api.side_effect = lambda method, path, body=None, paginate=False: (
                responses["closed"] if "state=closed" in path else responses["comments"])
            return gh
        self.assertEqual(dispatch.orphaned_asks(gh_with(["needs-decision:owner"], [ask]), IDENTITY, NOW), [(81, 1)])
        answered = [ask, comment(2, "aray4702", "13a 14a", 5)]
        self.assertEqual(dispatch.orphaned_asks(gh_with(["needs-decision:owner"], answered), IDENTITY, NOW), [], "answered")
        self.assertEqual(dispatch.orphaned_asks(gh_with(["type:definition"], [ask]), IDENTITY, NOW), [], "no longer held")
        self.assertEqual(dispatch.orphaned_asks(gh_with(["needs-decision:owner"], []), IDENTITY, NOW), [], "no question asked")

    def test_unsent_filters_by_key(self):
        self.assertEqual(notify.unsent([{"key": "a"}], [("a", "x"), ("b", "y")]), [("b", "y")])


class FakeGitHub:
    repo = "aray4702/local_meeting_transcriber"
    requirements = "## 2. Goals\n\n| ID | Goal | Outcome | Deadline |\n| --- | --- | --- | --- |\n| S1 | seed | x | none |\n"

    def __init__(self, repo=None):
        self.writes = []

    def api(self, method, path, body=None, paginate=False):
        if method != "GET":
            self.writes.append((method, path))
        if path.endswith("actions/variables/AGENTS_PAUSED"):
            raise SystemExit("failed: Not Found (HTTP 404)")
        if path == f"repos/{self.repo}/contents/project_requirements.md?ref=main":
            return {"encoding": "base64", "content": base64.b64encode(self.requirements.encode()).decode()}
        if "labels=record%3Agoal" in path:
            return [{"number": 21, "title": "Goal S1: seed goal (README)", "labels": [{"name": "record:goal"}]}]
        if path.startswith(f"repos/{self.repo}/issues?state=closed"):
            assert "since=" in path, path
            return [{"number": 20, "title": "Def", "labels": [{"name": "type:definition"}], "closed_at": "2026-10-27T02:30:00Z"},
                    {"number": 13, "title": "Log", "labels": [{"name": "record:decision-log"}], "closed_at": "2026-10-27T02:40:00Z"},
                    {"number": 5, "title": "Old", "labels": [], "closed_at": "2026-10-10T00:00:00Z"}]
        if path.startswith(f"repos/{self.repo}/issues?"):
            return [
                {"number": 1, "title": "Crash", "labels": [{"name": "type:fix"}, {"name": "sev:1"}], "html_url": "u", "body": ""},
                {"number": 2, "title": "Idea", "labels": [], "html_url": "u", "body": ""},
            ]
        return []

    def graphql(self, query, **variables):
        return {"repository": {"pullRequests": {"nodes": []}}}


class FakeStore:
    def __init__(self, *args):
        self.appended = []

    def read(self, kind):
        return [r for k, r in self.appended if k == kind]

    def append(self, kind, record):
        self.appended.append((kind, record))


class WordingTest(unittest.TestCase):
    def test_articles(self):
        self.assertEqual([dispatch.article(r) for r in ("architect", "developer", "reviewer")], ["an", "a", "a"])


class DryRunTest(unittest.TestCase):
    def test_a_dry_run_plans_and_changes_nothing(self):
        stores = []
        with mock.patch.object(post, "GitHub", FakeGitHub), \
             mock.patch("system.dispatcher.state.Store", side_effect=lambda *a: stores.append(FakeStore()) or stores[-1]), \
             mock.patch.object(dispatch, "spawn") as spawn, \
             mock.patch.object(plan, "daily_due", return_value=None), \
             mock.patch.object(dispatch.relay, "run", return_value=[]):  # never Discord from a test (test_relay.py)
            lines = dispatch.dispatch_pass("reconcile", dry_run=True, now=NOW)
        self.assertEqual(lines, [
            "would start a developer run on #1 (sev:1): Item #1 is sev:1: revert first (blueprint §3), then fix the cause.",
            "would start a coordinator run (triage+closed): Triage these issues: #2. Items closed since your last run: #20. "
            "Record their goals' progress, close what is done, and chart and schedule what comes next.",
        ])
        spawn.assert_not_called()
        self.assertEqual(stores[0].appended, [])

    def test_a_pass_catches_up_the_builders_daily_run(self):
        # NOW is 20:00 PT and no daily run has started today (#186): it takes the second slot, ahead of triage.
        # Run at the sizing's 2 slots, not the Owner's temporary 3 (#84).
        caps = tomllib.loads((ROOT / "system" / "caps.toml").read_text())
        caps["concurrency"] = {"max_runs": 2, "max_runs_per_role": 1}
        real_load = dispatch.runner.load_all
        with mock.patch.object(dispatch.runner, "load_all", lambda *a, **k: {**real_load(*a, **k), "caps": caps}), \
             mock.patch.object(post, "GitHub", FakeGitHub), \
             mock.patch("system.dispatcher.state.Store", FakeStore), \
             mock.patch.object(dispatch, "spawn"), \
             mock.patch.object(dispatch.relay, "run", return_value=[]):
            lines = dispatch.dispatch_pass("poll", dry_run=True, now=NOW)
        self.assertEqual(lines[1:], [f"would start a builder run (daily-catch-up): {DailyCatchUpTest.TASK}",
                                     "held: a coordinator run (triage+closed): 2 runs are active; the cap is 2"])


class HeldForTheOwner(FakeGitHub):
    """#81 closed while its question to the Owner was unanswered (#114)."""
    def api(self, method, path, body=None, paginate=False):
        if path.startswith(f"repos/{self.repo}/issues?state=closed&labels=needs-decision%3Aowner"):
            return [{"number": 81, "title": "Def", "labels": [{"name": "needs-decision:owner"}]}]
        if path == f"repos/{self.repo}/issues/81/comments?per_page=100":
            return [comment(1, "aray4702", NotifyTest.ASK, 0)]
        got = super().api(method, path, body, paginate)
        return {"html_url": "c/2"} if method == "POST" else got


class ReopenTest(unittest.TestCase):
    def passes(self, *dry_runs, gh=HeldForTheOwner):
        store, github = FakeStore(), gh()
        with mock.patch.object(post, "GitHub", lambda repo: github), \
             mock.patch("system.dispatcher.state.Store", return_value=store), \
             mock.patch.object(dispatch, "spawn"), \
             mock.patch.object(dispatch.relay, "run", return_value=[]):
            lines = [dispatch.dispatch_pass("poll", dry_run=d, now=NOW) for d in dry_runs]
        return lines, github.writes, store.appended

    def test_a_dry_run_says_it_would_reopen_and_changes_nothing(self):
        (lines,), writes, appended = self.passes(True)
        self.assertIn("would reopen #81: it closed while its question to the Owner was unanswered", lines)
        self.assertEqual((writes, appended), ([], []))

    def test_an_item_is_reopened_once_per_question_and_stays_closed_after(self):
        # The second pass still finds #81 closed (closed again), its question unchanged and unanswered.
        (first, second), writes, appended = self.passes(False, False)
        self.assertIn("reopen #81: it closed while its question to the Owner was unanswered", first)
        self.assertFalse([line for line in second if "reopen" in line], second)
        self.assertEqual(writes, [("PATCH", "repos/aray4702/local_meeting_transcriber/issues/81"),
                                  ("POST", "repos/aray4702/local_meeting_transcriber/issues/81/comments")])
        self.assertEqual(appended, [("notices", {"key": "reopen:1", "at": NOW.isoformat()})])

    def test_a_failed_check_never_stops_the_pass(self):
        class Down(HeldForTheOwner):
            def api(self, method, path, body=None, paginate=False):
                if "labels=needs-decision%3Aowner" in path:
                    raise SystemExit("failed: Bad Gateway (HTTP 502)")
                return super().api(method, path, body, paginate)
        (lines,), _, _ = self.passes(True, gh=Down)
        self.assertEqual(lines[0], "reopen check failed: SystemExit: failed: Bad Gateway (HTTP 502)")
        self.assertTrue(any(line.startswith("would start a developer run on #1") for line in lines), lines)


if __name__ == "__main__":
    unittest.main()
