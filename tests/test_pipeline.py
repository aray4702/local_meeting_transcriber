"""`lmt transcribe` with fake models (design/internal/g1-slice.md, S6): the checks before any work, the
stages' plumbing, the exit codes and the outputs."""

import json
import wave

import pytest
from fake_engine import INFO, FakeEngine

from lmt import cli, diarize, engines, models, pipeline
from lmt.transcript import Turn, Word

WORDS = [Word(0.1, 0.4, "Hello", 0.9), Word(0.5, 0.9, "there.", 0.8), Word(1.1, 1.6, "Hi.", 0.7)]
TURNS = [Turn(0.0, 1.0, "SPEAKER_00"), Turn(1.0, 1.9, "SPEAKER_01")]


class Fakes:
    """engines.load, diarize.load and models.ensure replaced, recording every call."""

    def __init__(self, monkeypatch, tmp_path):
        self.calls = []
        self.words = list(WORDS)
        self.ensured = None
        self.loads = []  # engines.load's (name, offline)

        def ensure(needed, offline=False):
            self.calls.append("ensure")
            self.ensured = [m.name for m in needed]
            return {m.name: tmp_path / m.name for m in needed}

        fakes = self

        class Engine(FakeEngine):
            def transcribe(self, audio):
                fakes.calls.append("asr")
                return list(fakes.words)

        class Diarizer:
            def diarize(self, audio, **options):
                fakes.calls.append(("diarize", options))
                return list(TURNS)

        def load_engine(name, *, offline):
            self.calls.append("load asr")
            self.loads.append((name, offline))
            return Engine(name=name)

        def load_diarizer(dirs):
            self.calls.append("load diarize")
            return Diarizer()

        monkeypatch.setattr(models, "ensure", ensure)
        monkeypatch.setattr(engines, "load", load_engine)
        monkeypatch.setattr(diarize, "load", load_diarizer)


@pytest.fixture
def fakes(monkeypatch, tmp_path):
    return Fakes(monkeypatch, tmp_path)


@pytest.fixture
def wav(tmp_path):
    """2 s of silence, 16-bit 16 kHz mono: decode runs for real."""
    path = tmp_path / "meeting.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\0\0" * 32000)
    return path


@pytest.fixture
def out(tmp_path):
    path = tmp_path / "out"
    path.mkdir()
    return path


def run(capsys, *argv):
    code = cli.main([str(a) for a in argv])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_writes_the_four_files_and_prints_their_paths(fakes, wav, out, capsys):
    code, stdout, stderr = run(capsys, "transcribe", wav, "-o", out)
    assert code == 0, stderr
    paths = [out / f"meeting.{fmt}" for fmt in ("txt", "srt", "vtt", "json")]
    assert stdout.splitlines() == [str(p) for p in paths]
    assert all(p.is_file() for p in paths)
    assert sorted(out.iterdir()) == sorted(paths)  # no temporary file left
    doc = json.loads(paths[3].read_text(encoding="utf-8"))
    assert [s["text"] for s in doc["segments"]] == ["Hello there.", "Hi."]
    assert [s["speaker"] for s in doc["segments"]] == ["S1", "S2"]
    assert doc["source"] == {"file": "meeting.wav", "duration": 2.0}
    manifest = models.load_manifest()
    diarization = manifest.get(diarize.DIARIZATION)
    assert doc["schema_version"] == "1.2"
    assert doc["models"] == {
        "asr": INFO,
        "diarization": {"name": diarization.name, "repository": diarization.repository,
                        "revision": diarization.revision},
    }
    assert fakes.loads == [("kyutai", False)]  # the engine ensures its own model
    assert fakes.ensured == [m.name for m in models.diarization_models(manifest)]
    assert stderr == ""


@pytest.mark.parametrize("argv, expected", [([], "kyutai"), (["--engine", "kyutai"], "kyutai"),
                                            (["--engine", "apple"], "apple")])
def test_engine_reaches_engines_load_and_the_transcript(fakes, wav, out, capsys, argv, expected):
    code, _, stderr = run(capsys, "transcribe", wav, "-o", out, "--offline", *argv)
    assert code == 0, stderr
    assert fakes.loads == [(expected, True)]
    doc = json.loads((out / "meeting.json").read_text(encoding="utf-8"))
    assert doc["models"]["asr"]["engine"] == expected


def test_an_engine_that_cant_run_exits_5_and_writes_nothing(wav, out, capsys, monkeypatch):
    def load(name, *, offline):
        raise engines.ModelError(f"--engine {name}", "not in this build")

    monkeypatch.setattr(engines, "load", load)
    code, stdout, stderr = run(capsys, "transcribe", wav, "-o", out, "--engine", "apple")
    assert (code, stdout, stderr) == (5, "", "lmt: error: --engine apple: not in this build\n")
    assert list(out.iterdir()) == []


@pytest.mark.parametrize("parallel", [True, False])
def test_speaker_options_reach_diarization(fakes, wav, out, capsys, monkeypatch, parallel):
    monkeypatch.setattr(pipeline, "PARALLEL", parallel)
    code, _, stderr = run(capsys, "transcribe", wav, "-o", out, "--min-speakers", "2", "--max-speakers", "3")
    assert code == 0, stderr
    assert ("diarize", {"num_speakers": None, "min_speakers": 2, "max_speakers": 3}) in fakes.calls


def test_no_diarize_never_loads_diarization(fakes, wav, out, capsys):
    code, _, stderr = run(capsys, "transcribe", wav, "-o", out, "--no-diarize")
    assert code == 0, stderr
    assert "load diarize" not in fakes.calls
    assert not [c for c in fakes.calls if isinstance(c, tuple)]
    assert fakes.ensured == []
    doc = json.loads((out / "meeting.json").read_text(encoding="utf-8"))
    assert doc["models"]["diarization"] is None
    assert {s["speaker"] for s in doc["segments"]} == {"S1"}


def test_existing_output_without_overwrite_exits_2_before_any_work(fakes, wav, out, capsys):
    (out / "meeting.srt").write_text("old")
    code, stdout, stderr = run(capsys, "transcribe", wav, "-o", out)
    assert (code, stdout, fakes.calls) == (2, "", [])
    assert stderr == f"lmt: error: {out / 'meeting.srt'}: exists; use --overwrite to replace it\n"
    assert (out / "meeting.srt").read_text() == "old"
    assert sorted(p.name for p in out.iterdir()) == ["meeting.srt"]


def test_overwrite_replaces_existing_outputs(fakes, wav, out, capsys):
    (out / "meeting.srt").write_text("old")
    code, _, stderr = run(capsys, "transcribe", wav, "-o", out, "--overwrite")
    assert code == 0, stderr
    assert (out / "meeting.srt").read_text() != "old"


def test_missing_output_directory_exits_3_before_any_work(fakes, wav, tmp_path, capsys):
    code, stdout, stderr = run(capsys, "transcribe", wav, "-o", tmp_path / "missing")
    assert (code, stdout, fakes.calls) == (3, "", [])
    assert stderr.startswith("lmt: error: ") and len(stderr.splitlines()) == 1


@pytest.mark.parametrize("argv", [["--engine", "whisper"], ["--model", "tiny"]])
def test_unknown_engine_or_the_old_model_option_exits_2_before_any_work(fakes, wav, out, capsys, argv):
    code, stdout, stderr = run(capsys, "transcribe", wav, "-o", out, *argv)
    assert (code, stdout, fakes.calls) == (2, "", [])
    assert stderr.startswith(f"lmt: error: {argv[0]}: ")


def test_no_words_exits_4_and_writes_nothing(fakes, wav, out, capsys):
    fakes.words = []
    code, stdout, stderr = run(capsys, "transcribe", wav, "-o", out)
    assert (code, stdout) == (4, "")
    assert stderr == "lmt: error: meeting.wav: no speech found\n"
    assert list(out.iterdir()) == []


def test_bad_input_exits_3_and_writes_nothing(fakes, tmp_path, out, capsys):
    bad = tmp_path / "notes.wav"
    bad.write_text("not audio")
    code, stdout, stderr = run(capsys, "transcribe", bad, "-o", out)
    assert (code, stdout) == (3, "")
    assert stderr.startswith(f"lmt: error: {bad}: ")
    assert list(out.iterdir()) == []


def test_missing_input_exits_3_before_the_models(monkeypatch, tmp_path, out, capsys):
    ensured = []

    def ensure(needed, offline=False):
        ensured.append(needed)
        pytest.fail("models.ensure was called before decode")

    monkeypatch.setattr(models, "ensure", ensure)
    missing = tmp_path / "missing.wav"
    code, stdout, stderr = run(capsys, "transcribe", missing, "-o", out)
    assert (code, stdout, ensured) == (3, "", [])
    assert stderr == f"lmt: error: {missing}: no such file\n"
    assert list(out.iterdir()) == []


def test_one_format_writes_one_file(fakes, wav, out, capsys):
    code, stdout, stderr = run(capsys, "transcribe", wav, "-o", out, "-f", "json")
    assert code == 0, stderr
    assert stdout == f"{out / 'meeting.json'}\n"
    assert [p.name for p in out.iterdir()] == ["meeting.json"]


def test_verbose_prints_six_stage_lines(fakes, wav, out, capsys):
    code, _, stderr = run(capsys, "transcribe", wav, "-o", out, "-v")
    assert code == 0, stderr
    lines = stderr.splitlines()
    # ASR and diarization run side by side, and each line comes when its stage ends.
    assert [line.split()[1] for line in lines] in (["decode", "models", "asr", "diarize", "align", "export"],
                                                    ["decode", "models", "diarize", "asr", "align", "export"])
    for line in lines:
        prefix, _stage, seconds, unit = line.split()
        assert (prefix, unit) == ("lmt:", "s")
        assert float(seconds) >= 0


def test_verbose_prints_each_stage_when_it_ends(fakes, wav, out, capsys, monkeypatch):
    # Run one after the other, diarization finds the earlier stages' lines already on stderr (#643).
    monkeypatch.setattr(pipeline, "PARALLEL", False)
    seen = []

    class Diarizer:
        def diarize(self, audio, **options):
            seen.append(capsys.readouterr().err)
            return list(TURNS)

    monkeypatch.setattr(diarize, "load", lambda dirs: Diarizer())
    code, _, stderr = run(capsys, "transcribe", wav, "-o", out, "-v")
    assert code == 0, stderr
    assert [line.split()[1] for line in seen[0].splitlines()] == ["decode", "models", "asr"]
    assert [line.split()[1] for line in stderr.splitlines()] == ["diarize", "align", "export"]


def test_verbose_keeps_the_stages_before_a_failure(wav, out, capsys, monkeypatch):
    def load(name, *, offline):
        raise engines.ModelError(f"--engine {name}", "not in this build")

    monkeypatch.setattr(engines, "load", load)
    code, stdout, stderr = run(capsys, "transcribe", wav, "-o", out, "--engine", "apple", "-v")
    assert (code, stdout) == (5, "")
    lines = stderr.splitlines()
    assert [line.split()[:2] for line in lines[:2]] == [["lmt:", "decode"], ["lmt:", "models"]]
    assert lines[2:] == ["lmt: error: --engine apple: not in this build"]


def test_transcribe_fills_timings(fakes, wav):
    timings = {}
    transcript = pipeline.transcribe(wav, timings=timings)
    assert set(timings) == {"decode", "models", "asr", "diarize", "align"}
    assert [s.text for s in transcript.segments] == ["Hello there.", "Hi."]
