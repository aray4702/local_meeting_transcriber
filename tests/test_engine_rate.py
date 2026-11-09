"""Batch mode's audio at the engine's own rate (#575, 62b38dd; #601 item 2): the pipeline decodes the file again at
`Engine.rate` and passes `rate=`; an engine at the default 16 kHz gets decode's samples and no keyword; and
`audio.decode(path, rate)` gives the same signal as resampling."""

import wave

import numpy
import pytest
from fake_engine import FakeEngine, install

from lmt import audio, pipeline
from lmt.engines import Piece

WORD = [Piece(" hi", 0.0, 0.08, True, 0.9)]


def tone(path, rate, seconds=1.0):
    t = numpy.arange(round(rate * seconds)) / rate
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((numpy.sin(2 * numpy.pi * 440 * t) * 8000).astype("<i2").tobytes())
    return path


class Rated(FakeEngine):
    """An engine that wants 24 kHz, recording each transcribe's audio and keywords."""

    rate = 24000

    def __init__(self):
        super().__init__(WORD)
        self.calls = []

    def transcribe(self, audio, **kwargs):
        self.calls.append((len(audio), kwargs))
        return super().transcribe(audio)


def test_an_engine_at_24_khz_gets_the_file_decoded_at_24_khz(tmp_path, monkeypatch):
    path = tone(tmp_path / "a.wav", 48000)
    engine = Rated()
    install(monkeypatch, engine)
    result = pipeline.transcribe(path, diarize=False)
    [(n, kwargs)] = engine.calls
    assert kwargs == {"rate": 24000}
    assert n == len(audio.decode(path, 24000))
    assert abs(n - 1.5 * len(audio.decode(path))) <= 2
    assert result.source["duration"] == pytest.approx(len(audio.decode(path)) / 16000, abs=1e-3)


def test_an_engine_at_the_default_rate_gets_decode_s_16_khz_and_no_keyword(tmp_path, monkeypatch):
    path = tone(tmp_path / "a.wav", 48000)
    engine = FakeEngine(WORD)
    install(monkeypatch, engine)
    pipeline.transcribe(path, diarize=False)
    [samples] = engine.transcribed
    assert len(samples) == len(audio.decode(path))


@pytest.mark.parametrize("in_rate", [48000, 16000])
def test_decode_at_24_khz_matches_resampling_the_input(tmp_path, in_rate):
    path = tone(tmp_path / f"t{in_rate}.wav", in_rate)
    direct = audio.decode(path, 24000)
    assert len(direct) == pytest.approx(24000, abs=2)
    with wave.open(str(path), "rb") as w:
        raw = numpy.frombuffer(w.readframes(w.getnframes()), "<i2").astype(numpy.float32) / 32768
    r = audio.Resampler(in_rate, 1, out_rate=24000)
    resampled = numpy.concatenate([r.push(raw), r.flush()])
    n = min(len(direct), len(resampled))
    assert numpy.max(numpy.abs(direct[:n] - resampled[:n])) < 1e-3
