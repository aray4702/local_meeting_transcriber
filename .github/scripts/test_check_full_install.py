"""Tests for the full-install sequence (4b1 and 4b2), on a fake `lmt`.

Run: python3 -I -m unittest discover -s .github/scripts -t .github/scripts
"""

import contextlib
import errno
import io
import json
import os
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_full_install as cfi

TOKEN = "abcdefghijklmnopqrstuv"  # 22 characters, as the demo's URL has
# Stands in for the installed lmt. It appends its argv, cwd and environment to FAKE_LMT_LOG, and
# FAKE_LMT_MODE (comma-separated) picks its faults.
FAKE_LMT = f'TOKEN = "{TOKEN}"\n' + r'''
import http.server, json, os, signal, socketserver, sys, time
from pathlib import Path

modes = os.environ.get("FAKE_LMT_MODE", "").split(",")
keys = ("HOME", "TMPDIR", "XDG_CACHE_HOME", "LMT_CACHE_DIR", "LMT_DATA_DIR", "HF_TOKEN",
        "PYTHONPATH", "LMT_NETGUARD_ALLOW", "LMT_NETGUARD_LOG")
with open(os.environ["FAKE_LMT_LOG"], "a") as f:
    f.write(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd(), "pid": os.getpid(),
                        "env": {k: os.environ.get(k) for k in keys}}) + "\n")
cache, data = Path(os.environ["LMT_CACHE_DIR"]), Path(os.environ["LMT_DATA_DIR"])

if sys.argv[1:] == ["models", "download"]:
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "model.bin").write_bytes(b"weights")
    sys.exit(1 if "download-fails" in modes else 0)

if sys.argv[1:2] == ["transcribe"] and sys.argv[3:6] == ["-f", "txt,srt,vtt,json", "-o"]:
    out = Path(sys.argv[6])
    for ext in ("txt", "srt", "vtt", "json"):
        (out / f"two_speakers.{ext}").write_text(f"placeholder {ext}\n")
    if "guard-line" in modes:
        with open(os.environ["LMT_NETGUARD_LOG"], "a") as f:
            f.write("connect ('203.0.113.7', 443)\n")
    if "transcribe-hangs" in modes:
        time.sleep(60)
    sys.exit(0)

if sys.argv[1:2] == ["rename"] and len(sys.argv) == 4:
    sys.exit(0)

if sys.argv[1:] == ["demo", "--sample", "--no-browser"]:
    (data / "derived" / "AMI-ci").mkdir(parents=True, exist_ok=True)
    (data / "derived" / "AMI-ci" / "ES2004a.wav").write_bytes(b"RIFF....WAVE")
    (data / "sample" / "0123456789abcdef").mkdir(parents=True, exist_ok=True)
    # "retranscribe": every run writes a new transcript, as if the second run didn't serve the cache
    (data / "sample" / "0123456789abcdef" / "ES2004a.json").write_text(
        str(time.time_ns()) if "retranscribe" in modes else "{}")
    if "write-home" in modes:
        Path(os.environ["HOME"], ".lmtrc").write_text("x")
    if "write-models" in modes:
        (cache / "late.bin").write_bytes(b"late")
    if "no-url" in modes:
        while True:
            time.sleep(1)

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = {f"/{TOKEN}/": b"<!doctype html>", f"/{TOKEN}/audio.wav": b"RIFF\0\0\0\0WAVE"}.get(self.path)
            self.send_response(200 if body else 404)
            self.end_headers()
            self.wfile.write(body or b"")

        def log_message(self, *args):
            pass

    def stop(*_):  # at once: no interpreter teardown of the server's threads, which a slow runner stalls in (#573)
        os._exit(3 if "exit-3" in modes else 0)

    class Server(http.server.ThreadingHTTPServer):
        def server_bind(self):  # without HTTPServer's socket.getfqdn, which waits out resolver timeouts on macos-26 (#641)
            socketserver.TCPServer.server_bind(self)
            self.server_name, self.server_port = self.server_address[:2]

    signal.signal(signal.SIGTERM, signal.SIG_IGN if "ignore-term" in modes else stop)
    server = Server(("127.0.0.1", 0), Handler)
    print(f"http://127.0.0.1:{server.server_address[1]}/{TOKEN}/", flush=True)
    server.serve_forever()

sys.exit(2)
'''


class Fake:
    """A work directory, a fake lmt and its log."""

    def __init__(self, tmp, modes=()):
        self.tmp = Path(tmp)
        self.work = self.tmp / "work"
        self.log = self.tmp / "lmt.log"
        self.lmt = self.tmp / "bin" / "lmt"
        self.lmt.parent.mkdir()
        self.lmt.write_text(f"#!{sys.executable} -I\n{FAKE_LMT}")
        self.lmt.chmod(0o755)
        self.env = {"FAKE_LMT_LOG": str(self.log), "FAKE_LMT_MODE": ",".join(modes),
                    "HF_TOKEN": "fake-token-for-the-test"}
        self.probe = OSError(errno.ENETUNREACH, "Network is unreachable")  # raised, or else returned
        self.probed = []  # the addresses the phase's probe connected to
        self.checked = []  # (check, path) for each stubbed subtitle check
        self.phase_argv = None

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def in_process_phase(self, argv):
        """The offline phase as a call rather than a process, so its stubs apply: its exit code."""
        self.phase_argv = argv
        return cfi.main(argv[argv.index("offline"):])

    def stubs(self):
        real_connect = socket.create_connection

        def connect(address, timeout=None, *rest):
            if address != cfi.PROBE:  # http.client's fetches from the demo
                return real_connect(address, timeout, *rest)
            self.probed.append((address, timeout))
            if isinstance(self.probe, BaseException):
                raise self.probe
            return self.probe

        def check_srt(path):
            self.checked.append(("srt", path))

        def check_vtt(path):
            self.checked.append(("vtt", path))

        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.object(cfi.socket, "create_connection", connect))
        stack.enter_context(mock.patch.object(cfi, "subtitle_checkers", lambda: (check_srt, check_vtt)))
        return stack

    def main(self, *extra, platform="linux-x86_64", phase=None):
        """main() on the fake, quietly, with the offline phase run by `phase(argv)` (in process by
        default): (exit code, its stdout)."""
        out = io.StringIO()
        env = dict(self.env, GITHUB_STEP_SUMMARY=str(self.tmp / "summary.md"))
        with mock.patch.dict(os.environ, env), contextlib.redirect_stdout(out), self.stubs(), \
                mock.patch.object(cfi, "run_phase", phase or self.in_process_phase):
            code = cfi.main(["--lmt", str(self.lmt), "--platform", platform, "--work", str(self.work), *extra])
        return code, out.getvalue()


class FakeTest(unittest.TestCase):
    modes = ()

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.fake = Fake(tmp.name, self.modes)

    def fake_with(self, *modes):
        self.fake.env["FAKE_LMT_MODE"] = ",".join(modes)
        return self.fake

    def assert_gone(self, pid):
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)


class OnlineOrderTest(FakeTest):
    def test_a_passing_run(self):
        code, out = self.fake.main()
        self.assertEqual(code, 0, out)
        work = self.fake.work.resolve()
        self.assertEqual([c["argv"] for c in self.fake.calls()], [
            ["models", "download"], ["demo", "--sample", "--no-browser"],
            ["transcribe", str(cfi.FIXTURE), "-f", "txt,srt,vtt,json", "-o", str(work / "out")],
            ["rename", str(work / "out" / "two_speakers.json"), "S1=José & Ana"],
            ["demo", "--sample", "--no-browser"]])
        self.assertEqual([line.split()[:2] for line in out.splitlines()],
                         [["PASS", s] for s in ("1.1", "1.2", "1.3", "2.1", "2.2", "2.3", "2.4", "2.5")])
        summary = (self.fake.tmp / "summary.md").read_text()
        for step in ("PASS 1.1 models download", "PASS 1.2 snapshot <work>/models", "PASS 1.3 the first --sample run",
                     "PASS 2.1 the cut is real", "PASS 2.2 offline transcribe", "PASS 2.3 offline rename",
                     "PASS 2.4 the second --sample run", "PASS 2.5 the guard's log"):
            self.assertIn(step, summary)

    def test_a_failed_step_fails_the_rest(self):
        code, out = self.fake_with("download-fails").main()
        self.assertEqual(code, 1)
        self.assertEqual([c["argv"] for c in self.fake.calls()], [["models", "download"]])
        self.assertIsNone(self.fake.phase_argv)  # the offline phase doesn't start
        self.assertIn("lmt models download exits 1", out)
        self.assertIn("FAIL 1.3 the first --sample run\n  - not reached: step 1.1 failed", out)
        self.assertIn("FAIL 2.5 the guard's log\n  - not reached: step 1.1 failed", out)


class RunDemoTest(FakeTest):
    def first_sample(self):
        """Step 1.3 alone, after 1.1 and 1.2: its problem, or None."""
        args = mock.Mock(lmt=self.fake.lmt, work=self.fake.work)
        with mock.patch.dict(os.environ, self.fake.env):
            cfi.step_models_download(args)
            cfi.step_snapshot_models(args)
            try:
                cfi.step_first_sample(args)
            except cfi.StepFailed as e:
                return str(e)
        return None

    def test_passes(self):
        self.assertIsNone(self.first_sample())

    def test_no_url_within_the_limit(self):
        self.fake_with("no-url")
        with mock.patch.object(cfi, "FIRST_URL_LIMIT", 1):
            self.assertEqual(self.first_sample(), "no URL on stdout within the 1 s limit")
        self.assert_gone(self.fake.calls()[-1]["pid"])

    def test_ignores_sigterm(self):
        self.fake_with("ignore-term")
        with mock.patch.object(cfi, "FETCH_LIMIT", 1):
            self.assertEqual(self.first_sample(), "still running 1 s after SIGTERM (the limit)")
        self.assert_gone(self.fake.calls()[-1]["pid"])

    def test_exit_code_other_than_0(self):
        self.fake_with("exit-3")
        self.assertEqual(self.first_sample(), "exits 3 after SIGTERM, not 0")

    def test_a_file_outside_lmt_data_dir(self):
        self.fake_with("write-home")
        self.assertIn("the run's fresh home directory isn't empty", self.first_sample())

    def test_models_written_after_the_snapshot(self):
        self.fake_with("write-models")
        problem = self.first_sample()
        self.assertTrue(problem.startswith("<work>/models changed: "), problem)
        self.assertIn("late.bin", problem)

    def test_the_fake_binds_without_a_reverse_lookup(self):
        # #641: HTTPServer.server_bind's socket.getfqdn waited out resolver timeouts on macos-26, ~45 s a test,
        # as it did for lmt's own server (#521). The fake runs with getfqdn made to exit before the URL.
        wrapper = ("import runpy, socket, sys\n"
                   "def getfqdn(*args):\n"
                   "    sys.exit('socket.getfqdn called')\n"
                   "socket.getfqdn = getfqdn\n"
                   "sys.argv = sys.argv[1:]\n"
                   "runpy.run_path(sys.argv[0], run_name='__main__')\n")
        dirs = cfi.fresh_dirs(self.fake.work, "demo")
        env = dict(cfi.command_env(self.fake.work, dirs), **self.fake.env)
        cfi.run_demo([sys.executable, "-I", "-c", wrapper, str(self.fake.lmt), "demo", "--sample", "--no-browser"],
                     env, dirs["cwd"], 10)


class DirectoriesTest(FakeTest):
    def test_models_snapshot_is_written_after_the_download(self):
        code, out = self.fake.main()
        self.assertEqual(code, 0, out)
        models = self.fake.work.resolve() / "models"
        saved = json.loads((self.fake.work / "snapshots" / "models.json").read_text())
        self.assertEqual(saved, cfi.snapshot(models))
        self.assertIn(str(models / "model.bin"), saved)

    def test_no_snapshot_when_the_download_fails(self):
        self.fake_with("download-fails").main()
        self.assertFalse((self.fake.work / "snapshots" / "models.json").exists())

    def test_each_command_has_fresh_directories_and_only_download_has_hf_token(self):
        code, out = self.fake.main()
        self.assertEqual(code, 0, out)
        work = self.fake.work.resolve()
        calls = self.fake.calls()
        seen = set()
        steps = ("models-download", "sample-online", "transcribe", "rename", "sample-offline")
        self.assertEqual(len(calls), len(steps))
        for call, step in zip(calls, steps):
            run = work / "runs" / step
            env = call["env"]
            self.assertEqual([env["HOME"], env["TMPDIR"], env["XDG_CACHE_HOME"]],
                             [str(run / "home"), str(run / "tmp"), str(run / "cache")])
            self.assertEqual(os.path.realpath(call["cwd"]), os.path.realpath(run / "cwd"))
            self.assertEqual([env["LMT_CACHE_DIR"], env["LMT_DATA_DIR"]], [str(work / "models"), str(work / "data")])
            seen |= {env["HOME"], env["TMPDIR"], env["XDG_CACHE_HOME"], call["cwd"]}
        self.assertEqual(len(seen), 4 * len(steps))
        self.assertEqual([c["env"]["HF_TOKEN"] for c in calls], ["fake-token-for-the-test", None, None, None, None])

    def test_only_offline_commands_have_the_guard(self):
        code, out = self.fake.main()
        self.assertEqual(code, 0, out)
        guard = [(c["env"]["PYTHONPATH"], c["env"]["LMT_NETGUARD_ALLOW"], c["env"]["LMT_NETGUARD_LOG"])
                 for c in self.fake.calls()]
        on = (str(cfi.CHECKOUT / "tests" / "netguard"), "127.0.0.1", str(self.fake.work.resolve() / "netguard.log"))
        self.assertEqual(guard[2:], [on] * 3)
        for env in guard[:2]:
            self.assertNotEqual(env[1:], on[1:])

    def test_snapshot_kinds(self):
        root = self.fake.tmp / "snap"
        (root / "d").mkdir(parents=True)
        (root / "d" / "f").write_bytes(b"abc")
        (root / "l").symlink_to("d/f")
        self.assertEqual(cfi.snapshot(root), {
            str(root / "d"): ["dir"],
            str(root / "d" / "f"): ["file", 3, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"],
            str(root / "l"): ["link", "d/f"],
        })


class OfflineCommandTest(unittest.TestCase):
    def test_argv_for_both_platforms(self):
        script = str(Path(cfi.__file__).resolve())
        phase = ["env", "-i", "HOME=/w/runs/offline/home", "PATH=/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE=1",
                 sys.executable, "-I", script, "offline",
                 "--lmt", "/s/bin/lmt", "--platform", "{platform}", "--work", "/w"]
        with mock.patch.object(cfi.subprocess, "run") as run, mock.patch.object(cfi.subprocess, "Popen") as popen:
            linux = cfi.offline_command("/s/bin/lmt", "linux-x86_64", "/w", path="/usr/bin:/bin", uid=1001, gid=118)
            macos = cfi.offline_command("/s/bin/lmt", "macos-arm64", "/w", path="/usr/bin:/bin")
        run.assert_not_called()
        popen.assert_not_called()
        self.assertEqual(linux, [
            "sudo", "-n", "unshare", "--net", "--", "sh", "-c",
            'ip link set lo up && u=$1 g=$2 && shift 2 && exec setpriv --reuid="$u" --regid="$g" --init-groups -- "$@"',
            "sh", "1001", "118", *[a.replace("{platform}", "linux-x86_64") for a in phase]])
        self.assertEqual(macos, ["sandbox-exec", "-p", cfi.SANDBOX_PROFILE,
                                 *[a.replace("{platform}", "macos-arm64") for a in phase]])

    def test_linux_defaults_to_the_runners_user(self):
        argv = cfi.offline_command("/s/bin/lmt", "linux-x86_64", "/w")
        self.assertEqual(argv[9:11], [str(os.getuid()), str(os.getgid())])
        self.assertEqual(argv[14], f"PATH={os.environ.get('PATH', '')}")


class OfflineStepsTest(FakeTest):
    """The offline phase's own steps, run in process (Fake.in_process_phase)."""

    def test_order_and_limits(self):
        with mock.patch.object(cfi, "run_command", wraps=cfi.run_command) as run_command, \
                mock.patch.object(cfi, "run_demo", wraps=cfi.run_demo) as run_demo:
            code, out = self.fake.main()
        self.assertEqual(code, 0, out)
        self.assertEqual([c.args[0][1] for c in run_command.call_args_list], ["models", "transcribe", "rename"])
        self.assertEqual([c.args[3:] for c in run_command.call_args_list[1:]], [(15 * 60,), (2 * 60,)])
        self.assertEqual([c.args[3] for c in run_demo.call_args_list], [30 * 60, 10])
        self.assertEqual(self.fake.probed, [(("192.0.2.1", 80), 2)])
        out_dir = self.fake.work.resolve() / "out"
        self.assertEqual(self.fake.checked, [("srt", out_dir / "two_speakers.srt"), ("vtt", out_dir / "two_speakers.vtt")])
        self.assertEqual(json.loads((self.fake.work / "offline.json").read_text())["steps"], [
            {"step": s, "name": n, "problem": None} for s, n, _ in cfi.OFFLINE])

    def test_macos_probes_in_its_sandbox(self):
        self.fake.probe = OSError(errno.EPERM, "Operation not permitted")  # sandbox-exec's refusal (#573)
        code, out = self.fake.main(platform="macos-arm64")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.fake.probed, [(("192.0.2.1", 80), 2)])
        self.assertEqual([line.split()[1] for line in out.splitlines()][3:], ["2.1", "2.2", "2.3", "2.4", "2.5"])
        self.assertEqual(self.fake.phase_argv[:2], ["sandbox-exec", "-p"])
        self.assertNotIn("sudo", self.fake.phase_argv)

    def test_the_probe_connecting_fails(self):
        self.fake.probe = mock.Mock()  # create_connection returns a socket: there's a route out
        code, out = self.fake.main()
        self.assertEqual(code, 1)
        self.assertIn("FAIL 2.1 the cut is real\n  - the namespace has a route out: 192.0.2.1:80 connects", out)
        self.fake.probe.close.assert_called_once()
        self.assertIn("FAIL 2.2 offline transcribe\n  - not reached: step 2.1 failed", out)

    def test_the_probe_failing_otherwise_fails(self):
        self.fake.probe = TimeoutError("timed out")
        code, out = self.fake.main()
        self.assertEqual(code, 1)
        self.assertIn("the namespace has a route out: connecting to 192.0.2.1:80 gives timed out, not ENETUNREACH or EPERM",
                      out)

    def test_transcribe_misses_its_limit(self):
        self.fake_with("transcribe-hangs")
        with mock.patch.object(cfi, "TRANSCRIBE_LIMIT", 1):
            code, out = self.fake.main()
        self.assertEqual(code, 1)
        self.assertIn("FAIL 2.2 offline transcribe\n  - lmt transcribe", out)
        self.assertIn("didn't finish within the 1 s limit", out)

    def test_a_subtitle_check_fails(self):
        def check_srt(path):
            raise AssertionError(f"{path}: no cue")

        stubs = Fake.stubs

        def failing_srt(fake):  # the fake's stubs, the probe's included, with this check_srt over them
            stack = stubs(fake)
            stack.enter_context(mock.patch.object(cfi, "subtitle_checkers", lambda: (check_srt, lambda path: None)))
            return stack

        with mock.patch.object(Fake, "stubs", failing_srt):
            code, out = self.fake.main(platform="macos-arm64")
        self.assertEqual(code, 1)
        self.assertIn("FAIL 2.2 offline transcribe\n  - check_srt fails on <work>/out/two_speakers.srt: ", out)

    def test_models_changed_against_the_saved_snapshot(self):
        def phase(argv):  # <work>/models changes after step 1.2's snapshot, before the phase
            (self.fake.work / "models" / "after.bin").write_bytes(b"x")
            return self.fake.in_process_phase(argv)

        code, out = self.fake.main(phase=phase)
        self.assertEqual(code, 1)
        self.assertIn("FAIL 2.4 the second --sample run\n  - <work>/models changed: ", out)
        self.assertIn("after.bin", out)

    def test_data_changed_by_the_second_run(self):
        code, out = self.fake_with("retranscribe").main()
        self.assertEqual(code, 1)
        self.assertIn("FAIL 2.4 the second --sample run\n  - <work>/data changed: ", out)
        self.assertIn("ES2004a.json", out)

    def test_the_second_run_misses_its_url_limit(self):
        def phase(argv):
            self.fake.env["FAKE_LMT_MODE"] = "no-url"
            with mock.patch.dict(os.environ, self.fake.env), mock.patch.object(cfi, "SECOND_URL_LIMIT", 1):
                return self.fake.in_process_phase(argv)

        code, out = self.fake.main(phase=phase)
        self.assertEqual(code, 1)
        self.assertIn("FAIL 2.4 the second --sample run\n  - no URL on stdout within the 1 s limit", out)
        self.assert_gone(self.fake.calls()[-1]["pid"])

    def test_a_line_in_the_guards_log(self):
        code, out = self.fake_with("guard-line").main()
        self.assertEqual(code, 1)
        self.assertIn("FAIL 2.5 the guard's log\n  - the guard's log has 1 line(s): connect ('203.0.113.7', 443)", out)


class OuterCheckTest(FakeTest):
    """The outer process's check of offline.json against the phase's exit code, and the record from it."""

    def run_with(self, code, steps=None, *, platform="linux-x86_64"):
        """main() with a stand-in phase that writes `steps` (or no file) and exits `code`: (exit code,
        stdout, record)."""
        def phase(argv):
            self.fake.phase_argv = argv
            if steps is not None:
                (self.fake.work / "offline.json").write_text(json.dumps({"steps": steps}))
            return code

        record = self.fake.tmp / "criteria-install-full.json"
        exit_code, out = self.fake.main("--criteria-out", str(record), platform=platform, phase=phase)
        return exit_code, out, json.loads(record.read_text())

    @staticmethod
    def steps(failed=None, platform="linux-x86_64"):
        out, reached = [], True
        for step, name, _ in cfi.offline_steps(platform):
            problem = None if reached and step != failed else ("boom" if reached else f"not reached: step {failed} failed")
            reached = reached and step != failed
            out.append({"step": step, "name": name, "problem": problem})
        return out

    def offline_checks(self, record):
        return [(c["check"].split(" ", 1)[1], c["criteria"], c["outcome"]) for c in record["checks"][2:]]

    def test_the_phase_is_offline_command(self):
        self.run_with(0, self.steps())
        work = self.fake.work.resolve()
        self.assertEqual(self.fake.phase_argv, cfi.offline_command(self.fake.lmt.resolve(), "linux-x86_64", work))
        self.assertTrue((work / "runs" / "offline" / "home").is_dir())

    def test_agreeing(self):
        code, _, record = self.run_with(1, self.steps(failed="2.3"))
        self.assertEqual(code, 1)
        self.assertEqual(self.offline_checks(record), [
            ("2.1 the cut is real", ["G3-8"], "passed"),
            ("2.2 offline transcribe", ["G3-8"], "passed"),
            ("2.3 offline rename", ["G3-8"], "failed"),
            ("2.4 the second --sample run", ["G3-6", "G3-8"], "failed"),
            ("2.5 the guard's log", ["G3-6", "G3-8"], "failed"),
        ])
        summary = (self.fake.tmp / "summary.md").read_text()
        self.assertIn("PASS 2.2 offline transcribe", summary)
        self.assertIn("FAIL 2.3 offline rename\n  - boom", summary)

    def test_agreeing_and_passing(self):
        code, out, record = self.run_with(0, self.steps())
        self.assertEqual(code, 0, out)
        self.assertEqual({c[2] for c in self.offline_checks(record)}, {"passed"})

    def test_missing(self):
        code, out, record = self.run_with(1)  # as when sudo fails before the phase starts
        self.assertEqual(code, 1)
        self.assertEqual([c[2] for c in self.offline_checks(record)], ["failed"] * 5)
        self.assertIn("FAIL 2.1 the cut is real\n  - no offline.json: the offline phase exits 1", out)
        self.assertIn("FAIL 2.5 the guard's log\n  - no offline.json: the offline phase exits 1",
                      (self.fake.tmp / "summary.md").read_text())

    def test_a_stale_file_is_missing(self):
        (self.fake.work / "offline.json").parent.mkdir(parents=True)
        (self.fake.work / "offline.json").write_text(json.dumps({"steps": self.steps()}))
        code, out, _ = self.run_with(1)
        self.assertEqual(code, 1)
        self.assertIn("no offline.json: the offline phase exits 1", out)

    def test_contradicting(self):
        for code, steps in ((1, self.steps()), (0, self.steps(failed="2.4"))):
            with self.subTest(code=code):
                self.setUp()
                exit_code, out, record = self.run_with(code, steps)
                self.assertEqual(exit_code, 1)
                self.assertEqual([c[2] for c in self.offline_checks(record)], ["failed"] * 5)
                self.assertIn(f"FAIL 2.1 the cut is real\n  - offline.json contradicts the offline phase's exit code "
                              f"{code}", out)

    def test_not_the_offline_steps(self):
        steps = [s for s in self.steps() if s["step"] != "2.1"]  # a list without 2.1
        code, out, record = self.run_with(0, steps)
        self.assertEqual(code, 1)
        self.assertEqual([c[2] for c in self.offline_checks(record)], ["failed"] * 5)
        self.assertIn("offline.json doesn't list the offline steps (the phase exits 0)", out)

    def test_macos_records_2_1(self):  # sandbox-exec cuts the network, so 2.1 runs on macOS too (#573)
        code, out, record = self.run_with(0, self.steps(platform="macos-arm64"), platform="macos-arm64")
        self.assertEqual(code, 0, out)
        self.assertEqual([c["check"] for c in record["checks"]], [
            "check_full_install.py::macos-arm64 1.1 models download",
            "check_full_install.py::macos-arm64 1.3 the first --sample run",
            "check_full_install.py::macos-arm64 2.1 the cut is real",
            "check_full_install.py::macos-arm64 2.2 offline transcribe",
            "check_full_install.py::macos-arm64 2.3 offline rename",
            "check_full_install.py::macos-arm64 2.4 the second --sample run",
            "check_full_install.py::macos-arm64 2.5 the guard's log",
        ])


class RecordTest(FakeTest):
    def record(self, *modes):
        out = self.fake.tmp / "criteria-install-full.json"
        code, _ = self.fake_with(*modes).main("--criteria-out", str(out))
        return code, json.loads(out.read_text())

    def test_a_passing_run(self):
        code, record = self.record()
        self.assertEqual(code, 0)
        self.assertEqual((record["job"], record["complete"]), ("install-full", True))
        self.assertEqual(record["checks"], [
            {"check": "check_full_install.py::linux-x86_64 1.1 models download", "criteria": ["G3-8"],
             "outcome": "passed"},
            {"check": "check_full_install.py::linux-x86_64 1.3 the first --sample run", "criteria": ["G3-6"],
             "outcome": "passed"},
            {"check": "check_full_install.py::linux-x86_64 2.1 the cut is real", "criteria": ["G3-8"],
             "outcome": "passed"},
            {"check": "check_full_install.py::linux-x86_64 2.2 offline transcribe", "criteria": ["G3-8"],
             "outcome": "passed"},
            {"check": "check_full_install.py::linux-x86_64 2.3 offline rename", "criteria": ["G3-8"],
             "outcome": "passed"},
            {"check": "check_full_install.py::linux-x86_64 2.4 the second --sample run", "criteria": ["G3-6", "G3-8"],
             "outcome": "passed"},
            {"check": "check_full_install.py::linux-x86_64 2.5 the guard's log", "criteria": ["G3-6", "G3-8"],
             "outcome": "passed"},
        ])

    def test_a_failing_run(self):
        code, record = self.record("download-fails")
        self.assertEqual(code, 1)
        self.assertTrue(record["complete"])
        self.assertEqual([(c["check"], c["outcome"]) for c in record["checks"]], [
            ("check_full_install.py::linux-x86_64 1.1 models download", "failed"),
            ("check_full_install.py::linux-x86_64 1.3 the first --sample run", "failed"),
            ("check_full_install.py::linux-x86_64 2.1 the cut is real", "failed"),
            ("check_full_install.py::linux-x86_64 2.2 offline transcribe", "failed"),
            ("check_full_install.py::linux-x86_64 2.3 offline rename", "failed"),
            ("check_full_install.py::linux-x86_64 2.4 the second --sample run", "failed"),
            ("check_full_install.py::linux-x86_64 2.5 the guard's log", "failed"),
        ])


if __name__ == "__main__":
    unittest.main()
