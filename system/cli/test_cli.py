"""Tests for the Owner's CLI and dashboard. Nothing here touches GitHub."""

import fcntl
import socketserver
import tempfile
import threading
import tomllib
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from system.cli import arsys, data, views
from system.dispatcher import run
from system.tools import post, runner

ROOT = Path(__file__).resolve().parents[2]
IDENTITY = post.load_identity()
CONFIG = runner.load_all()
CAPS = tomllib.loads((ROOT / "system" / "caps.toml").read_text())
BOT, SECOND = IDENTITY["reviewer_app"]["bot_login"], IDENTITY["second_login"]
NOW = datetime(2026, 10, 27, 6, 0, tzinfo=timezone.utc)  # 23:00 PDT: no PT-midnight edge in the runs below

REQUIREMENTS = """# Requirements

| Version | Date       | By | Change        |
| ------- | ---------- | -- | ------------- |
| 1.0     | 2026-10-26 | o  | First version |
| 1.3     | 2026-10-26 | b  | S1 struck     |

## 2. Goals

| ID  | Goal                    | Measurable outcome or requirement IDs              | Deadline |
| --- | ----------------------- | -------------------------------------------------- | -------- |
| G0  | the starting point (§0) | its done-check, from Definition (none for scratch) |          |
| ~~S1~~ | ~~seed~~ | ~~readme~~ | ~~none~~ |
| G1  |                         |                                                    |          |

## 3. Use cases
"""


def pr(**over):
    base = {"number": 9, "title": "t", "draft": False, "head": "h2", "merge_state": "BLOCKED", "review_decision": "REVIEW_REQUIRED",
            "auto_merge": False, "author": IDENTITY["owner_login"], "author_role": "developer", "labels": set(), "protected": False, "gate": "SUCCESS", "reviews": []}
    base.update(over)
    return base


class RequirementsEditTest(unittest.TestCase):
    def test_a_goal_fills_the_templates_empty_row_and_the_version_bumps(self):
        out = arsys.bump_version(arsys.add_row(REQUIREMENTS, "## 2. Goals", "G1", ["Transcribe calls", "WER < 10 %", "2026-12-01"]),
                                 "Added goal G1", "2026-10-27")
        self.assertIn("| G1 | Transcribe calls | WER < 10 % | 2026-12-01 |", out)
        self.assertEqual(out.count("| G1"), 1)
        self.assertIn("| 1.4     | 2026-10-27 | Owner, with arsys | Added goal G1 |", out)

    def test_a_new_id_is_appended_to_the_table(self):
        out = arsys.add_row(REQUIREMENTS, "## 2. Goals", "G2", ["More", "x", ""])
        lines = out.split("\n")
        self.assertEqual(lines[lines.index("| G2 | More | x |  |") - 1].split("|")[1].strip(), "G1")

    def test_an_id_in_use_or_struck_is_never_reused(self):
        filled = arsys.add_row(REQUIREMENTS, "## 2. Goals", "G1", ["A", "B", ""])
        with self.assertRaises(SystemExit):
            arsys.add_row(filled, "## 2. Goals", "G1", ["C", "D", ""])
        with self.assertRaises(SystemExit):
            arsys.add_row(REQUIREMENTS, "## 2. Goals", "S1", ["reuse", "x", ""])


class WaitingOnTest(unittest.TestCase):
    def test_every_stage_of_the_merge_flow(self):
        w = lambda **o: data.waiting_on(pr(**o), IDENTITY)
        self.assertEqual(w(gate=None), "CI")
        self.assertEqual(w(gate="FAILURE"), "author: red gate")
        self.assertEqual(w(reviews=[{"login": BOT, "state": "CHANGES_REQUESTED", "commit": "h2"}]), "author: changes requested")
        self.assertEqual(w(), "Reviewer")
        app = [{"login": BOT, "state": "APPROVED", "commit": "h2"}]
        self.assertEqual(w(reviews=app, merge_state="BEHIND"), "Dispatcher: refresh")
        self.assertEqual(w(reviews=app, protected=True), "you: approve (second account)")
        self.assertEqual(w(reviews=app, protected=True, review_decision="APPROVED", merge_state="CLEAN"), "you: merge")
        self.assertEqual(w(reviews=app, review_decision="APPROVED", merge_state="CLEAN"), "Dispatcher: auto-merge")
        self.assertEqual(w(author_role=None), "you: approve (second account), then merge")

    def test_an_outsiders_pr_is_theirs_and_waits_on_triage_never_approval(self):
        # github_state gives no role to the Owner's own PRs or to outsiders'; anyone can open a PR on a public repo
        app = [{"login": BOT, "state": "APPROVED", "commit": "h2"}]
        for p in (pr(author="stranger", author_role=None), pr(author="stranger", author_role=None, reviews=app, gate=None),
                  pr(author=None, author_role=None)):
            self.assertEqual(data.waiting_on(p, IDENTITY), "you: triage (outside contributor)")
        self.assertEqual(data.author(pr(author="stranger", author_role=None), IDENTITY), "outsider stranger")
        self.assertEqual(data.author(pr(author_role=None), IDENTITY), "owner")
        self.assertEqual(data.author(pr(), IDENTITY), "developer")


class RunnerViewTest(unittest.TestCase):
    def test_the_fetch_holds_the_shared_checkout_lock_a_launcher_takes(self):
        # an unlocked fetch beside a launcher's makes the launcher's fail, and its run doesn't start
        with tempfile.TemporaryDirectory() as d:
            config = {**CONFIG, "runner": {**CONFIG["runner"], "runner": {**CONFIG["runner"]["runner"], "home": d}}}
            held = []

            def fake_run(cmd, **kw):
                with open(Path(d, "system.lock"), "w") as probe:
                    try:
                        fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        held.append(False)
                    except BlockingIOError:
                        held.append(True)
                return mock.Mock(returncode=0)
            with mock.patch.object(data.runner.subprocess, "run", side_effect=fake_run), \
                 mock.patch.object(data.runner, "commits", return_value=("a", "a")), \
                 mock.patch.object(data.runner, "claude_login", return_value=("claude.ai", "max")), \
                 mock.patch.object(data.runner, "problems", return_value=[]):
                view = data.runner_view(config)
            self.assertEqual(held, [True])
            self.assertTrue(view["ok"], view)
            self.assertIs(run.locked, data.runner.locked, "the launcher and the CLI must take the same lock")

    def test_a_failed_fetch_is_reported_and_the_rest_still_checked(self):
        with mock.patch.object(data.runner, "fetch_main", side_effect=OSError("offline")), \
             mock.patch.object(data.runner, "commits", return_value=("a", "b")), \
             mock.patch.object(data.runner, "claude_login", return_value=("claude.ai", "max")), \
             mock.patch.object(data.runner, "problems", return_value=["the applied checkout is at a, main is at b"]):
            view = data.runner_view(CONFIG)
        self.assertFalse(view["ok"])
        self.assertEqual(len(view["problems"]), 2)
        self.assertIn("offline", view["problems"][0])


def sample():
    return {
        "now": NOW.isoformat(), "repo": "aray4702/local_meeting_transcriber", "time_zone": "America/Los_Angeles",
        "paused": False, "pause_reason": "AGENTS_PAUSED is not set",
        "decisions": [{"number": 49, "title": "Release <S1>", "asker": "coordinator", "question": "Publish?\n1. Yes",
                       "answered": False, "url": "u"}],
        "prs": [{"number": 50, "title": "<script>alert(1)</script>", "author": "builder", "gate": "SUCCESS",
                 "protected": True, "waiting_on": "you: merge"}],
        "work_order": [{"order": 1, "number": 29, "parallel_safe": False, "title": "README", "labels": ["type:feature"]}],
        "items": [{"number": 31, "title": "milestones", "labels": ["type:system"]}],
        "usage": data.usage_view(CAPS, [
            {"event": "start", "run_id": "r1", "role": "reviewer", "item": 50, "at": (NOW - timedelta(minutes=2)).isoformat()},
            {"event": "end", "run_id": "r0", "role": "developer", "item": 29, "at": (NOW - timedelta(hours=1)).isoformat(),
             "cost_usd": 1.07, "five_hour": 0.02, "seven_day": 0.07, "seven_day_resets_at": int((NOW + timedelta(days=2)).timestamp())},
        ], NOW, "America/Los_Angeles"),
        "last_heartbeat": None, "last_run": {"run_id": "r1", "event": "start"},
        "runner": {"ok": True, "problems": [], "applied": "abc1234", "main": "abc1234"},
        "merges": [{"number": 50, "title": "Strike S1", "mergedAt": "2026-10-27T06:42:20Z", "url": "u"}],
    }


class ViewsTest(unittest.TestCase):
    def test_each_overview_section_is_a_tab_of_its_own(self):
        d = sample()
        heads = {path: views.html_page(d, path) for path, _ in views.OVERVIEW}
        self.assertIn("<h2>Waiting on you</h2>", heads["/waiting"])
        self.assertNotIn("<h2>Pull requests</h2>", heads["/waiting"])
        self.assertIn("<h2>Usage against the caps</h2>", heads["/usage"])
        self.assertIn("<h2>Open items</h2>", heads["/items"])
        self.assertEqual([p for p, _ in views.TABS][:2], ["/", "/roles"], "Progress, then Roles, first")

    def test_usage_counts_the_window_the_roles_and_the_active_runs(self):
        u = sample()["usage"]
        self.assertEqual((u["cost_window"], u["seven_day"], len(u["active"])), (1.07, 0.07, 1))
        self.assertAlmostEqual(u["points_used"], round(1.07 * CAPS["claude"]["points_per_usd"], 2))
        self.assertEqual(u["per_role"]["reviewer"]["today"], 1)

    def test_text_puts_what_waits_on_the_owner_first(self):
        out = views.text(sample())
        self.assertIn("Waiting on you (1 decisions):", out)
        self.assertLess(out.index("#49"), out.index("Pull requests:"))
        self.assertIn("PR #50", out)
        self.assertIn("reviewer on #50", out)

    def test_html_escapes_github_text_and_carries_the_icon_and_favicon(self):
        page = views.html_page(sample())
        every = "".join(views.html_page(sample(), path) for path, _ in views.OVERVIEW)
        self.assertNotIn("<script>alert(1)</script>", every)
        self.assertIn("&lt;script&gt;", every)
        self.assertIn('<link rel="icon" type="image/svg+xml" href="/favicon.svg">', page)
        self.assertIn('rel="alternate icon" href="data:image/svg+xml,', page)
        self.assertIn("<header><svg", page)
        self.assertIn("prefers-color-scheme:dark", page)
        self.assertIn('name="viewport"', page)

    def test_the_kill_switch_is_impossible_to_miss(self):
        d = sample()
        d.update(paused=True, pause_reason="AGENTS_PAUSED is 'true'")
        for path, _ in views.OVERVIEW:
            self.assertIn("Kill switch thrown", views.html_page(d, path), f"{path}: on every Overview tab (#253)")
        self.assertIn("KILL SWITCH: THROWN", views.text(d))


class MergesTest(unittest.TestCase):
    def test_every_merge_from_the_owners_account_across_pages(self):
        pages = [
            {"pageInfo": {"hasNextPage": True, "endCursor": "c1"}, "nodes": [
                {"number": 50, "title": "a", "mergedAt": "2026-10-27T06:42:00Z", "url": "u", "mergedBy": {"login": SECOND}},
                {"number": 45, "title": "b", "mergedAt": "2026-10-27T06:35:00Z", "url": "u", "mergedBy": {"login": "aray4702"}}]},
            {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": [
                {"number": 3, "title": "c", "mergedAt": "2026-10-27T01:37:00Z", "url": "u", "mergedBy": {"login": "aray4702"}}]},
        ]
        gh = mock.Mock()
        gh.graphql.side_effect = lambda q, **v: {"repository": {"pullRequests": pages[0 if v["after"] is None else 1]}}
        self.assertEqual([m["number"] for m in data.merges_by_owner_account(gh, IDENTITY)], [45, 3])
        self.assertEqual(gh.graphql.call_args_list[1].kwargs["after"], "c1")

    def test_reaching_the_page_bound_with_pages_left_is_loud(self):
        page = {"pageInfo": {"hasNextPage": True, "endCursor": "c"}, "nodes": [
            {"number": 45, "title": "b", "mergedAt": "2026-10-27T06:35:00Z", "url": "u", "mergedBy": {"login": "aray4702"}}]}
        gh = mock.Mock()
        gh.graphql.return_value = {"repository": {"pullRequests": page}}
        with self.assertRaisesRegex(RuntimeError, "incomplete"):
            data.merges_by_owner_account(gh, IDENTITY, max_pages=2)
        self.assertEqual(gh.graphql.call_count, 2)

    def test_a_last_page_at_the_bound_is_complete(self):
        page = {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": [
            {"number": 45, "title": "b", "mergedAt": "2026-10-27T06:35:00Z", "url": "u", "mergedBy": {"login": "aray4702"}}]}
        gh = mock.Mock()
        gh.graphql.return_value = {"repository": {"pullRequests": page}}
        self.assertEqual([m["number"] for m in data.merges_by_owner_account(gh, IDENTITY, max_pages=1)], [45])


class DashboardServerTest(unittest.TestCase):
    def test_serves_the_page_and_favicon_on_localhost_and_refuses_writes(self):
        self.check_server()

    def test_the_first_page_is_full_on_a_machine_booted_seconds_ago(self):
        # time.monotonic() counts from boot on Linux, so a fresh CI runner reads it below 30 s
        with mock.patch.object(arsys.time, "monotonic", return_value=5.0):
            self.check_server()

    def check_server(self):
        started = threading.Event()
        servers = []
        real = arsys.http.server.ThreadingHTTPServer

        class Server(real):
            def server_bind(self):  # no socket.getfqdn, which waits out macos-26's resolver (#648)
                socketserver.TCPServer.server_bind(self)
                self.server_name, self.server_port = self.server_address[:2]

        def capture(addr, handler):
            server = Server(("127.0.0.1", 0), handler)
            servers.append((addr, server))
            started.set()
            return server
        from system.cli.test_progress import ProgressViewTest, RolesTest
        with mock.patch.object(arsys.data, "collect", return_value=sample()), \
             mock.patch.object(arsys.data, "progress", return_value=ProgressViewTest().page_data()), \
             mock.patch.object(arsys.data, "roles", return_value=RolesTest().roles()), \
             mock.patch.object(arsys.http.server, "ThreadingHTTPServer", side_effect=capture), \
             mock.patch("builtins.print"):
            t = threading.Thread(target=arsys.serve, args=({}, 8765), daemon=True)
            t.start()
            self.assertTrue(started.wait(30), "the dashboard's server didn't start")
            (addr, server), = servers
            self.assertEqual(addr, ("127.0.0.1", 8765), "the dashboard must bind to this Mac only")
            base = f"http://127.0.0.1:{server.server_address[1]}"
            page = urllib.request.urlopen(base + "/").read().decode()
            self.assertIn("auto_research", page)
            self.assertIn('<a href="/" aria-current=page>Progress</a>', page, "Progress is the default tab (#246)")
            self.assertIn("Met: 0 of 2 features", page)
            roles = urllib.request.urlopen(base + "/roles").read().decode()
            self.assertIn('<a href="/roles" aria-current=page>Roles</a>', roles)
            for path, name in views.OVERVIEW:
                tab = urllib.request.urlopen(base + path).read().decode()
                self.assertIn(f'<a href="{path}" aria-current=page>{name}</a>', tab)
            old = urllib.request.urlopen(base + "/overview").read().decode()
            self.assertIn('<a href="/waiting" aria-current=page>Waiting on you</a>', old, "a saved Overview link still opens")
            self.assertEqual(arsys.data.collect.call_count, 1, "the Overview tabs share one read")
            icon = urllib.request.urlopen(base + "/favicon.svg")
            self.assertEqual(icon.headers["Content-Type"], "image/svg+xml")
            self.assertEqual(icon.read().decode(), views.ICON_SVG)
            with self.assertRaises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(urllib.request.Request(base + "/", data=b"x", method="POST"))
            self.assertEqual(e.exception.code, 405)
            e.exception.close()
            server.shutdown()


if __name__ == "__main__":
    unittest.main()
