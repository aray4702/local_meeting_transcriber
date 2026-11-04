"""`lmt transcribe`: decode, ASR and diarization, alignment and the exports (design/internal/g1-slice.md, S6;
design/architecture.md, "Pipeline").

`cli_transcribe` checks everything it can before loading any model. Every error is an `LmtError`, which
`cli.main` prints as one line with its exit code. G3's `transcribe(path, offline=...)` is this module's.
"""

import concurrent.futures
import sys
import threading
import time
from pathlib import Path

import lmt
from lmt import align, audio, engines, export, models
from lmt import diarize as diarizer  # `transcribe`'s `diarize` is the on/off switch
from lmt.errors import NoSpeechError

# ASR and diarization side by side, as the architecture's "Run order" says. False runs ASR, then diarization.
PARALLEL = True


def _timed(timings, stage, work):
    start = time.perf_counter()
    try:
        return work()
    finally:
        timings[stage] = time.perf_counter() - start


class _StageLog(dict):
    """`--verbose`'s timings: each stage's line goes to stderr when the stage ends, so a run that fails or is
    killed has already shown how far it got (#643, the Architect's decision of 2026-11-04). ASR and diarization
    end in either order when they run side by side."""

    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()

    def __setitem__(self, stage, seconds):
        super().__setitem__(stage, seconds)
        with self._lock:
            sys.stderr.write(f"lmt: {stage} {seconds:.2f} s\n")
            sys.stderr.flush()


def _model_info(model) -> dict:
    return {"name": model.name, "repository": model.repository, "revision": model.revision}


def transcribe(path, *, engine="kyutai", offline=False, diarize=True, num_speakers=None, min_speakers=None,
               max_speakers=None, timings=None):
    """The transcript of the recording at `path`, with `engine` for ASR and the default diarization models.
    `timings`, if given, gets each stage's wall time in seconds."""
    timings = {} if timings is None else timings
    manifest = models.load_manifest()
    needed = models.diarization_models(manifest) if diarize else []
    # Decode first, so a bad input exits 3 without hashing or downloading a model (g1-stage2.md, P1). The engine
    # loads before anything is written (G4-2).
    samples = _timed(timings, "decode", lambda: audio.decode(path))

    def load_models():
        loaded = engines.load(engine, offline=offline)
        return loaded, models.ensure(needed, offline=offline)

    asr_engine, dirs = _timed(timings, "models", load_models)

    def run_asr():
        # The engine's own rate, decoded from the file again, rather than resampled from 16 kHz (#575, G1-2).
        rate = asr_engine.rate
        if rate == audio.SAMPLE_RATE:
            return asr_engine.transcribe(samples)
        return asr_engine.transcribe(audio.decode(path, rate), rate=rate)

    def run_diarize():
        return diarizer.load(dirs).diarize(samples, num_speakers=num_speakers, min_speakers=min_speakers,
                                           max_speakers=max_speakers)

    turns = None
    if diarize and PARALLEL:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            asr_job = pool.submit(_timed, timings, "asr", run_asr)
            diarize_job = pool.submit(_timed, timings, "diarize", run_diarize)
            words = asr_job.result()
            turns = diarize_job.result()
    else:
        words = _timed(timings, "asr", run_asr)
        if diarize:
            turns = _timed(timings, "diarize", run_diarize)

    if not words:
        raise NoSpeechError(Path(path).name, "no speech found")
    diarization = manifest.get(diarizer.DIARIZATION) if diarize else None
    info = {"asr": dict(asr_engine.info), "diarization": _model_info(diarization) if diarization else None}
    return _timed(timings, "align", lambda: align.build(
        words, turns or None, duration_samples=len(samples), source_file=Path(path).name, models=info,
        lmt_version=lmt.__version__))


def cli_transcribe(args) -> int:
    out_dir, stem = Path(args.output_dir), Path(args.input).stem
    export.check(out_dir, stem, args.formats, overwrite=args.overwrite)

    timings = _StageLog() if args.verbose else {}
    transcript = transcribe(args.input, engine=args.engine, offline=args.offline, diarize=not args.no_diarize,
                            num_speakers=args.num_speakers, min_speakers=args.min_speakers,
                            max_speakers=args.max_speakers, timings=timings)
    paths = _timed(timings, "export", lambda: export.write(transcript, out_dir, stem, args.formats,
                                                            overwrite=args.overwrite))
    for path in paths:
        print(path)
    return 0
