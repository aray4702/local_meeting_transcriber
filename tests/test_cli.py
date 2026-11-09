"""The CLI: help, version, usage errors, the stubs, and G1-6's option-table test (design §1a)."""

import argparse
import contextlib
import io
import re
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

import pytest

from lmt import cli

PUBLIC_API = Path(__file__).resolve().parents[1] / "design" / "public-api.md"


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


def documented_options():
    """{command path: option strings} from public-api.md's "Commands" section, `--help` left out."""
    text = PUBLIC_API.read_text()
    commands = text.split("\n## Commands\n", 1)[1].split("\n## ", 1)[0]
    options = {}
    for block in re.split(r"^### ", commands, flags=re.MULTILINE)[1:]:
        heading, _, body = block.partition("\n")
        if heading == "Global options":
            options[()] = set(re.findall(r"`lmt (--[\w-]+)`", body)) - {"--help"}
            continue
        command = re.match(r"`lmt (\w+)", heading).group(1)
        if command == "models":  # one row per subcommand, its options in brackets
            for action, rest in re.findall(r"^\| `lmt models (\w+)([^`]*)`", body, re.MULTILINE):
                options[("models", action)] = set(re.findall(r"--[\w-]+", rest))
            continue
        found = set()
        for line in body.splitlines():
            if line.startswith("| `-"):
                found |= {code.split()[0] for code in re.findall(r"`([^`]+)`", line.split("|")[1])}
        options[(command,)] = found
    return options


def parser_options(parser, path=()):
    """{command path: option strings} for the root and every parser without subcommands."""
    options, found, nested = {}, set(), False
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            nested = True
            for name, sub in action.choices.items():
                options.update(parser_options(sub, path + (name,)))
        elif not isinstance(action, argparse._HelpAction):
            found |= set(action.option_strings)
    if path == () or not nested:
        options[path] = found
    return options


class HelpAndVersionTest(unittest.TestCase):
    @pytest.mark.criterion("G1-6", "G3-3")
    def test_help_exits_0_for_lmt_and_every_subcommand(self):
        for argv in ([], ["transcribe"], ["models"], ["models", "download"], ["models", "list"],
                     ["models", "verify"], ["eval"], ["rename"], ["demo"]):
            with self.subTest(argv=argv):
                code, out, err = run(*argv, "--help")
                self.assertEqual(code, 0, err)
                self.assertIn("usage: lmt", out)

    @pytest.mark.criterion("G1-6")
    def test_module_entry_point_help(self):
        r = subprocess.run([sys.executable, "-m", "lmt", "--help"], capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("transcribe", r.stdout)

    def test_help_imports_no_handler_module(self):
        script = ("import sys; from lmt.cli import main; main(['--help']); "
                  "print([m for m in ('lmt.pipeline', 'lmt.models', 'lmt.eval.cli', 'lmt.rename', "
                  "'lmt.demo.server', 'lmt.demo.sample') if m in sys.modules])")
        r = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip().splitlines()[-1], "[]")

    @pytest.mark.criterion("G1-6")
    def test_version(self):
        code, out, _ = run("--version")
        self.assertEqual((code, out), (0, "lmt 0.3.0\n"))


@pytest.mark.criterion("G1-6")
class OptionTableTest(unittest.TestCase):
    """G1-6: the parser's options are exactly public-api.md's, both ways."""

    @pytest.mark.criterion("G3-3")
    def test_parser_matches_public_api(self):
        documented = documented_options()
        self.assertEqual(set(documented), {(), ("transcribe",), ("live",), ("models", "download"),
                                           ("models", "list"), ("models", "verify"), ("eval",), ("rename",),
                                           ("demo",), ("app",)})
        self.assertEqual(parser_options(cli.build_parser()), documented)

    def test_transcribe_table_is_read(self):
        # Guards the reader: a table it failed to parse would compare empty with empty.
        self.assertIn("--output-dir", documented_options()[("transcribe",)])
        self.assertIn("-f", documented_options()[("transcribe",)])


@pytest.mark.criterion("G1-6")
class UsageErrorTest(unittest.TestCase):
    def assertUsageError(self, argv, subject):
        code, out, err = run(*argv)
        self.assertEqual(code, 2, err)
        self.assertEqual(out, "")
        self.assertEqual(len(err.splitlines()), 1, err)
        self.assertTrue(err.startswith(f"lmt: error: {subject}: "), err)

    # argparse's own errors
    def test_unknown_option(self):
        self.assertUsageError(["transcribe", "a.wav", "--language", "en"], "--language")

    def test_unknown_command(self):
        self.assertUsageError(["summarize"], "COMMAND")

    def test_no_command(self):
        self.assertUsageError([], "COMMAND")

    def test_missing_input(self):
        self.assertUsageError(["transcribe"], "INPUT")

    def test_bad_integer(self):
        self.assertUsageError(["transcribe", "a.wav", "--num-speakers", "two"], "--num-speakers")

    def test_missing_value(self):
        self.assertUsageError(["transcribe", "a.wav", "--model"], "--model")

    def test_bad_choice(self):
        self.assertUsageError(["eval", "--set", "big"], "--set")

    def test_abbreviated_option(self):
        self.assertUsageError(["transcribe", "a.wav", "--over"], "--over")

    def test_short_option_names_the_long_one(self):
        self.assertUsageError(["transcribe", "a.wav", "-f"], "--formats")

    # validate's rules
    def test_unknown_format(self):
        self.assertUsageError(["transcribe", "a.wav", "-f", "txt,docx"], "--formats")

    def test_empty_format(self):
        self.assertUsageError(["transcribe", "a.wav", "--formats", "txt,"], "--formats")

    def test_repeated_format(self):
        self.assertUsageError(["transcribe", "a.wav", "--formats", "srt,txt,srt"], "--formats")

    def test_formats_keep_their_order(self):
        args = cli.build_parser().parse_args(["transcribe", "a.wav", "-f", "vtt,txt"])
        cli.validate(args)
        self.assertEqual(args.formats, ["vtt", "txt"])

    @pytest.mark.criterion("G1-4")
    def test_default_formats(self):
        args = cli.build_parser().parse_args(["transcribe", "a.wav"])
        self.assertEqual(args.formats, "txt,srt,vtt,json")
        cli.validate(args)
        self.assertEqual(args.formats, ["txt", "srt", "vtt", "json"])

    def test_speakers_out_of_range(self):
        for option, value in (("--num-speakers", "0"), ("--min-speakers", "21"), ("--max-speakers", "-1")):
            with self.subTest(option=option):
                self.assertUsageError(["transcribe", "a.wav", option, value], option)

    def test_min_more_than_max(self):
        self.assertUsageError(["transcribe", "a.wav", "--min-speakers", "4", "--max-speakers", "3"],
                              "--min-speakers")

    def test_num_with_min_or_max(self):
        for option in ("--min-speakers", "--max-speakers"):
            with self.subTest(option=option):
                self.assertUsageError(["transcribe", "a.wav", "--num-speakers", "2", option, "2"], option)

    def test_no_diarize_with_speakers(self):
        for option in ("--num-speakers", "--min-speakers", "--max-speakers"):
            with self.subTest(option=option):
                self.assertUsageError(["transcribe", "a.wav", "--no-diarize", option, "2"], option)

    def test_eval_needs_set_or_check_readme(self):
        self.assertUsageError(["eval"], "--set")

    def test_eval_set_and_check_readme_conflict(self):
        self.assertUsageError(["eval", "--set", "ci", "--check-readme"], "--check-readme")

    def test_update_readme_only_with_full(self):
        self.assertUsageError(["eval", "--set", "ci", "--update-readme"], "--update-readme")
        self.assertUsageError(["eval", "--check-readme", "--update-readme"], "--update-readme")

    @pytest.mark.criterion("G3-3")
    def test_rename_unknown_format(self):
        self.assertUsageError(["rename", "t.json", "S1=Ana", "-f", "txt,docx"], "--formats")

    @pytest.mark.criterion("G3-4")
    def test_demo_transcript_and_sample_conflict(self):
        self.assertUsageError(["demo", "t.json", "--sample"], "--sample")

    def test_demo_needs_transcript_or_sample(self):
        self.assertUsageError(["demo"], "TRANSCRIPT")

    def test_demo_audio_and_sample_conflict(self):
        self.assertUsageError(["demo", "--sample", "--audio", "a.wav"], "--audio")

    def test_demo_port_out_of_range(self):
        for value in ("65536", "-1"):
            with self.subTest(value=value):
                self.assertUsageError(["demo", "t.json", "--port", value], "--port")


def every_parser(parser):
    """`parser` and each parser under it, at any depth."""
    yield parser
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for sub in action.choices.values():
                yield from every_parser(sub)


class EnglishOnlyTest(unittest.TestCase):
    @pytest.mark.criterion("G1-7")
    def test_no_language_option(self):
        found = {option for parser in every_parser(cli.build_parser()) for action in parser._actions
                 for option in action.option_strings}
        self.assertIn("--num-speakers", found)  # guards the walk: it reached transcribe's parser
        self.assertIn("--bytes", found)  # and one two levels down
        self.assertEqual([o for o in found if "lang" in o.lower()], [])


class HandlerTest(unittest.TestCase):
    def test_valid_speakers_reach_the_handler(self):
        with mock.patch("lmt.pipeline.cli_transcribe", return_value=None) as handler:
            code, _, err = run("transcribe", "a.wav", "--min-speakers", "2", "--max-speakers", "2")
        self.assertEqual(code, 0, err)
        self.assertEqual((handler.call_args.args[0].min_speakers, handler.call_args.args[0].max_speakers), (2, 2))

    def test_handler_code_is_returned(self):
        with mock.patch("lmt.models.cli_models", return_value=5):
            self.assertEqual(run("models", "verify")[0], 5)

    def test_keyboard_interrupt_exits_130(self):
        with mock.patch("lmt.pipeline.cli_transcribe", side_effect=KeyboardInterrupt):
            self.assertEqual(run("transcribe", "a.wav")[0], 130)

    def test_internal_error_is_one_line_without_a_traceback(self):
        with mock.patch("lmt.pipeline.cli_transcribe", side_effect=ValueError("boom")):
            code, _, err = run("transcribe", "a.wav")
        self.assertEqual((code, err), (1, "lmt: error: internal: ValueError: boom\n"))


if __name__ == "__main__":
    unittest.main()
