"""G1-11 (spec/acceptance.md), end to end: each bad input through `lmt transcribe` in a subprocess, within
120 s (design/internal/g1-stage2.md, P4). The decode cases need no model; the rest run in test-models."""

import json
import os
import re
import subprocess
import time

import pytest
from bad_inputs import DECODE_CASES, MUTATION_CASES, SPEECHLESS, build, run_bounded

OUTPUTS = ("txt", "srt", "vtt", "json")  # the default --formats


def report(line):
    print(line)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def transcribe(name, tmp_path):
    """The input built in its own directory, and `lmt transcribe <its absolute path>` run in a fresh one. The
    report gives its wall time, and on a timeout its stderr so far, so the runner's own times are on record (#643)."""
    inputs, work = tmp_path / "inputs", tmp_path / "work"
    inputs.mkdir()
    work.mkdir()
    path = build(name, inputs).resolve()
    start = time.perf_counter()
    try:
        r = run_bounded(["transcribe", str(path)], cwd=work)
    except subprocess.TimeoutExpired as e:
        stderr = e.stderr.decode(errors="replace") if isinstance(e.stderr, bytes) else e.stderr
        report(f"G1-11: lmt transcribe {name}: timed out after {e.timeout} s; stderr so far: {stderr!r}")
        raise
    report(f"G1-11: lmt transcribe {name}: exit {r.returncode} in {time.perf_counter() - start:.1f} s")
    return r, path, work


def assert_one_error_line(r, path, work):
    assert "Traceback" not in r.stderr, r.stderr
    lines = r.stderr.splitlines()
    assert len(lines) == 1, r.stderr
    assert re.match(rf"lmt: error: .*{re.escape(path.name)}: \S", lines[0]), lines[0]
    assert list(work.iterdir()) == [], r.stdout


def test_a_timeout_is_reported_with_its_stderr(tmp_path, monkeypatch):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    def times_out(argv, *, cwd):
        raise subprocess.TimeoutExpired(argv, 120, stderr=b"lmt: downloading kyutai/model.safetensors\n")

    monkeypatch.setitem(globals(), "run_bounded", times_out)
    with pytest.raises(subprocess.TimeoutExpired):
        transcribe("silence.wav", tmp_path)
    assert summary.read_text(encoding="utf-8") == ("G1-11: lmt transcribe silence.wav: timed out after 120 s; "
                                                   "stderr so far: 'lmt: downloading kyutai/model.safetensors\\n'\n")


@pytest.mark.criterion("G1-11")
@pytest.mark.parametrize("name", DECODE_CASES)
def test_a_decode_case_exits_3_with_one_error_line(tmp_path, name):
    r, path, work = transcribe(name, tmp_path)
    assert r.returncode == 3, r.stderr
    assert_one_error_line(r, path, work)


@pytest.mark.models
@pytest.mark.criterion("G1-11")
@pytest.mark.parametrize("name", SPEECHLESS)
def test_silence_and_noise_exit_4_with_one_error_line(tmp_path, name):
    r, path, work = transcribe(name, tmp_path)
    assert r.returncode == 4, r.stderr
    assert_one_error_line(r, path, work)


@pytest.mark.models
@pytest.mark.criterion("G1-11")
@pytest.mark.parametrize("name", MUTATION_CASES)
def test_a_mutation_exits_3_or_4_or_writes_valid_outputs(tmp_path, name):
    from lmt.schema import validate

    r, path, work = transcribe(name, tmp_path)
    assert r.returncode in (0, 3, 4), r.stderr
    if r.returncode:
        assert_one_error_line(r, path, work)
        return
    stem = path.stem
    for suffix in OUTPUTS:
        assert (work / f"{stem}.{suffix}").is_file(), r.stdout
    validate(json.loads((work / f"{stem}.json").read_text(encoding="utf-8")))
