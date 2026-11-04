"""G1-6: one test per `lmt transcribe` option, each checking its effect, with fake models; and each bad
input through `lmt transcribe` in a process of its own (design/internal/g1-stage2.md, P3)."""

import json
import os

import pytest
import test_models
import test_pipeline
from conftest import CLIP, run_lmt
from test_pipeline import run

from lmt import diarize, models

pytestmark = pytest.mark.criterion("G1-6")
# Their fixtures: test_pipeline's Fakes, its silent WAV and output directory, and the fake hub.
fakes, wav, out, hub = test_pipeline.fakes, test_pipeline.wav, test_pipeline.out, test_models.hub
REAL_ENSURE = models.ensure  # Fakes replaces it; --offline's test needs the real one
STAGES = ["decode", "models", "asr", "diarize", "align", "export"]
# Each line comes when its stage ends (#643), and ASR and diarization run side by side.
ORDERS = (STAGES, ["decode", "models", "diarize", "asr", "align", "export"])


@pytest.fixture
def cwd(tmp_path, monkeypatch):
    path = tmp_path / "cwd"
    path.mkdir()
    monkeypatch.chdir(path)
    return path


def outputs(directory, formats=("txt", "srt", "vtt", "json")):
    return [directory / f"meeting.{fmt}" for fmt in formats]


def diarize_options(fakes):
    return [c[1] for c in fakes.calls if isinstance(c, tuple)]


# The options, in public-api.md's order.

@pytest.mark.parametrize("flag", ["-o", "--output-dir"])
def test_output_dir(fakes, wav, out, cwd, capsys, flag):
    code, stdout, stderr = run(capsys, "transcribe", wav, flag, out)
    assert code == 0, stderr
    assert stdout.splitlines() == [str(p) for p in outputs(out)]
    assert sorted(out.iterdir()) == sorted(outputs(out))
    assert list(cwd.iterdir()) == [], "nothing lands in the working directory"


def test_output_dir_defaults_to_the_working_directory(fakes, wav, cwd, capsys):
    code, _, stderr = run(capsys, "transcribe", wav)
    assert code == 0, stderr
    assert sorted(p.name for p in cwd.iterdir()) == sorted(p.name for p in outputs(cwd))


@pytest.mark.parametrize("flag", ["-f", "--formats"])
def test_formats(fakes, wav, out, capsys, flag):
    code, stdout, stderr = run(capsys, "transcribe", wav, "-o", out, flag, "srt,json")
    assert code == 0, stderr
    assert stdout.splitlines() == [str(p) for p in outputs(out, ("srt", "json"))]
    assert sorted(p.name for p in out.iterdir()) == ["meeting.json", "meeting.srt"]


def test_num_speakers(fakes, wav, out, capsys):
    code, _, stderr = run(capsys, "transcribe", wav, "-o", out, "--num-speakers", "3")
    assert code == 0, stderr
    assert diarize_options(fakes) == [{"num_speakers": 3, "min_speakers": None, "max_speakers": None}]


@pytest.mark.parametrize("argv, expected", [
    (["--min-speakers", "2"], {"num_speakers": None, "min_speakers": 2, "max_speakers": None}),
    (["--max-speakers", "5"], {"num_speakers": None, "min_speakers": None, "max_speakers": 5}),
    (["--min-speakers", "2", "--max-speakers", "5"], {"num_speakers": None, "min_speakers": 2, "max_speakers": 5}),
])
def test_min_and_max_speakers(fakes, wav, out, capsys, argv, expected):
    code, _, stderr = run(capsys, "transcribe", wav, "-o", out, *argv)
    assert code == 0, stderr
    assert diarize_options(fakes) == [expected]


def test_no_diarize(fakes, wav, out, capsys):
    code, _, stderr = run(capsys, "transcribe", wav, "-o", out, "--no-diarize")
    assert code == 0, stderr
    assert "load diarize" not in fakes.calls and diarize_options(fakes) == []
    doc = json.loads((out / "meeting.json").read_text(encoding="utf-8"))
    assert doc["segments"] and {s["speaker"] for s in doc["segments"]} == {"S1"}
    assert doc["models"]["diarization"] is None


@pytest.mark.parametrize("argv, expected", [([], "kyutai"), (["--engine", "apple"], "apple")])
def test_engine(fakes, wav, out, capsys, argv, expected):
    code, _, stderr = run(capsys, "transcribe", wav, "-o", out, *argv)
    assert code == 0, stderr
    assert fakes.loads == [(expected, False)]
    doc = json.loads((out / "meeting.json").read_text(encoding="utf-8"))
    assert doc["models"]["asr"]["engine"] == expected


@pytest.mark.parametrize("present", [False, True])
def test_offline(fakes, hub, wav, out, capsys, monkeypatch, present):
    monkeypatch.setattr(models, "ensure", REAL_ENSURE)
    monkeypatch.setattr(diarize, "DIARIZATION", "diar")
    if present:
        models.download(models.default_models(hub["manifest"]))
        hub["calls"].clear()
    code, stdout, stderr = run(capsys, "transcribe", wav, "-o", out, "--offline")
    assert hub["calls"] == [], "--offline never downloads"
    assert fakes.loads == [("kyutai", True)], "the engine loads offline too"
    if present:
        assert code == 0, stderr
        assert sorted(out.iterdir()) == sorted(outputs(out))
    else:
        assert (code, stdout) == (5, "")
        assert stderr == ("lmt: error: org/diar/config.yaml: missing, and --offline never downloads; "
                          "run lmt models download\n")
        assert list(out.iterdir()) == []


def test_overwrite(fakes, wav, out, capsys):
    (out / "meeting.srt").write_text("old")
    code, _, stderr = run(capsys, "transcribe", wav, "-o", out, "--overwrite")
    assert code == 0, stderr
    assert (out / "meeting.srt").read_text() != "old"


def test_without_overwrite_an_existing_output_is_kept(fakes, wav, out, capsys):
    (out / "meeting.srt").write_text("old")
    code, stdout, stderr = run(capsys, "transcribe", wav, "-o", out)
    assert (code, stdout) == (2, "")
    assert stderr == f"lmt: error: {out / 'meeting.srt'}: exists; use --overwrite to replace it\n"
    assert (out / "meeting.srt").read_text() == "old"
    assert [p.name for p in out.iterdir()] == ["meeting.srt"]


@pytest.mark.parametrize("flag", ["-v", "--verbose"])
def test_verbose(fakes, wav, out, capsys, flag):
    code, _, stderr = run(capsys, "transcribe", wav, "-o", out, flag)
    assert code == 0, stderr
    assert [line.split()[1] for line in stderr.splitlines()] in ORDERS


def test_without_verbose_no_stage_line(fakes, wav, out, capsys):
    code, _, stderr = run(capsys, "transcribe", wav, "-o", out)
    assert (code, stderr) == (0, "")


# Bad input, through `lmt transcribe` in a process of its own. Decode comes before the models (P1), so
# none is needed: the cache is empty and offline, so a run that reached a model would exit 5.

@pytest.fixture
def isolated(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    return os.environ | {"LMT_CACHE_DIR": str(cache), "HF_HUB_OFFLINE": "1"}


def assert_one_error_line(r, code, subject, out_dir, before):
    assert r.returncode == code, r.stderr
    assert r.stdout == ""
    assert "Traceback" not in r.stderr
    assert len(r.stderr.splitlines()) == 1, r.stderr
    assert r.stderr.startswith(f"lmt: error: {subject}: "), r.stderr
    assert sorted(out_dir.iterdir()) == before, "the output directory holds no new file"


def test_missing_file(tmp_path, out, isolated):
    missing = tmp_path / "missing.wav"
    r = run_lmt(["transcribe", str(missing), "-o", str(out)], cwd=tmp_path, env=isolated)
    assert_one_error_line(r, 3, missing, out, [])


def test_directory(tmp_path, out, isolated):
    directory = tmp_path / "recording.wav"
    directory.mkdir()
    r = run_lmt(["transcribe", str(directory), "-o", str(out)], cwd=tmp_path, env=isolated)
    assert_one_error_line(r, 3, directory, out, [])


def test_unknown_option(tmp_path, out, isolated):
    r = run_lmt(["transcribe", str(CLIP), "-o", str(out), "--language", "en"], cwd=tmp_path, env=isolated)
    assert_one_error_line(r, 2, "--language", out, [])


def test_bad_value(tmp_path, out, isolated):
    r = run_lmt(["transcribe", str(CLIP), "-o", str(out), "--num-speakers", "0"], cwd=tmp_path, env=isolated)
    assert_one_error_line(r, 2, "--num-speakers", out, [])


def test_existing_output(tmp_path, out, isolated):
    existing = out / "clip.json"
    existing.write_text("{}")
    r = run_lmt(["transcribe", str(CLIP), "-o", str(out)], cwd=tmp_path, env=isolated)
    assert_one_error_line(r, 2, existing, out, [existing])
    assert existing.read_text() == "{}"


def test_unwritable_output_directory(tmp_path, out, isolated):
    if os.geteuid() == 0:
        pytest.skip("running as root, who can write anywhere, so no directory is unwritable")
    out.chmod(0o500)
    try:
        r = run_lmt(["transcribe", str(CLIP), "-o", str(out)], cwd=tmp_path, env=isolated)
        assert_one_error_line(r, 3, out, out, [])
    finally:
        out.chmod(0o700)
