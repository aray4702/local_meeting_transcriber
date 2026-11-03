#!/usr/bin/env python3
"""The Dispatcher (blueprint §2, §4): everything mechanical, no judgment calls.

  dispatch.py poll [--dry-run]        every 2 minutes
  dispatch.py reconcile [--dry-run]   every hour: a poll, plus expired claims and a heartbeat
  dispatch.py daily                   anomaly signals and the rule audit (blueprint §8 step 7), raised once each
  dispatch.py audit [product|system|all]   07:30, and on demand: the daily pass, and reports (audit.py)

Each pass: the kill switch; runs whose launcher died; the merge queue; new runs in dispatch order
within the caps; notices to the Owner. A pass that raises tells the Owner, once a day, and exits 1.
With --dry-run it prints what it would do and changes nothing. Standard library only.
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from system.dispatcher import audit, daily, flow, github_state, killswitch, merge_rules, notify, plan, relay, state, usage  # noqa: E402
from system.tools import post, runner, tracker  # noqa: E402


def article(word):
    return "an" if word[0] in "aeiou" else "a"


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def sign_off_question(pr, approved):
    """The SR2 question (#150), asked once on the PR. Own lines unchanged: the Coordinator judges, then the builder,
    then the Owner. Own lines changed (on a PR the builder didn't write): the builder, then the Owner."""
    n, head = pr["number"], pr["head"]
    if pr.get("same_lines"):
        what = (f"Since then only main changed: the PR's own added and removed lines are the same, in order, but main "
                f"edited code next to them, so that approval no longer counts by itself.\n\n"
                f"Judge whether main's changes around those lines change what the Owner approved: compare "
                f"`compare/{approved}...{head}` and read main's commits that touched the same places.\n")
    else:
        what = (f"Since then the PR's own lines changed, and the Reviewer approved the new head.\n\n"
                f"Judge whether the changes stay within what the Owner approved (for example, fixes the Reviewer asked "
                f"for) or change what it does in a way the Owner should see: compare `compare/{approved}...{head}`.\n")
    return (f"**SR2.** The Owner approved this PR at `{approved}`. {what}"
            f"- **Within it:** `post.py sign-off {n} --approved {approved} --head {head}` with your reasons as the "
            f"body. SR1 then merges it in its turn.\n"
            f"- **You can't tell** (Coordinator): `post.py escalate {n} --level builder` with what you found.\n"
            f"- **You can't tell** (builder): `post.py escalate {n} --level owner`, asking whether to sign off. On "
            f"the Owner's yes, sign off quoting it; otherwise the Owner approves the PR again on GitHub.\n\n"
            f"Only a sign-off from a run on this PR, by a role SR2 lets judge this kind of change, counts "
            f"(`system/standing-rules.md`).")


def approval_question(pr):
    """The SR3 question (#221), asked once per head on the PR: the builder approves it in the Owner's place, or
    escalates it to the Owner."""
    n, head = pr["number"], pr["head"]
    return (f"**SR3.** The Reviewer approved this protected PR at `{head}`, and its gate is green. Approve it in the "
            f"Owner's place, or pass it to the Owner (`system/standing-rules.md`, SR3; your role file says what to check).\n\n"
            f"- **It's yours to approve:** `post.py builder-approve {n} --head {head}` with what you checked as the "
            f"body. SR1 then merges it in its turn.\n"
            f"- **It's an Owner matter, or you can't tell:** `post.py escalate {n} --level owner`, with one question "
            f"and a recommendation. The Owner then approves it on GitHub, or not.\n\n"
            f"Only an approval from a builder run on this PR that started after the Reviewer approved it counts: never "
            f"from the run that wrote it. Don't push to this PR: a new commit needs the Reviewer again.")


def expired_claims(gh, items, active_items, now):
    out = []
    for n in items:
        if n in active_items:
            continue
        comments = gh.api("GET", f"repos/{gh.repo}/issues/{n}/comments?per_page=100", paginate=True)
        expiries = [post.CLAIM_EXPIRY.search(c.get("body") or "") for c in comments]
        expiries = [datetime.fromisoformat(m["at"]) for m in expiries if m]
        if not expiries or expiries[-1] <= now:
            out.append(n)
    return out


def spawn(config, role, item, task, logs):
    """Start run.py detached; it re-checks the kill switch and the caps, and claims the item."""
    cmd = [config["runner"]["runner"]["python"], "-I", str(ROOT / "system" / "dispatcher" / "run.py"), role, "--task", task]
    if item:
        cmd += ["--item", str(item), "--claim"]
    logs.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with open(logs / f"launcher-{role}-{stamp}.log", "ab") as log:
        subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)


def relay_answers(gh, store, identity, dry_run, now):
    # The Owner may ask for an audit in the chat: it runs here, and the relay replies with the reports' links.
    on_audit = lambda kinds: audit_pass(kinds, dry_run=False, now=now, announce=False)[1]  # noqa: E731
    try:
        return relay.run(gh, store, identity, dry_run, now, on_audit=on_audit)
    except (Exception, SystemExit) as e:  # the chat must never stop a pass (GitHub errors are SystemExit); no secret named
        return [f"relay failed: {type(e).__name__}: {e}"]


def orphaned_asks(gh, identity, now, days=2):
    """Items closed while held for the Owner, their latest question unanswered: closing (often a PR's
    `Resolves`) would otherwise hide the question, since only open items are forwarded (#114)."""
    since = (now - timedelta(days=days)).isoformat().replace("+00:00", "Z")
    out = []
    for i in gh.api("GET", f"repos/{gh.repo}/issues?state=closed&labels=needs-decision%3Aowner&since={since}&per_page=100",
                    paginate=True):
        if "pull_request" in i or "needs-decision:owner" not in {x["name"] for x in i["labels"]}:
            continue
        comments = gh.api("GET", f"repos/{gh.repo}/issues/{i['number']}/comments?per_page=100", paginate=True)
        found = notify.latest_ask(comments, identity, post.MARKER)
        if found and not found[2]:
            out.append((i["number"], found[0]["id"]))
    return out


def reopen_orphans(gh, store, me, identity, notices, dry_run, now):
    """Reopen each orphaned question's item once per question (`reopen:<ask id>`): closed again, it stays closed."""
    done = {n["key"] for n in notices}
    lines = []
    try:
        for n, ask_id in orphaned_asks(gh, identity, now):
            if f"reopen:{ask_id}" in done:
                continue
            lines.append(("would " if dry_run else "") + f"reopen #{n}: it closed while its question to the Owner was unanswered")
            if not dry_run:
                gh.api("PATCH", f"repos/{gh.repo}/issues/{n}", {"state": "open"})
                post.cmd_comment(gh, me, n, "Reopened: this item closed while its question to the Owner was still unanswered, and "
                                 "only open items' questions are forwarded (#114). The next pass forwards it; close it again once "
                                 "it's answered.")
                store.append("notices", {"key": f"reopen:{ask_id}", "at": now.isoformat()})
    except (Exception, SystemExit) as e:  # best-effort, like the relay: never stops a pass (GitHub errors are SystemExit)
        lines.append(f"reopen check failed: {type(e).__name__}: {e}")
    return lines


def dispatch_pass(command, dry_run, now=None):
    now = now or datetime.now(timezone.utc).replace(microsecond=0)
    config = runner.load_all()
    identity, caps = config["identity"], config["caps"]
    gh = post.GitHub(identity["repo"])
    me = ("dispatcher", f"dispatcher-{now:%Y%m%dT%H%M%SZ}")
    lines = []
    say = lambda text: lines.append(("would " if dry_run else "") + text)

    thrown, why = killswitch.paused(gh)
    if thrown:  # the relay too: nothing posts as the Owner while paused; answers wait at the relay's cursor
        return [f"paused: {why}"]
    store = state.Store(runner.home(config) / "state", f"https://github.com/{identity['repo']}.git")
    lines += relay_answers(gh, store, identity, dry_run, now)
    lines += reopen_orphans(gh, store, me, identity, store.read("notices"), dry_run, now)
    runs, notices = store.read("runs"), store.read("notices")

    # Runs whose launcher died without recording an end.
    for r in usage.active(runs):
        if r.get("pid") and not alive(r["pid"]):
            say(f"record {r['run_id']} as cut off" + (f" and release #{r['item']}" if r.get("item") else ""))
            if not dry_run:
                store.append("runs", {"run_id": r["run_id"], "role": r["role"], "item": r.get("item"), "event": "end",
                                      "at": now.isoformat(), "status": "cut-off"})
                if r.get("item"):
                    post.cmd_release(gh, me, r["item"])
    runs = store.read("runs") if not dry_run else runs
    active_items = {r.get("item") for r in usage.active(runs) if r.get("item")}

    # Closing events since the Coordinator's last run ended start it again (blueprint §4.1).
    ends = [datetime.fromisoformat(r['at']) for r in runs if r['event'] == 'end' and r['role'] == 'coordinator']
    snap = github_state.snapshot(gh, identity, closed_since=max(ends) if ends else now - timedelta(days=7))
    url = lambda n: f"https://github.com/{identity['repo']}/pull/{n}"
    wanted, renewed = [], set()

    merge_rules.annotate(gh, snap, runs, identity, post.MARKER)

    # The merge queue: one PR at a time.
    for action, n, detail in merge_rules.merge_plan(snap, identity):
        if action == "refresh":
            say(f"refresh PR #{n} from main ({detail})")
            if not dry_run:
                gh.api("PUT", f"repos/{gh.repo}/pulls/{n}/update-branch", {})
        elif action == "auto-merge":
            say(f"turn on auto-merge for PR #{n}")
            if not dry_run:
                subprocess.run(["gh", "pr", "merge", str(n), "--auto", "--merge", "--repo", gh.repo], check=True, capture_output=True)
        elif action == "cancel-auto-merge":
            say(f"turn off auto-merge for PR #{n}: changes were pushed after its approval")
            if not dry_run:
                subprocess.run(["gh", "pr", "merge", str(n), "--disable-auto", "--repo", gh.repo], check=True, capture_output=True)
        elif action == "renew":
            pr = next(p for p in snap["prs"] if p["number"] == n)
            if merge_rules.same_changes(gh, detail, pr["head"]):
                say(f"renew the Reviewer App's approval of PR #{n} (its own changes are as they were at {detail[:7]})")
                renewed.add(n)
                if not dry_run:
                    post.cmd_review(identity, me, n, "APPROVE",
                                    f"Renewed after a refresh from main: the PR's own changes are unchanged since the approval of {detail[:7]}.")
        elif action in ("ask-coordinator-to-sign-off", "ask-builder-to-sign-off"):
            level = action.split("-")[1]
            say(f"ask the {'Coordinator' if level == 'coordinator' else level} to judge PR #{n} under SR2 (the Owner approved {detail[:7]})")
            if not dry_run:
                post.cmd_escalate(gh, me, n, level, sign_off_question(next(p for p in snap["prs"] if p["number"] == n), detail))
        elif action == "ask-builder-to-approve":
            say(f"ask the builder to approve PR #{n} under SR3, in the Owner's place (head {detail[:7]})")
            if not dry_run:
                post.cmd_escalate(gh, me, n, "builder", approval_question(next(p for p in snap["prs"] if p["number"] == n)))
        else:
            wanted.append(notify.merge_notice(action, n, detail, url(n)))

    # Questions for the Owner: forwarded once and reminded once; once answered, the asker is started.
    answered = {}
    for item in snap["issues"] + [{"number": p["number"], "title": p["title"], "labels": p["labels"]} for p in snap["prs"]]:
        if "needs-decision:owner" in item["labels"]:
            comments = gh.api("GET", f"repos/{gh.repo}/issues/{item['number']}/comments?per_page=100", paginate=True)
            wanted += notify.owner_questions(item, comments, identity, notices, now, post.MARKER,
                                             reply=bool(relay.settings(identity)))
            found = notify.latest_ask(comments, identity, post.MARKER)
            if found and found[2] and found[1] in config["runner"]["roles"]:
                answered[item["number"]] = found[1]

    # New runs, in dispatch order, within the caps.
    starts, skipped = plan.choose(snap, runs, caps, identity, now, skip_review=renewed, answered=answered,
                                  daily_schedule=config["runner"]["schedules"].get("builder-daily"))
    logs = Path(config["runner"]["runner"]["logs"]).expanduser() / "runs"
    for role, item, task, why in starts:
        say(f"start {article(role)} {role} run" + (f" on #{item}" if item else "") + f" ({why}): {task}")
        if not dry_run:
            spawn(config, role, item, task, logs)
    for role, item, why, reasons in skipped:
        lines.append(f"held: {article(role)} {role} run" + (f" on #{item}" if item else "") + f" ({why}): {reasons}")
    ok, reasons, warnings = usage.may_start(caps, runs, "coordinator", now, identity["time_zone"])
    window = usage.window_start(runs, now).date().isoformat()
    for w in warnings:
        wanted.append((f"usage-warning:{window}", f"Usage warning: {w}. The system pauses at the cap."))
    if any("weekly points" in r for r in reasons):
        wanted.append((f"usage-cap:{window}", f"The system has reached its weekly cap and is paused: {reasons[0]}."))


    if command == "reconcile":
        claimed = [i["number"] for i in snap["issues"] if plan.CLAIMED in i["labels"]]
        claimed += [p["number"] for p in snap["prs"] if plan.CLAIMED in p["labels"]]
        for n in expired_claims(gh, claimed, active_items, now):
            say(f"release the expired claim on #{n}")
            if not dry_run:
                post.cmd_release(gh, me, n)
        if not dry_run:
            store.append("heartbeats", {"event": "reconcile", "at": now.isoformat()})

    pending = notify.unsent(notices, wanted)
    if pending and not dry_run:
        hook = notify.webhook_url(identity)
        for key, text in pending:
            notify.send(hook, text)
            store.append("notices", {"key": key, "at": now.isoformat()})
    for key, _ in pending:
        say(f"notify the Owner ({key})")
    return lines or ["nothing to do"]


def daily_pass(dry_run, now=None, collect=None):
    """Anomaly signals and the rule audit (blueprint §4.5), each taken to its response once per key. With collect
    (a dict), it also returns what the system audit reports: the findings, the flow records and the runs."""
    now = now or datetime.now(timezone.utc).replace(microsecond=0)
    config = runner.load_all()
    identity = config["identity"]
    gh = post.GitHub(identity["repo"])
    me = ("dispatcher", f"dispatcher-{now:%Y%m%dT%H%M%SZ}")
    store = state.Store(runner.home(config) / "state", f"https://github.com/{identity['repo']}.git")
    runs, raised = store.read("runs"), {a["key"] for a in store.read("anomalies")}
    week = now - timedelta(days=7)
    history = [r for r in runs if datetime.fromisoformat(r["at"]) < week]
    snap = github_state.snapshot(gh, identity)

    closed_at, finished = [], []
    since = (now - timedelta(days=8)).isoformat().replace("+00:00", "Z")
    for i in gh.api("GET", f"repos/{gh.repo}/issues?state=closed&since={since}&per_page=100", paginate=True):
        if "pull_request" not in i and i.get("closed_at") and not any(x["name"].startswith("record:") for x in i["labels"]):
            closed_at.append(datetime.fromisoformat(i["closed_at"].replace("Z", "+00:00")))
            if i.get("state_reason") == "completed":
                finished.append(i)
    flows = store.read("flow")
    have = {r["item"] for r in flows}
    new = [flow.fetch(gh, i, runs, identity["reviewer_app"]["bot_login"], identity["second_login"])
           for i in finished if i["number"] not in have]
    if new and not dry_run:
        store.extend("flow", new)
    flows += new
    waits = [0.0]
    for item in snap["issues"] + [{"number": p["number"], "labels": p["labels"]} for p in snap["prs"]]:
        if "needs-decision:owner" in item["labels"]:
            comments = gh.api("GET", f"repos/{gh.repo}/issues/{item['number']}/comments?per_page=100", paginate=True)
            found = notify.latest_ask(comments, identity, post.MARKER)
            if found and not found[2]:
                asked = datetime.fromisoformat(found[0]["created_at"].replace("Z", "+00:00"))
                waits.append(round((now - asked).total_seconds() / 3600, 1))
    watch = next((i for i in snap["issues"] if "record:watch-list" in i["labels"]), None)

    open_items = {i["number"] for i in snap["issues"] if not any(x.startswith("record:") for x in i["labels"])}
    explained = config["runner"].get("denials", {}).get("explained", [])
    found = (daily.denials(runs, now, explained) +daily.bumpy(runs, now, open_items) + daily.new_failures(runs, now, history)
             + daily.review_rounds(snap["prs"], identity["reviewer_app"]["bot_login"], config["caps"]["wip"]["max_review_rounds"])
             + daily.cost_per_item(runs, now, closed_at) + flow.bottlenecks(flows, now) + flow.idle_waits(flows, now, identity["time_zone"])
             + daily.watch_list(watch["body"] if watch else "", {**daily.metrics(runs, now, max(waits)), **flow.metrics(flows, now)}))
    live = gh.api("GET", f"repos/{gh.repo}/branches/main/protection")
    found += daily.protection_breaches(live, identity["branch_protection"])
    applied, main_commit = runner.commits(config)
    drift = runner.problems(config, applied_commit=applied, main_commit=main_commit,
                            login=runner.claude_login(config), cli=runner.cli_link(config))
    if drift:
        found.append((f"runner:{';'.join(drift)}", "builder", "The runner differs from main",
                      "runner.py check:\n- " + "\n- ".join(drift), None))

    found += audit.missed_builder_daily(runs, now, identity["time_zone"])
    if collect is not None:
        collect.update(findings=[(key, level, title, key not in raised) for key, level, title, _, _ in found], flows=flows, runs=runs)
    lines = []
    for key, level, title, evidence, item in found:
        if key in raised:
            continue
        lines.append(("would raise" if dry_run else "raise") + f" ({level}): {title}")
        if dry_run:
            continue
        body = f"**Anomaly (Dispatcher's daily pass, {now.isoformat()}):** {title}\n\n{evidence}"
        if level == "owner":
            subprocess.run(["gh", "variable", "set", killswitch.VARIABLE, "--body", "true", "--repo", gh.repo],
                           check=True, capture_output=True)
            made = post.cmd_issue_create(gh, me, f"Rule breach: {title}", ["type:system", "sev:1"], body)
            n = int(made.split()[0].lstrip("#"))
            post.cmd_escalate(gh, me, n, "owner", "1. Restore the recorded settings, then resume (`arsys resume`).\n"
                              "2. Keep the new settings: record them in `system/identity.toml` by PR, then resume.\n\n"
                              "Recommended: 1, unless you changed them on purpose.")
        elif level == "coordinator":
            target = item or (watch["number"] if watch else None)
            if target:
                post.cmd_escalate(gh, me, target, "coordinator", body)
        else:
            made = post.cmd_issue_create(gh, me, f"Anomaly: {title}", ["type:system", "state:ready", "sev:3"], body)
            post.cmd_escalate(gh, me, int(made.split()[0].lstrip("#")), "builder", "Respond to this anomaly (blueprint §4.5): fix the cause, "
                              "and add a check and response so a recurrence is handled without you.")
        store.append("anomalies", {"key": key, "level": level, "title": title, "at": now.isoformat()})
    return lines or ["no anomalies"]


def record_issue(gh, me, kind, dry_run):
    """The open record issue an audit's reports go on (created on first use), or None in a dry run before then."""
    label, title = audit.RECORD[kind]
    found = tracker.record_issues(gh, label)
    if found:
        return found[0]
    if dry_run:
        return None
    made = post.cmd_issue_create(gh, me, title, [label], f"Reports of the {kind} audit (system/dispatcher/audit.py), newest "
                                 "last: one comment each, daily at 07:30 and on demand. Each is linked in the Owner's chat.")
    return gh.api("GET", f"repos/{gh.repo}/issues/{made.split()[0].lstrip('#')}")


def product_facts(gh, store, config, record, now):
    identity = config["identity"]
    bot, second = identity["reviewer_app"]["bot_login"], identity["second_login"]
    snap = github_state.snapshot(gh, identity)
    merge_rules.annotate(gh, snap, store.read("runs"), identity, post.MARKER)
    everything = gh.api("GET", f"repos/{gh.repo}/issues?state=open&per_page=100", paginate=True)
    in_review = {n for pr in snap["prs"] for n in pr["resolves"]}
    items = [{"number": i["number"], "title": i["title"], "milestone": (i.get("milestone") or {}).get("title"),
              "state": audit.item_state({x["name"] for x in i["labels"]}, i["number"] in in_review)}
             for i in everything if "pull_request" not in i and i.get("milestone")]
    questions = []
    for i in snap["issues"] + snap["prs"]:
        if "needs-decision:owner" in i["labels"]:
            found = notify.latest_ask(gh.api("GET", f"repos/{gh.repo}/issues/{i['number']}/comments?per_page=100", paginate=True),
                                      identity, post.MARKER)
            if found and not found[2]:
                questions.append((i["number"], i["title"], datetime.fromisoformat(found[0]["created_at"].replace("Z", "+00:00"))))
    approvals = [(pr["number"], pr["title"]) for pr in snap["prs"]
                 if pr["author_role"] and not pr["draft"] and pr["protected"] and pr["gate"] == "SUCCESS"
                 and merge_rules.current(pr, bot) and not merge_rules.owner_approves(pr, second)
                 and not merge_rules.sr2_due(pr, bot, second)]
    last = gh.api("GET", f"repos/{gh.repo}/issues/{record['number']}/comments?per_page=100", paginate=True) if record else []
    since = max((c["created_at"] for c in last), default=(now - timedelta(hours=12)).isoformat().replace("+00:00", "Z"))
    merged = [(p["number"], p["title"]) for p in gh.api("GET", f"repos/{gh.repo}/pulls?state=closed&sort=updated&direction=desc&per_page=50")
              if p.get("merged_at") and p["merged_at"] > since]
    milestones = [{"title": m["title"], "open": m["open_issues"], "closed": m["closed_issues"]}
                  for m in gh.api("GET", f"repos/{gh.repo}/milestones?state=all&per_page=100", paginate=True)]
    watch = next((i for i in snap["issues"] if "record:watch-list" in i["labels"]), None)
    note = next((line for line in post.MARKER.sub("", (watch or {}).get("body") or "", count=1).splitlines() if line.strip()), "")
    return {"goals": sorted((i for i in snap["issues"] if "record:goal" in i["labels"]), key=lambda i: i["title"]),
            "deadlines": audit.deadlines(github_state.requirements_on_main(gh)), "milestones": milestones, "items": items,
            "questions": questions, "approvals": approvals, "merged": merged, "gate": post.cmd_gate(gh, identity, "main"),
            "watch": (watch["number"], note[:400] + ("…" if len(note) > 400 else "")) if watch else None}


def system_facts(gh, store, config, collect, now):
    identity, zone = config["identity"], config["identity"]["time_zone"]
    runs = collect["runs"]
    everything = gh.api("GET", f"repos/{gh.repo}/issues?state=open&labels=type%3Asystem&per_page=100", paginate=True)
    open_system = [(i["number"], i["title"], next((x["name"] for x in i["labels"] if x["name"].startswith("sev:")), "sev:?"))
                   for i in everything if "pull_request" not in i]
    _, reasons, warnings = usage.may_start(config["caps"], runs, "coordinator", now, zone)
    beats = [datetime.fromisoformat(b["at"]) for b in store.read("heartbeats") if b.get("event") == "reconcile"]
    return {"findings": collect["findings"], "open_system": open_system, "flow": flow.report(collect["flows"], now, 7, zone),
            "paused": killswitch.paused(gh), "runs": audit.runs_summary(runs, now),
            "usage": (warnings, [r for r in reasons if "points" in r]), "last_reconcile": max(beats, default=None),
            "builder_daily": audit.builder_daily(runs)}


def audit_pass(kinds=audit.KINDS, dry_run=False, now=None, announce=True):
    """The product and system audits: each posted on its record issue; with announce, one notice in the Owner's chat.
    Returns (lines, [(kind, headline, url)])."""
    now = now or datetime.now(timezone.utc).replace(microsecond=0)
    config = runner.load_all()
    identity = config["identity"]
    gh = post.GitHub(identity["repo"])
    me = ("dispatcher", f"dispatcher-{now:%Y%m%dT%H%M%SZ}")
    store = state.Store(runner.home(config) / "state", f"https://github.com/{identity['repo']}.git")
    lines, posted = [], []
    for kind in kinds:
        record = record_issue(gh, me, kind, dry_run)
        if kind == "system":
            collect = {}
            lines += daily_pass(dry_run, now, collect)
            headline, body = audit.system_report(system_facts(gh, store, config, collect, now), now, identity["time_zone"])
        else:
            headline, body = audit.product_report(product_facts(gh, store, config, record, now), now, identity["time_zone"])
        if dry_run:
            lines += [f"would post the {kind} audit: {headline}", body]
            continue
        url = post.cmd_comment(gh, me, record["number"], body)
        lines.append(f"posted the {kind} audit: {headline} ({url})")
        posted.append((kind, headline, url))
    if posted and announce:
        notify.send(notify.webhook_url(identity), "\n".join(f"**{k.capitalize()} audit:** {h}\n<{u}>" for k, h, u in posted))
    return lines, posted


def crash_notice(command, error, now, zone):
    """The Owner's notice for a pass that raised (#638): keyed by the day, so one a day while passes keep failing."""
    local = now.astimezone(ZoneInfo(zone))
    first = (str(error).strip().splitlines() or [""])[0][:300]
    return (f"crash:{local:%Y-%m-%d}",
            f"**The Dispatcher's {command} pass failed** at {local:%Y-%m-%d %H:%M %Z}: {type(error).__name__}: {first}\n"
            f"Until a pass succeeds, no runs start, nothing merges, and no questions or audits reach you. "
            f"The builder's daily run looks into it. This notice comes once a day while it lasts.")


def report_crash(command, error, now=None):
    """Tell the Owner that a pass raised, once a day (#638): a crashed poll can't send its own notices or escalations.
    Never raises, so the pass's own error stays the one reported. If the state branch can't be read to see whether
    today's notice went, only the 07:30 audit pass sends it, which is still once a day."""
    now = now or datetime.now(timezone.utc).replace(microsecond=0)
    try:
        config = runner.load_all()
        identity = config["identity"]
        key, text = crash_notice(command, error, now, identity["time_zone"])
        store = state.Store(runner.home(config) / "state", f"https://github.com/{identity['repo']}.git")
        try:
            pending = notify.unsent(store.read("notices"), [(key, text)])
        except (Exception, SystemExit):
            store, pending = None, [(key, text + " The state branch can't be read either.")] if command == "audit" else []
        for key, text in pending:
            notify.send(notify.webhook_url(identity), text)
            if store:
                store.append("notices", {"key": key, "at": now.isoformat()})
        return [f"notify the Owner ({key})" for key, _ in pending]
    except (Exception, SystemExit) as e:  # no secret named: the webhook's URL is never in these errors
        return [f"crash notice failed: {type(e).__name__}: {e}"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["poll", "reconcile", "daily", "audit"])
    parser.add_argument("kind", nargs="?", choices=["product", "system", "all"], default="all", help="audit only")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")
    try:
        return run_pass(args, stamp)
    except (Exception, SystemExit) as e:
        # GitHub's errors are SystemExit. A dry run only prints; a pass that raised still exits 1 after the notice.
        if not args.dry_run and not (isinstance(e, SystemExit) and e.code in (0, None)):
            for line in report_crash(args.command, e):
                print(f"{stamp} {args.command}: {line}", file=sys.stderr)
        raise


def run_pass(args, stamp):
    if args.command == "audit":
        for line in audit_pass(audit.KINDS if args.kind == "all" else (args.kind,), args.dry_run)[0]:
            print(f"{stamp} audit: {line}")
        return 0
    if args.command == "daily":
        thrown, why = killswitch.paused(post.GitHub(runner.load_all()["identity"]["repo"]))
        if thrown:  # the audit still runs while paused: a breach must reach the Owner
            print(f"{stamp} daily: paused ({why}); auditing anyway")
        for line in daily_pass(args.dry_run):
            print(f"{stamp} daily: {line}")
        return 0
    for line in dispatch_pass(args.command, args.dry_run):
        print(f"{stamp} {args.command}: {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
