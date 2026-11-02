"""The merge queue and the standing rules' checks (system/standing-rules.md): which approvals count, and what merges.

The Dispatcher calls `annotate` to fill in what these checks read from GitHub, then `merge_plan`, and carries out its
actions. SR1 never covers a change to this file: the Owner merges it (blueprint §6). Standard library only.
"""

import re
from datetime import datetime

UP_TO_DATE = ("CLEAN", "BLOCKED", "HAS_HOOKS", "UNSTABLE")


def latest_review(pr, login):
    reviews = [r for r in pr["reviews"] if r["login"] == login and r["state"] in ("APPROVED", "CHANGES_REQUESTED")]
    return reviews[-1] if reviews else None


# Standing rule SR1 (system/standing-rules.md) never covers a change to the standing rules or to this file.
SR1_EXCLUDED = ("system/standing-rules.md", "system/dispatcher/merge_rules.py")


def current(pr, login):
    """Whether login's latest review approves the PR as it is: its head, or a commit at which the PR's own changes
    were what they are at the head (`pr["fresh"]`, filled in by `annotate`). A
    conflict-free refresh keeps an approval; any other push doesn't (#118, #127). GitHub no longer dismisses stale
    approvals, so this is the check."""
    r = latest_review(pr, login)
    return r is not None and r["state"] == "APPROVED" and (r["commit"] == pr["head"] or (pr.get("fresh") or {}).get(login, False))


# Standing rule SR2 (#150): others may judge that the Owner's approval of an earlier commit still covers a PR. Its own
# added and removed lines unchanged, only the code around them: the Coordinator, then the builder. Its own lines
# changed: the builder, unless it wrote the PR. Then the Owner.
SR2_LABELS = {"needs-decision:coordinator", "needs-decision:builder", "needs-decision:owner"}
SIGN_OFF = re.compile(r"^\*\*SR2 sign-off:\*\* the Owner's approval of `(?P<approved>[0-9a-f]{40})` covers `(?P<head>[0-9a-f]{40})`")


def own_lines(changes):
    """A PR's own changes (`dispatch.own_changes`) reduced to its added and removed lines, in order, file by file.
    A file compared by its blob stays so."""
    return {f: (status, tuple(line for line in v.splitlines() if line[:1] in "+-") if isinstance(v, str) and v.startswith("@@") else v)
            for f, (status, v) in changes.items()}


def sr2_signers(pr):
    """Who may sign off on this PR under SR2 (`pr["same_lines"]`, filled in by the Dispatcher). The builder never
    judges its own changes in the Owner's place. Nobody, if the Dispatcher didn't compare the lines."""
    if "same_lines" not in pr:
        return ()
    if pr["same_lines"]:
        return ("coordinator", "builder")
    return () if pr["author_role"] == "builder" else ("builder",)


def signed_off(pr, comments, runs, identity, marker):
    """The commit up to which an SR2 sign-off says the Owner's latest approval covers the PR, or None. Only a sign-off
    posted through post.py by a run of a role that may sign off on this PR (`sr2_signers`), recorded on this PR by the
    Dispatcher, counts, and only one naming the commit the Owner approved."""
    owner = latest_review(pr, identity["second_login"])
    signers = sr2_signers(pr)
    if not owner or owner["state"] != "APPROVED" or not signers:
        return None
    recorded = {(r["run_id"], r["role"]) for r in runs if r["event"] == "start" and r.get("item") == pr["number"]}
    covered = None
    for c in comments:
        body = c.get("body") or ""
        m = marker.match(body)
        # Only straight after the marker, where `post.py sign-off` writes it: a quoted sign-off line doesn't count.
        s = m and SIGN_OFF.match(body[m.end():].lstrip("\n"))
        if (c["user"]["login"] == identity["owner_login"] and m and s and m["role"] in signers
                and (m["run"], m["role"]) in recorded and s["approved"] == owner["commit"]):
            covered = s["head"]
    return covered


# Standing rule SR3 (#221): the builder approves a protected PR in the Owner's place, except a change to these. The
# Owner kept the blueprint, the requirements and caps (a script can't tell a raise from a cut); blueprint §6 keeps the
# standing rules, this check and what it enforces (§5: the branch protection recorded, the protected paths).
SR3_EXCLUDED = SR1_EXCLUDED + ("blueprint.md", "project_requirements.md", "system/caps.toml", "system/identity.toml",
                               ".github/CODEOWNERS")
SR3_APPROVAL = re.compile(r"^\*\*SR3 approval:\*\* the builder approves `(?P<head>[0-9a-f]{40})` in the Owner's place")


def sr3_covers(pr):
    return pr["protected"] and not any(f in SR3_EXCLUDED for f in pr["files"])


def builder_approved(pr, comments, runs, identity, marker):
    """The commit the latest SR3 approval on this PR names, or None. Only an approval posted through post.py by a
    builder run the Dispatcher recorded on this PR counts, and only from a run that started after the Reviewer App's
    latest approval: never the run that wrote it (the Owner's "other builder"). A commit's date is whatever its writer
    set, so the time is GitHub's: a run that wrote a commit started before it was pushed, so before the Reviewer
    approved it, and a later push of the PR's own needs the Reviewer again."""
    review = latest_review(pr, identity["reviewer_app"]["bot_login"])
    if not sr3_covers(pr) or not review or review["state"] != "APPROVED" or not review.get("at"):
        return None
    reviewed = datetime.fromisoformat(review["at"].replace("Z", "+00:00"))
    started = {r["run_id"]: datetime.fromisoformat(r["at"]) for r in runs
               if r["event"] == "start" and r["role"] == "builder" and r.get("item") == pr["number"] and r.get("at")}
    covered = None
    for c in comments:
        body = c.get("body") or ""
        m = marker.match(body)
        # Only straight after the marker, where `post.py builder-approve` writes it: a quoted line doesn't count.
        s = m and SR3_APPROVAL.match(body[m.end():].lstrip("\n"))
        if (c["user"]["login"] == identity["owner_login"] and m and s and m["role"] == "builder"
                and m["run"] in started and started[m["run"]] > reviewed):
            covered = s["head"]
    return covered


def owner_approves(pr, second):
    """The Owner's approval covers the PR as it is: current itself, carried to a later commit by an SR2 sign-off
    (`pr["sign_off"]`), or given by the builder under SR3 (`pr["builder_approval"]`), each followed by no more than
    a conflict-free refresh (`pr["fresh"]["sign-off"]`, `pr["fresh"]["sr3"]`)."""
    fresh = pr.get("fresh") or {}
    covers = lambda sha, key: bool(sha and (sha == pr["head"] or fresh.get(key)))
    return (current(pr, second) or covers(pr.get("sign_off"), "sign-off")
            or (sr3_covers(pr) and covers(pr.get("builder_approval"), "sr3")))


def sr2_due(pr, bot, second):
    """SR2's checkable conditions hold and only the judgment is missing: green, protected, outside SR1's exclusions,
    the Reviewer's approval current, the Owner's approval on an earlier commit, someone who may sign off on it
    (`sr2_signers`), and no sign-off covering it yet. A PR SR3 covers goes to SR3 instead."""
    owner = latest_review(pr, second)
    return (pr["protected"] and pr["gate"] == "SUCCESS" and not any(f in SR1_EXCLUDED for f in pr["files"])
            and not sr3_covers(pr)
            and current(pr, bot) and owner is not None and owner["state"] == "APPROVED"
            and bool(sr2_signers(pr)) and not owner_approves(pr, second))


def sr3_due(pr, bot, second):
    """SR3's checkable conditions hold and only the builder's judgment is missing: green, outside SR3's exclusions,
    the Reviewer's approval current, and no approval of the Owner's or the builder's covering it."""
    return sr3_covers(pr) and pr["gate"] == "SUCCESS" and current(pr, bot) and not owner_approves(pr, second)


def sr1(pr, bot, second):
    """SR1: a protected PR merges on its own once the Reviewer App and the Owner's code-owner account have both
    approved it as it is (#116, #118), SR2 carried the Owner's approval to it (#150), or the builder approved it under
    SR3 (#221), unless it changes the standing rules or this check."""
    return current(pr, bot) and owner_approves(pr, second) and not any(f in SR1_EXCLUDED for f in pr["files"])


def merge_plan(snap, identity):
    """Merge-queue actions: ('refresh'|'auto-merge'|'cancel-auto-merge'|'ask-owner-to-merge'|'ask-owner-to-approve'|
    'renew'|'ask-owner-to-reapprove'|'ask-coordinator-to-sign-off'|'ask-builder-to-sign-off'|'ask-builder-to-approve',
    pr, detail)."""
    bot, second = identity["reviewer_app"]["bot_login"], identity["second_login"]
    prs = [pr for pr in snap["prs"] if pr["author_role"] and not pr["draft"]]
    actions = []
    # Auto-merge on, but the approvals no longer cover the PR as it is (real changes were pushed): turn it off,
    # since GitHub keeps stale approvals now (#118).
    stale = [pr for pr in prs if pr["auto_merge"] and not (current(pr, bot) and (not pr["protected"] or owner_approves(pr, second)))]
    actions += [("cancel-auto-merge", pr["number"], pr["head"]) for pr in stale]
    in_flight = [pr for pr in prs if pr["auto_merge"] and pr not in stale]

    def awaiting_owner(pr):
        # Protected, green, the Reviewer App's approval current: only the Owner's approval is missing.
        return pr["protected"] and pr["gate"] == "SUCCESS" and current(pr, bot)

    def needs_owner(pr):
        # Protected and not mergeable under SR1: it waits for the Owner, so it goes behind the PRs that can merge (#127).
        return pr["protected"] and not sr1(pr, bot, second)

    ready = sorted(
        (pr for pr in prs if pr["gate"] == "SUCCESS" and current(pr, bot) and (pr["review_decision"] == "APPROVED" or awaiting_owner(pr))),
        key=lambda pr: (needs_owner(pr), pr["number"]),
    )
    queue = in_flight or ready
    if queue:
        nxt = queue[0]
        if nxt["merge_state"] == "BEHIND":
            actions.append(("refresh", nxt["number"], "behind main"))
        elif nxt["merge_state"] in ("CLEAN", "HAS_HOOKS") and not nxt["auto_merge"] and nxt["review_decision"] == "APPROVED":
            if not needs_owner(nxt):
                actions.append(("auto-merge", nxt["number"], nxt["head"]))
            elif owner_approves(nxt, second):  # current approvals, but a path SR1 leaves to the Owner
                actions.append(("ask-owner-to-merge", nxt["number"], nxt["head"]))
            # Otherwise the Owner's approval isn't current: the loop below asks for a sign-off or a re-approval.
    for pr in prs:
        if pr["gate"] != "SUCCESS":
            continue
        app, owner = latest_review(pr, bot), latest_review(pr, second)
        # GitHub keeps stale approvals now, so APPROVED alone no longer means there's nothing to ask (#127).
        if pr["review_decision"] == "APPROVED" and current(pr, bot) and (not pr["protected"] or owner_approves(pr, second)):
            continue
        if pr["review_decision"] != "APPROVED" and app and app["state"] == "APPROVED" and app["commit"] != pr["head"]:
            actions.append(("renew", pr["number"], app["commit"]))
        if sr2_due(pr, bot, second):
            # The first who may sign off judges, then the next, then the Owner (#150). Behind main too: a sign-off
            # survives the refresh that the PR gets when the queue reaches it.
            if pr["merge_state"] in UP_TO_DATE + ("BEHIND",) and not pr["labels"] & SR2_LABELS:
                actions.append((f"ask-{sr2_signers(pr)[0]}-to-sign-off", pr["number"], owner["commit"]))
        elif sr3_due(pr, bot, second):
            # The builder judges in the Owner's place, and escalates what it can't (#221).
            if pr["merge_state"] in UP_TO_DATE + ("BEHIND",) and not pr["labels"] & SR2_LABELS:
                actions.append(("ask-builder-to-approve", pr["number"], pr["head"]))
        elif pr["protected"] and pr["merge_state"] in UP_TO_DATE:
            # Ask the Owner only about a PR GitHub reports as up to date: one behind main would be refreshed,
            # and GitHub reports UNKNOWN for a moment after main moves.
            if owner and owner["state"] == "APPROVED" and not owner_approves(pr, second):
                actions.append(("ask-owner-to-reapprove", pr["number"], pr["head"]))
            elif current(pr, bot) and not owner:
                actions.append(("ask-owner-to-approve", pr["number"], pr["head"]))
    return actions


HUNK_LINE_NUMBERS = re.compile(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@", re.M)


def own_changes(gh, ref):
    """A commit's diff against its merge base with main, file by file: a PR's own changes. Each patch is kept whole
    and in order, context included, less the line numbers in its hunk headers, so main adding or removing lines
    elsewhere only shifts it. A file without a patch (binary, or too large to show) is compared by its blob.
    None for a commit that shares no history with main, as after a rewrite of main's history: it has no own changes
    to compare, and one such PR mustn't stop the whole pass (#635)."""
    try:
        files = gh.api("GET", f"repos/{gh.repo}/compare/main...{ref}")["files"]
    except SystemExit as e:
        if "No common ancestor" in str(e):
            return None
        raise
    return {f["filename"]: (f["status"], HUNK_LINE_NUMBERS.sub("@@", f["patch"]))
            if f.get("patch") is not None else (f["status"], f.get("sha")) for f in files}


def same_changes(gh, approved, head):
    """True when the PR's own changes at head are what they were at the approved commit: everything since came from
    main. A merge that resolved a conflict by hand, or any commit of the PR's own, changes them (#118, #127). So
    does main editing a line next to one of them: that errs toward asking for a re-approval.
    (Comparing commits instead fails: the commits merged in from main include other PRs' own commits.)
    False when either shares no history with main."""
    before = own_changes(gh, approved)
    return before is not None and before == own_changes(gh, head)


def annotate(gh, snap, runs, identity, marker):
    """Fill in what the checks above read from GitHub, on each PR: `fresh` (an approval followed only by merges from
    main still counts, #118), `same_lines` and `sign_off` (SR2, #150), and `builder_approval` (SR3, #221)."""
    bot, second = identity["reviewer_app"]["bot_login"], identity["second_login"]
    for pr in snap["prs"]:
        pr["fresh"] = {}
        for login in (bot, second):
            r = latest_review(pr, login)
            if r and r["state"] == "APPROVED" and r["commit"] and r["commit"] != pr["head"]:
                approved, head = own_changes(gh, r["commit"]), own_changes(gh, pr["head"])
                pr["fresh"][login] = approved is not None and approved == head
                if None in (approved, head):
                    continue  # nothing to compare: no SR2 sign-off can carry the approval either
                if login == second and pr["protected"] and not pr["fresh"][login]:
                    # SR2: a sign-off may carry the approval, from whoever may judge this kind of change.
                    pr["same_lines"] = own_lines(approved) == own_lines(head)
                    if sr2_signers(pr):
                        comments = gh.api("GET", f"repos/{gh.repo}/issues/{pr['number']}/comments?per_page=100", paginate=True)
                        pr["sign_off"] = signed_off(pr, comments, runs, identity, marker)
                        if pr["sign_off"] and pr["sign_off"] != pr["head"]:
                            pr["fresh"]["sign-off"] = same_changes(gh, pr["sign_off"], pr["head"])
        # SR3: only for a PR waiting on the Owner's approval, since the Reviewer's approval is current.
        if sr3_covers(pr) and pr["gate"] == "SUCCESS" and current(pr, bot) and not owner_approves(pr, second):
            comments = gh.api("GET", f"repos/{gh.repo}/issues/{pr['number']}/comments?per_page=100", paginate=True)
            pr["builder_approval"] = builder_approved(pr, comments, runs, identity, marker)
            if pr["builder_approval"] and pr["builder_approval"] != pr["head"]:
                pr["fresh"]["sr3"] = same_changes(gh, pr["builder_approval"], pr["head"])
