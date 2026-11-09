# Internal design: G1 stage 2, the rest (G1-3 to G1-7, G1-8c, G1-11, G1-13)

| Date (PT) | By | Change |
| --- | --- | --- |
| 2026-10-29 | architect, #402 | P13's finding on PR #403: with the scratch `MPLCONFIGDIR`, matplotlib's "building the font cache" warning reaches stderr on every diarizing run, so G1-11's silence and noise cases see two lines. `diarize.LOGGERS` gains `"matplotlib"` (S3's quiet loggers), and `test_library_writes.py`'s first case imports pyannote inside `diarize._quiet()` and checks that stderr has no matplotlib line. G1-11 and G1-13 are unchanged |
| 2026-10-29 | architect, #391 | P7c's finding on PR #400: a product run writes outside its outputs. New item P13 sets `ORT_DISABLE_TELEMETRY=1` in `asr.py` (onnxruntime 1.31.1's 1DS telemetry, which keeps a device id and an event database and posts to Microsoft's collector) and points `MPLCONFIGDIR` at a directory of the process's own under `TMPDIR`, removed at exit, in `diarize.load` (pyannote.audio's tasks import `matplotlib.pyplot`). P7c waits for it. G1-13 and P7c's test are unchanged |
| 2026-10-29 | architect, #387 | The four export goldens aren't one transcript: `transcript.json` is `test_export.py`'s two-segment `small()`, and `transcript.{txt,srt,vtt}` are `test_export_formats.py`'s five-segment one. P6a's `words` test and P9's golden test now take their JSON from `export.render(test_export_formats.small(), "json")` at test time, in `tmp_path`. No fixture is added or changed, and both items keep their file lists. P9's other golden test checks `transcript.json` against itself. G1-4 is unchanged |
| 2026-10-29 | architect, #349 | Reviewer's findings on #386: a pull request runs tier 1 at most (a75a67b), so P6b's and P7c's PRs show the Developer's local `pytest -m models` result, P6b's with the four ffmpeg commands and their exit codes (G1-4's "the PR shows"); the ffmpeg step and `isolated` true are first confirmed on `main`'s `test-models`, a failure there is `sev:1`, and P10 marks G1-4 and G1-13 only after it. In `g3-stage1.md`, item 2a needs P7b too, and items 1 and 4b need P6a |
| 2026-10-29 | architect, #349 | The Owner's "Break down L and XL items into S items" (2026-10-29): P6 (#349) splits into P6a (the subtitle checks, on the export goldens and a fake ffmpeg) and P6b (G1-4's test, with the real ffmpeg in `test-models`); P7 (#350) into P7a (the guard), P7b (`isolation.py`) and P7c (G1-13's test). Each has its own files, test, Needs and tier. `isolation.py` gains `wrap`, so P7b can test the namespace without the models. G1-4 and G1-13 are unchanged |
| 2026-10-29 | architect, #372 | Reviewer's finding on #383: P12's step 6 could cut before a turn's first word and leave a piece with no words. A cut now also needs the piece to hold a word, and the tests gain both cases |
| 2026-10-29 | architect, #372 | #372's measurement: AMI-ci's product DER is 0.426, mostly missed speech, and segments built from the diarization turns give 0.203. New item P12 makes `align.build` turns-first when there are turns, and keeps today's rule without them. #343 (P2b's reading) waits for it. `architecture.md`'s alignment paragraph changes with it, for the Owner's approval |
| 2026-10-29 | architect, #345 | Reviewer's findings on #370: P11's fresh-process test runs the VAD through `get_speech_timestamps`, which pads to 512 samples; the `fake` fixture also fakes `onnxruntime` (and `faster_whisper.vad` for the fallback); the PR shows the Linux failure with a red ubuntu run on the tests alone, then the green one; the fallback's capture overlapping diarization's load is accepted, with the reasons |
| 2026-10-29 | architect, #345 | P4's finding on PR #364: onnxruntime's warning on Linux breaks G1-11's one stderr line. New item P11 turns onnxruntime's log down to errors in `asr.py`, and P4 waits for it. P4's input and expected result don't change |
| 2026-10-29 | architect, #289 | Reviewer's 01:32 findings on #304: P2 splits into P2a (the runner, on fakes) and P2b (the `eval-ci` job, and the command in the README), and P8 needs only P2a; the three RTFs' timing bases are stated, in P2a and in the README table's note (P8), with `public-api.md`'s wording asked of the Owner in #328; a two-speaker turn's 13.5 s counts the gaps between its own utterances, in whole samples; P7's guard test covers G3's `LMT_NETGUARD_ALLOW=127.0.0.1` cases, and `g3-stage1.md` points to it |
| 2026-10-29 | architect, #289 | Reviewer's findings on #304: P9 builds #286 as `g1-slice.md` decides it (#303), by reference; G1-8c's rounding argument restated for WER, and DER equal to its bound after rounding goes to the Architect; P4's time limit is its own `run_bounded`; G1-4's default formats are tagged through P3; FFmpeg's log is already off |
| 2026-10-29 | architect, #289 | First version: ten Developer items on top of the slice, G1-2's design and #110, with the two-speaker clip's rule for #123 |

This is what a Developer needs to build each item below in one run. It finishes G1's stage 2 for **G1-3, G1-4, G1-5, G1-6, G1-7, G1-8c, G1-11 and G1-13** in `spec/acceptance.md`, each exactly as the spec gives it, with no bound, scoring or fixture loosened. It also adds `lmt.transcript.load`, which G3 assumes, and builds #286 as `g1-slice.md` decides it. G1-2 is `g1-formats.md`'s. It extends the code on `main`: `g1-slice.md`'s pipeline and product run, `g1-stage1.md`'s harness (§4, §5a, §6), #110's CI subset (PR #298), and `criteria.md`'s record. Where this file and those, `architecture.md` or `public-api.md` disagree, they win, and this file is the one to fix. The Reviewer reviews this file. The Architect changes it.

**What doesn't change.** Every bound (G1-8c's 5.0 %, 25.0 % and 25.0 %, inclusive), the scoring (#109's `wer` and `der`), the fixtures (the clip, its encodings, the two-speaker clip and the CI subset, each fixed before it is measured) and the product's defaults. If a measurement misses, the product is what gets fixed. G1-8c's subset bound changes only by the Architect's proposal to the Owner, as the spec says.

## Items, files and order

| Item | What | Needs | Files it creates or changes | Tier |
| --- | --- | --- | --- | --- |
| **P1** | Decode before the models; a truncated WAV is an input error | — | `src/lmt/pipeline.py`, `src/lmt/audio.py`, `tests/test_pipeline.py`, `tests/test_audio.py` | 3 |
| **P2a** | `lmt eval --set ci`: the runner, the worker and the option, on fakes (G1-6's `--set ci` and `--out`) | #110 (PR #298, merged) | `src/lmt/eval/runner.py` (new), `src/lmt/eval/worker.py` (new), `src/lmt/eval/cli.py`, `tests/test_eval_runner.py` (new), `tests/fixtures/eval/fake_worker.py` (new) | 3 |
| **P2b** | The `eval-ci` job's double run and bounds (G1-5, G1-8c, G1-12's CI half), and the command in the README | P2a | `tests/test_eval_ci.py` (new), `.github/workflows/product.yml` (`eval-ci` only), `README.md` (`## Checks`), `.github/scripts/check_readme.py` (`PRODUCT_COMMANDS`) | 3 |
| **P3** | One test per CLI option and per bad input (G1-6); no language option (G1-7) | P1 | `tests/test_g1_6.py` (new), `tests/test_cli.py`, `tests/test_models.py` (tags) | 2 |
| **P4** | Bad input never crashes it (G1-11) | P1, E1 (#296/#299), P11 | `tests/bad_inputs.py` (new), `tests/test_g1_11.py` (new), `tests/test_decode_fuzz.py` (new) | 2 |
| **P5** | The two-speaker product run and G1-3's test | #123's two-speaker clip | `tests/conftest.py`, `tests/test_g1_3.py` (new) | 2 |
| **P6a** | The subtitle checks, on the export goldens and a fake ffmpeg (G1-4's helpers) | — | `tests/subtitle_checks.py` (new), `tests/test_subtitle_checks.py` (new) | 2 |
| **P6b** | G1-4's test on both clips' product runs, with the real ffmpeg | P5, P6a | `tests/test_g1_4.py` (new), `.github/workflows/product.yml` (`test-models` only) | 3 |
| **P7a** | The network guard (G1-13's `socket.connect` block, and G3's) | — | `tests/netguard/sitecustomize.py` (new), `tests/test_netguard.py` (new) | 2 |
| **P7b** | `unshare --net` and the tree snapshot (G1-13's isolation and file compare) | — | `tests/isolation.py` (new), `tests/test_isolation.py` (new) | 2 |
| **P7c** | G1-13's test on the two-speaker clip | P5, P7a, P7b, P13 | `tests/test_g1_13.py` (new) | 2 |
| **P8** | `lmt eval --set full` and `--update-readme`, on fakes (G1-6's last two options), and the README table's RTF note | P2a | `src/lmt/eval/runner.py`, `src/lmt/eval/cli.py`, `src/lmt/eval/readme.py`, `tests/test_eval_full.py` (new), `tests/test_readme_table.py` | 3 |
| **P9** | `lmt.transcript.load`, `jsonschema` at run time, and the code for #286 as `g1-slice.md` decides it | — | `src/lmt/transcript.py`, `src/lmt/schema/transcript.schema.json`, `schema/transcript.schema.json`, `src/lmt/export/__init__.py`, `pyproject.toml`, `uv.lock`, `tests/test_transcript.py`, `tests/test_export.py` | 3 |
| **P10** | The registry: `complete = true` for each criterion whose checks have passed on `main` | the items it marks | `tests/criteria.toml`, `.github/scripts/test_criteria.py` | 2 |
| **P11** | onnxruntime's log down to errors, so a run's stderr is the product's own (P4's finding on #364) | — | `src/lmt/asr.py`, `tests/test_asr.py` | 3 |
| **P12** | Turns-first segments, so the product's DER follows diarization (#372's finding on G1-8c) | — | `src/lmt/align.py`, `tests/test_align.py` | 3 |
| **P13** | No library writes outside the outputs: onnxruntime's telemetry off, and matplotlib's cache in a directory removed at exit (P7c's finding on #400) | — | `src/lmt/asr.py`, `src/lmt/diarize.py`, `tests/test_library_writes.py` (new), `tests/test_diarize.py` | 3 |

**Parallel-safe,** by the files above. Items that share a file are already in sequence through `Needs`: P2a, then P2b and P8 (the runner and `cli.py`). P1 and P3 share no file, but P3's cases rely on decode coming first, so P3 waits for P1. P6b uses P6a's helpers, and P7c uses P7a's guard and P7b's `isolation.py`, so each waits for them. The one pair that may run at the same time and share a file is P2b and P6b, which edit `product.yml` in different jobs (`eval-ci` and `test-models`), so git merges them cleanly; whichever merges second refreshes from `main`. No other two items share a file. Only P10 edits the registry, so the others never conflict there: each item's PR shows its criterion `partial` with every check passing, and P10 turns that into `pass`.

**Order, for G1's CI deadline (2026-10-30, end of day).** The shortest path to the most criteria met. Two Developer runs at a time (`system/caps.toml`):

1. **P1 ∥ P2a.** Both are small and need nothing unmerged.
2. **P2b ∥ P3.** P2b is the first measurement of G1-8c, the criterion most likely to need a product fix or an Owner question, so it goes as soon as P2a merges. If it is held for the Architect, only the `eval-ci` job's check waits: P2a's runner and `--set ci` are already on `main`, and P8 doesn't need P2b. G1-7 needs only P3.
3. **P4 ∥ P8** (P4 once E1 has merged). G1-11 needs P4; P8 completes G1-6. P4's PR (#364) merges after **P11**, rebased onto it.
4. **#123's two-speaker clip**, then **P5**, then P6 and P7 as five items: **P6a ∥ P7a**, then **P6b ∥ P7b**, then **P7c**. P6a, P7a and P7b need nothing unmerged, so any of them may go earlier when a run is free. These carry G1-3, G1-4 and G1-13. **Recommendation to the Coordinator:** #123 lands the two-speaker clip first, as an item of its own (rules, "If the item is bigger than one run"), with LS full, AMI full and the one-hour recording after it, since only stage 3 needs those.
5. **P10**, once the others have passed on `main`. If the deadline nears first, it marks what has passed, and a second P10 run marks the rest.
6. **P9** whenever a run is free: no G1 criterion waits on it, but G3's stage 1 does.

**P12 goes ahead of every other open item** (#372's finding, 2026-10-29). P2b's reading (#343) is blocked by it, and G1-5 and G1-8c with it. It shares no file with any other item.

**P13 goes next, ahead of the rest** (#391's finding, 2026-10-29). P7c's PR (#400) is blocked by it, and G1-13 and stage 2's close with it. Its files are P11's `asr.py`, already merged, and `diarize.py`, which no open item edits.

**What the deadline can carry.** It's 09:46 PT on 2026-10-29. Every item is one Developer run, and most are tier 2 or 3, so roughly an hour of CI each, plus review and the Owner's merge where the path is protected. All eleven fit by the end of 2026-10-30 if #123's two-speaker clip merges by the evening of 2026-10-29 (#110 has merged). The criteria at risk are: G1-3, G1-4 and G1-13, behind #123; and G1-5 and G1-8c, if G1-8c's first reading misses a bound. Next most exposed is G1-6, which waits for P8 behind P2a.

**Every item's local checks:** `uv run --frozen ruff check`, `uv run --frozen pytest`, `uv run --frozen pytest -m models` where it has model tests and the models are in `LMT_CACHE_DIR`, and `python3 -I system/gate/generic.py --base origin/main`. Each tagged test carries its criterion (`criteria.md` §1). Each PR shows `criteria.py --ref refs/pull/<n>/merge` giving its criteria `partial`, with no failed check.

## P1. Decode before the models; a truncated WAV

**`pipeline.transcribe`** decodes first, then calls `models.ensure`. So a bad input exits 3 at once, without hashing or downloading 1.5 GB of models, and G1-6's and G1-11's decode cases need no model. Nothing else moves: `cli_transcribe` still checks `--model` and the outputs before `transcribe`, and `timings` keeps both stages.

**`audio.decode`** gains one check, before `av.open`. FFmpeg decodes a WAV whose data is cut short without an error, so the audio that's left would be transcribed. G1-11 requires exit 3 for "a WAV with a header but truncated data". So, when the file's first 12 bytes are `RIFF<4 bytes>WAVE`, decode walks its chunks with `struct` (`<4sI`: id and size), from offset 12, to the first `data` chunk, skipping each other chunk by `8 + size + (size & 1)`. If the `data` chunk's size isn't 0 or `0xFFFFFFFF` (the sizes streaming writers leave) and its end, `offset + 8 + size`, is past the end of the file, it raises `InputError(str(path), f"truncated: its data chunk declares {size} bytes, the file holds {held}")`. A walk that reaches the end of the file without a `data` chunk leaves the file to PyAV.

**Tests.** `tests/test_audio.py`: the clip's 44-byte header with its first 16,000 bytes of data, and nothing after them, raises `InputError` whose problem starts `truncated`; a complete WAV with a `LIST` chunk before `data` decodes; a header declaring `0xFFFFFFFF` raises no truncation error. `tests/test_pipeline.py`: with `models.ensure` faked to fail the test if called, a missing input exits 3 and the fake is never called.

**Test of the item:** those tests, in the `test` job, and G1-1's test still passing in `test-models`.

## P2a and P2b. `lmt eval --set ci` and the `eval-ci` job

Two items, so that G1-8c's first reading can't hold back the runner. **P2a** builds the runs ("The runs") and their test, `tests/test_eval_runner.py`, in the `test` job. **P2b** builds the `eval-ci` job's steps ("The `eval-ci` job") and `tests/test_eval_ci.py`, on P2a's runner. Each is tested on its own, as "Tests" says.

### The runs (P2a)

Each scored file goes through **the product run**, in a process of its own, as the spec's "Terms" define it: LibriSpeech utterances with `--no-diarize`, and AMI with no option. The architecture has each stage's output "computed once per file and reused". So the same process also records ASR's words and diarization's turns, which give Whisper alone and pyannote alone (`architecture.md`, "Evaluation harness").

**`src/lmt/eval/worker.py`**, run as `python -m lmt.eval.worker STAGES_OUT transcribe INPUT [--no-diarize]`:

- It wraps four functions for this process only: `asr.load` and `asr.Engine.transcribe`, then `diarize.load` and `diarize.Diarizer.diarize`. Each wrapper adds its wall time to `asr_seconds` or `diarize_seconds`, and the two stage wrappers keep what they return.
- It then calls `lmt.cli.main(["transcribe", INPUT, *options])`, unchanged. If that returns 0, it writes `STAGES_OUT` (a temporary file, then renamed): `{"words": [[start, end, text], …], "turns": [[start, end, speaker], …] or null, "asr_seconds": …, "diarize_seconds": … or null}`. It exits with `main`'s code.
- So the product's own code runs, untouched. The wrappers only observe it, and nothing in `lmt` knows about them.

**`src/lmt/eval/runner.py`:**

```python
WORKER = ("-m", "lmt.eval.worker")              # tests point it at tests/fixtures/eval/fake_worker.py
@dataclass(frozen=True)
class Run:  transcript: dict; words: list; turns: list | None; wall_seconds: float
            peak_rss_bytes: int; asr_seconds: float; diarize_seconds: float | None
def run_product(item: Item, work_dir: Path) -> Run
def hypotheses(item: Item, run: Run) -> dict[tuple[str, str, str], Hypothesis]
def evaluate(set_name: str, *, out_dir: Path, determinism=None) -> dict    # writes <out_dir>/<set>.json, returns it
```

- **`run_product`.** Diarization is on when the item has reference turns (`item.ref_turns is not None`), which holds for AMI and not for LibriSpeech. The process is `[sys.executable, *WORKER, <stages file>, "transcribe", str(item.audio)]`, plus `--no-diarize` when diarization is off. It runs in a new empty directory under `work_dir`, with stdout to `DEVNULL` and stderr to a file there. `wall_seconds` runs from just before `Popen` to `os.wait4(pid, 0)`'s return: process start to exit, model loading included (spec, RTF). `peak_rss_bytes` is `wait4`'s `ru_maxrss`, × 1024 on Linux, as is on macOS. That is the counter `/usr/bin/time -l` prints, which G1-10 names. A non-zero exit raises `InputError(str(item.audio), f"lmt transcribe exited {code}: {stderr's last line}")`. The transcript is `<dir>/<audio stem>.json`.
- **`hypotheses`.** `product`: `hypothesis_from_transcript(doc)`, with the run's `wall_seconds` and `peak_rss_bytes`. `whisper-alone`: the words' texts joined by single spaces, no turns, `wall_seconds = asr_seconds`. `pyannote-alone`, only when diarization ran: the raw turns as `score.Turn`s, no text, `wall_seconds = diarize_seconds`.
- **The three RTFs' timing bases differ, and that is stated, not measured away.** The product's is the spec's: process start to exit. Whisper alone's and pyannote alone's is their own stage's time within that same run: the model's loading and its inference, without interpreter start, imports, decode or export. When diarization runs, the two stages run side by side (`PARALLEL`), so each is timed under the other's load. Measuring the alones the product's way would mean running each model again in a process of its own, against `architecture.md`'s "each stage's output is computed once per file and reused", and doubling the Mac's full run. So the basis is stated where readers see the figures: the README table's note (P8), and, by the Owner's decision, the results format in `public-api.md` (#328). No item here waits on #328. CI never fails on RTF (G1-9), so no check depends on it.
- **`evaluate`.** It calls `datasets.fetch(set_name)`, which downloads, caches and verifies the set (G1-5's "downloads and caches"). Then it runs every item in order, one at a time, in a `tempfile.TemporaryDirectory()`, with one stderr line per item: `lmt: eval: <dataset> <id> (<i>/<n>) <wall> s`. It calls `score.score(items, hyps)`, then `report.build(set_name, figures, models, determinism, out_dir=out_dir)` and `report.write(out_dir / f"{set_name}.json", …)`. `models` is the first diarized run's transcript `models`, or the first run's when none is diarized. It writes nothing but the results file, and the temporary directory goes when it's done.
- **The figures** for `ci`, in `score`'s order: LS-ci `product` and `whisper-alone` (WER and RTF); AMI-ci `product` (WER, DER and RTF), `whisper-alone` (WER and RTF) and `pyannote-alone` (DER and RTF). That is G1-5's list: WER on both, DER on AMI-ci, RTF for each system.

**`src/lmt/eval/cli.py`:** `--set ci` creates `--out` if needed (`mkdir(parents=True, exist_ok=True)`), then calls `runner.evaluate("ci", out_dir=Path(args.out))`, and prints the results file's path to stdout. `--set full` stays `NotBuilt` until P8.

### The `eval-ci` job (P2b)

On top of #110's steps, which restore the data cache and run `pytest -m data`:

1. The model cache, the download on a miss and `lmt models verify`: the same three steps as `test-models`, with the same key, and `HF_TOKEN` on the download step only.
2. #110's separate `python -m lmt.eval.datasets fetch ci` step goes. The first run below is what fetches on a cache miss, as G1-5 says the command does.
3. `uv run --frozen lmt eval --set ci`, which writes `results/ci.json`.
4. `cp results/ci.json "$RUNNER_TEMP/ci-1.json"`.
5. `uv run --frozen lmt eval --set ci` again. `report`'s `dirty` excludes `results/`, so the first file doesn't make the second run's tree dirty (`g1-stage1.md` §4).
6. #110's `pytest -m data --criteria-out=criteria-eval-ci.json` step moves here, after the two runs, with `env: LMT_EVAL_CI_FIRST: ${{ runner.temp }}/ci-1.json`. So one pytest run writes the job's one record.
7. Before #110's record upload, an upload of both results files, `if: ${{ !cancelled() }}`, named `eval-ci-results` (the same pinned `actions/upload-artifact`).

**The command in the README** (`g1-stage1.md` §1a, "The stage-2 item that adds the `eval-ci` run adds the command"): `README.md`'s `## Checks` names `uv run --frozen lmt eval --set ci` as inline code, outside fenced code, and `check_readme.py`'s `PRODUCT_COMMANDS` gains that string. S1-4's check then finds it in both the README and `product.yml`. The `readme` job runs that check on the PR.

**Time.** One run is 20 LibriSpeech processes, each loading the model (≈ 10 s) for about 8 s of audio, plus AMI-ci's 300 s at an RTF near 0.5. That's about 7 minutes, so the two come to about 15, inside the job's 45-minute timeout. The PR shows the job's time. If it passes 1.5 times the architecture's 34-minute tier-3 estimate, the Developer says so on the item.

### Tests

- **`tests/test_eval_runner.py`** (P2a; the `test` job, no model):
  - The runner runs `tests/fixtures/eval/fake_worker.py` in place of the worker, on fake items built from `tests/fixtures/eval/ls/` and `ami/` (#109's fixtures). The fake copies the fixture's hypothesis transcript into its directory as `<stem>.json`. It writes stages whose words are that transcript's words, and whose turns are its segments' turns.
  - The results file's figures are then the hand-computed ones: LS WER 0.263158 for `product` and `whisper-alone`, and AMI DER 0.117647 for `product` and `pyannote-alone`. Every figure's `rtf` and `wall_seconds` is a number, and `peak_rss_bytes` is a number for `product` only.
  - Diarization is off exactly for the LibriSpeech items: the fake records its argv. A fake that exits 4 makes `evaluate` raise exit 3, naming the item. `--set ci` and `--out DIR` through `cli.main` write `DIR/ci.json` and print its path (tagged `G1-6`).
  - `worker.main` runs in process, with `asr.load` and `diarize.load` faked as in `tests/test_pipeline.py`. Its stages file holds the fakes' words and turns, and its exit code is `cli.main`'s. With a fake ASR that finds no words, it exits 4 and writes no stages file.
- **`tests/test_eval_ci.py`** (P2b), marked `data`, reads the job's two files: `$LMT_EVAL_CI_FIRST` and `results/ci.json`. Without the variable it skips, saying so, except under `CI`, where it fails.
  - **G1-5 and G1-12** (tagged both): both files exist with `set` `"ci"`, they hold the figures listed above with those values non-null, and `report.same_accuracy(first, second)` is true. On failure it prints both stripped files' unified diff.
  - **G1-8c** (tagged): from `results/ci.json`'s `product` figures, LS-ci WER ≤ 0.050, AMI-ci WER ≤ 0.250 and AMI-ci DER ≤ 0.250. Each bound is a constant whose comment cites the spec. `score._figure` rounds `wer` and `der` to 6 decimal places, so rounding can lower a value by up to 5 × 10⁻⁷. The two rates need different rules for that:
    - **WER** is `E/N`, whole errors over `N` reference words. If `E/N > 1/20`, then `20E ≥ N + 1`, so it exceeds 0.05 by at least `1/(20N)`. That is more than 5 × 10⁻⁷, and survives rounding, only while `N < 100,000`. For 0.25 the margin is `1/(4N)`, so `N < 500,000`. LS-ci's 20 utterances and AMI-ci's 300 s hold on the order of a thousand reference words between them, far below both. So for WER, the rounded value `≤` its bound is exactly the spec's inclusive test. A comment beside the WER bounds states this, and that it must be redone if a CI subset ever nears 100,000 reference words.
    - **DER** is a ratio of durations, with no such spacing: a true 0.2500004 rounds to 0.250000. So AMI-ci's DER passes only when the rounded value is **below** 0.250. A rounded value equal to 0.250 fails, with the message "DER equals its bound after rounding, so a pass can't be told from a miss", and goes to the Architect as a miss does (below). That can't pass a miss. It can hold back a true pass of exactly 0.250, which the Architect then settles.
  - Every figure goes to the test's output and to `$GITHUB_STEP_SUMMARY`, pass or fail.

**Test of P2a:** `tests/test_eval_runner.py`, in the PR's `test` job (tier 3, for `src/lmt/eval/`). Its PR shows G1-6 `partial`, with every check passing.

**Test of P2b:** `tests/test_eval_ci.py` in the PR's `eval-ci` job (tier 3, for `product.yml`), with the summary's figures and `criteria-eval-ci` giving G1-5 and G1-8c `passed`, and the `readme` job passing. **If G1-8c misses a bound,** or its DER equals the bound after rounding, while the double run passes, the Developer reports the figures on the item and holds it for the Architect (`needs-decision:architect`), without changing the bounds or the subset. The Architect then decides between a product fix and the spec's route: a subset bound proposed to the Owner, only if the full set meets G1-8, which needs the Mac's run.

## P3. G1-6's tests, and G1-7's

**`tests/test_g1_6.py`** (the `test` job, no model), tagged `G1-6`. It reuses `tests/test_pipeline.py`'s fakes (`from test_pipeline import Fakes`), and has one test per option, each checking the option's effect:

| Option | Effect checked |
| --- | --- |
| `-o`, `--output-dir` | The outputs land in `DIR`, and none in the working directory. |
| `-f`, `--formats` | `-f srt,json` writes exactly those two, and prints them in that order. |
| `--num-speakers` | The fake diarizer gets `num_speakers=3`, and `min_speakers` and `max_speakers` `None`. |
| `--min-speakers`, `--max-speakers` | Each reaches the diarizer, alone and together. |
| `--no-diarize` | Diarization is never loaded, every segment is `S1`, and `models.diarization` is `null`. |
| `--model` | With a test manifest of two ASR models, `asr.load` gets the named one's directory, and the JSON's `models.asr.name` is that name. |
| `--offline` | A missing model file exits 5, with the download fake never called. With every file present, the run succeeds without it. |
| `--overwrite` | An existing output is replaced. Without the option, it exits 2 and the file is unchanged. |
| `-v`, `--verbose` | Six stage lines on stderr, and none without it. |

The other commands' options are tagged where their tests already are: `models download --model`, `list --bytes` and `verify` in `tests/test_models.py`; and `--version` and `--help` already in `tests/test_cli.py`. P3 also tags `tests/test_cli.py`'s `test_default_formats` `G1-4`, for P6b (below). `eval --set ci` and `--out` are P2a's; `--set full`, `--update-readme` and the tag on `eval --check-readme` in `tests/test_readme_table.py` are P8's, which edits that file.

**Bad input,** through `lmt transcribe` in a subprocess (`conftest.run_lmt`), with no model needed since P1:

| Case | Exit | The one stderr line names |
| --- | --- | --- |
| A missing file | 3 | its path |
| A directory | 3 | its path |
| An unknown option, `--language en` | 2 | `--language` |
| A bad value, `--num-speakers 0` | 2 | `--num-speakers` |
| `clip.json` already in `-o DIR`, without `--overwrite` | 2 | that path |
| An output directory with mode `0o500` | 3 | the directory |

Each prints exactly one line on stderr, starting `lmt: error: `, with no `Traceback`, and the output directory holds no new file. The last case skips, saying so, when the tests run as root, who can write anywhere.

**G1-7** (`tests/test_cli.py`, tagged `G1-7`): no option string of any parser that `build_parser()` builds, at any depth, contains `lang`. With `test_asr.py`'s decode language and `test_manifests.py`'s sources, both already tagged, that is G1-7's test. The Reviewer's reading of `public-api.md` for a language option happens on P10's PR.

**Test of the item:** the tests above, in the `test` job.

## P4. Bad input never crashes it (G1-11)

### `tests/bad_inputs.py`

G2 calls these too (`g2-stage1.md`):

```python
SOURCES = ("wav", "flac", "mp3", "m4a", "mp4", "mov")    # tests/fixtures/clip.<suffix>
OPS = ("flip", "truncate", "splice")
E2E_MUTATIONS = (0, 7, 14, 21, 28)
def mutation(i: int) -> tuple[str, bytes]               # (suffix, bytes)
def build(name: str, directory: Path) -> Path           # one end-to-end input, by its name below
def run_bounded(argv, *, cwd, timeout=120) -> subprocess.CompletedProcess
```

- **`run_bounded`** is `subprocess.run([sys.executable, "-m", "lmt", *argv], cwd=cwd, capture_output=True, text=True, check=False, timeout=timeout)`: `conftest.run_lmt` with a time limit. It lives here, not in `tests/conftest.py`, which is P5's file, so P4 shares no file with P3 or P5. `subprocess.TimeoutExpired` propagates, and fails the test.

- **`mutation(i)`** reads `clip.<SOURCES[i % 6]>` and applies `OPS[(i // 6) % 3]`, with `rng = numpy.random.default_rng(i)`. **flip:** `n = rng.integers(1, 33)` positions from `rng.integers(0, len, n)`, each byte XORed with `rng.integers(1, 256)`. **truncate:** the first `rng.integers(0, len)` bytes. **splice:** `n = rng.integers(1, 4097)`, `p, q = rng.integers(0, len − n, 2)`, and bytes `[p, p + n)` replaced by `[q, q + n)`. So `E2E_MUTATIONS` covers a flipped WAV, a truncated FLAC, a spliced MP3, a flipped M4A and a truncated MP4.
- **The end-to-end inputs** (`build`): `empty.wav` (0 bytes); `zero.wav` (the `wave` module, 16 kHz mono 16-bit, no frames); `truncated.wav` (`clip.wav`'s first 44 + 32,000 bytes, so its header declares 56.565 s and it holds 1 s); `random.wav`, `random.mp3` and `random.m4a` (65,536 bytes from `default_rng(1)`, `(2)` and `(3)`); `text.mp4` (a line of English text); `video-only.mp4` (three 64×64 black frames in `mpeg4`, written with PyAV, with no audio stream); `notes.txt`; `notes.docx` (a zip with `[Content_Types].xml` and `word/document.xml`); `silence.wav` (60 s of zeros); `noise.wav` (60 s of white noise, `default_rng(4).standard_normal`, scaled to an RMS of 10^(−60/20) of full scale, × 32,767, rounded and clipped to 16 bits); and `mutation-<i>.<suffix>` for each of `E2E_MUTATIONS`.

### Tests

- **`tests/test_g1_11.py`**, tagged `G1-11`, one test per input, each run as `run_bounded(["transcribe", <its absolute path>], cwd=<a fresh empty directory>)`, so with a 120 s limit. A timeout fails the test.
  - **The decode cases**, in the `test` job: every input except silence, noise and the mutations. Each exits 3.
  - **The rest**, marked `models`, in `test-models`. `silence.wav` and `noise.wav` exit 4. A mutation exits 3 or 4, or exits 0.
  - **For exits 3 and 4,** stderr is exactly one line, starting `lmt: error: `, holding the input's file name and a problem after it. stderr contains no `Traceback`, and the directory is still empty.
  - **For exit 0,** the four outputs exist and the JSON validates against the schema.
- **`tests/test_decode_fuzz.py`** (the `test` job), tagged `G1-11`, parametrized over `range(200)`. Mutation `i` is written to a temporary file with its suffix and passed to `audio.decode` in the test's process. It returns a one-dimensional float32 array with at least one sample, or raises `InputError` (exit code 3). Any other exception fails, naming `i`. The time is measured with `perf_counter` and must be ≤ 10 s. `faulthandler.dump_traceback_later(60, exit=True)` around each call turns a hang into a failure with a traceback, rather than a job timeout.

**Test of the item:** the tests above in the `test` and `test-models` jobs of the PR. The PR lists each end-to-end case's exit code and each mutation's outcome. **If a case fails,** for example random bytes that FFmpeg decodes, or library output on stderr, that is a product finding. The Developer reports it on the item for the Architect, who designs the fix in the product: in decode, or in the stage whose library prints (P11). Neither the input nor the expected code changes.

## P5. The two-speaker product run and G1-3

**`tests/conftest.py`** gains `TWO_SPEAKERS = ROOT / "tests" / "fixtures" / "two_speakers.wav"` and the session fixture `two_speakers_run`, made exactly as `clip_run` is: `lmt transcribe <its absolute path>`, with no option, in a fresh directory. G2's and G3's designs assume this name.

**`tests/test_g1_3.py`**, marked `models` and tagged `G1-3`. It uses the run's `two_speakers.json` and the clip's committed RTTM from #123:

- The run exits 0. `speakers` has exactly two entries, and the segments use both.
- **Each hypothesis word** (every segment's `words`, with its segment's `speaker`) goes to a reference speaker. That is the RTTM turn holding the word's midpoint, or else the nearest turn by gap, the earlier on a tie. No word is dropped.
- **For each reference speaker,** the label most of their words carry has at least 90 % of their words, and the two speakers' majority labels differ. A reference speaker with no words fails.
- Each speaker's word count and majority share go to the output and `$GITHUB_STEP_SUMMARY`, pass or fail.

### The two-speaker clip's rule (for #123)

`g1-stage1.md` §5b describes the clip but doesn't fix which utterances it uses. This rule fixes them now, before anything is measured on the clip. #123 applies it, and records the result in a comment in `sets.toml` as S1 did, with the clip's resulting duration: at least 55.5 s (item 4), and longer when a turn's last utterance runs past 13.5 s. The rule stands whatever that duration is, since it is fixed before measurement:

1. **The speakers.** From `LibriSpeech/SPEAKERS.TXT` (a member to add to the archive source), the test-clean speaker with the lowest id whose sex is `F`, and the one with the lowest id whose sex is `M`.
2. **The turns** alternate, F, M, F, M. Each speaker's utterances are taken in ascending id order, continuing from where that speaker's previous turn stopped. A turn is the shortest run of them that lasts at least 13.5 s, as item 4 measures it.
3. **The pieces** are the turns' utterances in order, each whole (`start = 0.0`, `end` = its duration), joined with `gap = 0.5`, by S1's recipe.
4. **How long a turn lasts:** from its first piece's start to its last piece's end in the clip. That is its utterances' durations plus the 0.5 s gaps *between its own utterances*, so a turn of `k` utterances counts `k − 1` gaps. The gap after a turn's last utterance, before the next speaker, isn't counted. An utterance's duration is its decoded sample count at 16 kHz over 16,000. So the test is exact in whole samples: the sum of its `k` utterances' sample counts, plus `8,000 × (k − 1)`, is at least 216,000. The clip is then the four turns plus the three 0.5 s gaps between them, at least 4 × 13.5 + 3 × 0.5 = 55.5 s.
5. **The references.** `tests/fixtures/two_speakers.rttm` has one `SPEAKER two_speakers 1 <start> <duration> <NA> <NA> <LibriSpeech speaker id> <NA> <NA>` line per piece, at its offset in the clip, with times to the millisecond. `two_speakers.txt` holds the texts in order, as `clip.txt` does.

## P6a and P6b. The exports' checks (G1-4)

Two items. **P6a** builds the helpers below and tests them on the committed export goldens, with a fake `ffmpeg`, so it needs no model and no ffmpeg. **P6b** runs them, with the real ffmpeg, on the two clips' product runs: that is G1-4's test, exactly as the spec gives it.

### `tests/subtitle_checks.py` (P6a)

G3's items call these names:

```python
def check_srt(path)          # srt.parse, strict; the ffmpeg re-encode to srt
def check_vtt(path)          # webvtt.read; the ffmpeg re-encode to webvtt
def ffmpeg_reencode(path, fmt)   # the spec's command, exactly; asserts exit 0 and empty stdout and stderr
def words(path, fmt, labels) -> list[str]
```

- **`check_srt`:** `list(srt.parse(text))` with its default strictness, which raises on anything it can't parse, and at least one cue. Then `ffmpeg -v error -i <file> -map 0:s:0 -c:s srt -f srt -y /dev/null`.
- **`check_vtt`:** `webvtt.read(path)`, with at least one caption. Then the same command with `webvtt` in place of both `srt`s.
- **`ffmpeg_reencode`** fails, saying so, when `shutil.which("ffmpeg")` is `None`: it never skips.
- **`words`** gives each format's words in order. For `json`, each segment's `text` split on white space. For `txt`, each line after its `] <label>: `. For `srt`, each cue's lines joined, after its `<label>: `. For `vtt`, each cue's text after its voice tag and its `<label>: `, with character references decoded (`html.unescape`).

**`tests/test_subtitle_checks.py`** (P6a; the `test` job, no model), tagged `G1-4`. It uses `tests/fixtures/export/transcript.{txt,srt,vtt}`, whose labels include `José & Ana`, escaped in the WebVTT. Those three are `test_export_formats.py`'s `small()`, while the committed `transcript.json` is `test_export.py`'s two-segment `small()`. So the test's JSON is `export.render(test_export_formats.small(), "json")`, written to `tmp_path`, and the committed `transcript.json` isn't used. The JSON renderer's bytes are already checked by `test_export.py`'s golden. Its fake `ffmpeg` is an executable `sh` script in `tmp_path`, put first on `PATH` with `monkeypatch`, that writes its arguments, one per line, to a file beside it. Each case sets what it prints and how it exits.

- **The goldens pass.** With the silent fake exiting 0, `check_srt` and `check_vtt` pass on the goldens. The fake's recorded arguments are exactly `-v error -i <file> -map 0:s:0 -c:s srt -f srt -y /dev/null`, and the same with `webvtt` in place of both `srt`s.
- **`ffmpeg_reencode` fails** (an `AssertionError`, or `pytest.fail`, never a skip) when the fake exits 1, when it prints a line on stdout, when it prints a line on stderr, and when no `ffmpeg` is on `PATH` (`PATH` set to an empty directory). Each failure's message names the file and the command.
- **The parsers are strict.** An SRT whose first timestamp reads `00:00:0x,480` fails `check_srt`, and so does an SRT with no cue. A WebVTT without its `WEBVTT` line fails `check_vtt`, and so does one with no cue.
- **`words`** gives the same list for the three goldens and that JSON, with the JSON's labels, and that list is the JSON's segments' texts split on white space. `José & Ana`'s cue gives `Yes,`, `the`, `Q&A`, `<draft>`, … in the WebVTT, unescaped.

**Test of P6a:** `tests/test_subtitle_checks.py`, in the PR's `test` job (tier 2, for `tests/`).

### G1-4's test (P6b)

**`tests/test_g1_4.py`**, marked `models` and tagged `G1-4`, runs for both `clip_run` and `two_speakers_run`. Those runs pass no option, so they write the default formats. The spec's run names `--formats txt,srt,vtt,json`, and the two are the same run only because the default is exactly those four, in that order. `tests/test_cli.py::…test_default_formats` checks that, and P3 tags it `G1-4` (P3 already edits `tests/test_cli.py`, so P6b doesn't touch it). Running the defaults keeps one product run per clip, which G1-13's byte comparison also uses. The test checks:

1. stdout lists four paths, and `<stem>.txt`, `.srt`, `.vtt` and `.json` exist.
2. The JSON validates against `schema/transcript.schema.json` with `jsonschema.Draft202012Validator`.
3. Every segment has a speaker label and timestamps in every format. In the JSON, each segment has `start`, `end` and a `speaker` among `speakers`' ids. In the text file, one line per segment, each `[HH:MM:SS] <label>: `. In the SRT, each cue has `start < end`, and its first line starts `<label>: `. In the WebVTT, each cue starts `<v <label>>` and then `<label>: `, both escaped as `public-api.md` says. Here `<label>` is always one of the JSON's labels.
4. `check_srt` and `check_vtt`.
5. `words(...)` is the same list for all four formats.

Each ffmpeg command, as run, and its exit code are printed, and go to `$GITHUB_STEP_SUMMARY` when it is set.

**`product.yml`, `test-models`:** a step before pytest, `command -v ffmpeg || { sudo apt-get update && sudo apt-get install -y --no-install-recommends ffmpeg; }`, then `ffmpeg -version | head -n 1` to the log. The ffmpeg CLI is only CI's checking tool, never shipped, so G1-15's inventory doesn't change.

**Test of P6b.** A pull request runs tier 1 at most (`tiers.py`'s `PULL_REQUEST_MAX_TIER`), so the PR's CI runs neither `test-models` nor this test. The PR shows instead:
- the Developer's local `uv run --frozen pytest -m models` result, with `tests/test_g1_4.py` passing on both clips;
- the four ffmpeg commands (SRT and WebVTT, for each clip's product run) and their exit codes, all 0, from `uv run --frozen pytest -m models -rP tests/test_g1_4.py`, whose passed-test output holds what the test printed. That is G1-4's "the PR that adds the test shows both commands exiting 0 on the fixtures' files".
- **If the Mac has no ffmpeg CLI,** `ffmpeg_reencode` fails, saying so, and the test can't pass. A run can't install software on the Mac, so the Developer escalates to the Owner: "P6b needs an ffmpeg CLI on the Mac's `PATH` for its local run. 1. Install it with Homebrew (`brew install ffmpeg`), recommended. 2. Put another build on `PATH`, named in your answer." The PR waits for the answer, then shows the commands and their exit codes. G1-4's sentence isn't met any other way.

It fails without the change: on `main` there is no `tests/test_g1_4.py`, so G1-4 has no check of the exports.

**First confirmed on `main`, after the merge:** the ffmpeg install step and the test in `main`'s `test-models` (tier 3, for `product.yml`), with the commands in its summary. If that run fails, it is `sev:1` (a broken `main`): revert first, as the next Developer item, then fix the cause. P10 marks G1-4 only after `main`'s `test-models` has passed with this test.

**If a check fails** on a product run (a cue ffmpeg rejects, say, or words that differ between formats), that is a product finding: the Developer reports it on the item for the Architect, and the check doesn't change.

## P7a, P7b and P7c. The network and files (G1-13)

Three items. **P7a** is the guard and its test, and **P7b** is `isolation.py` and its test, both in the `test` job with no model. **P7c** puts them together on the two-speaker clip: that is G1-13's test, exactly as the spec gives it.

### The guard (P7a)

**`tests/netguard/sitecustomize.py`**, active only when `LMT_NETGUARD_LOG` is set. It wraps `socket.socket.connect` and `connect_ex`. A connection to an address not in `LMT_NETGUARD_ALLOW` (comma-separated, empty by default) appends one line to the log, `<family> <address>`, and raises `OSError(errno.ENETUNREACH)`. Every family counts, `AF_UNIX` included. It is put on `PYTHONPATH` for a subprocess, so it applies to `lmt` without changing it. G3's guard (`g3-stage1.md`, "The network guard") is this file, with `LMT_NETGUARD_ALLOW=127.0.0.1`.

**`tests/test_netguard.py`** (the `test` job), tagged `G1-13`. It is the guard's one test, G1's and G3's (`g3-stage1.md`, "The network guard"). The guard refuses before the system tries, so no case depends on the machine's interfaces. Each case is a subprocess, `[sys.executable, "-c", <the connection>]`, with `PYTHONPATH` set to `tests/netguard` (absolute) and `LMT_NETGUARD_LOG` to a file in `tmp_path`:
- **With the default empty allowance,** connections to `127.0.0.1`, `::1` and `192.0.2.1:80` are each logged and refused.
- **With `LMT_NETGUARD_ALLOW=127.0.0.1`** (G3's setting), a connection to a closed port on `127.0.0.1` is refused by the system (`ECONNREFUSED`) and not logged, and connections to `127.0.0.2`, `::1` and `192.0.2.1:80` are each logged and refused with `ENETUNREACH`.
- **`connect_ex`** to `192.0.2.1:80` is logged and refused too, and an `AF_UNIX` connection to a path in `tmp_path` is logged and refused.
- **Without `LMT_NETGUARD_LOG`,** the guard is off: a connection to a closed port on `127.0.0.1` gets `ECONNREFUSED`, and no log file is made.
- Only the `::1` cases are skipped, saying so, where an IPv6 socket can't be made.

**Test of P7a:** `tests/test_netguard.py`, in the PR's `test` job (tier 2, for `tests/`).

### `tests/isolation.py` (P7b)

G2's and G3's designs assume these names:

```python
def snapshot(*dirs) -> dict[str, tuple]     # absolute path -> ("file", size, sha256) | ("dir",) | ("link", target), recursive
def wrap(command, *, env) -> tuple[list[str], bool]   # the command as run_isolated runs it, and whether it is isolated
def run_isolated(argv, *, env, cwd) -> Isolated     # CompletedProcess fields, plus .isolated: bool
```

- **`snapshot`** walks each directory with `os.walk(followlinks=False)`, and records every entry under it, the directory itself excluded. A symbolic link is recorded as a link with its `os.readlink` target, and never followed. A file's SHA-256 is read in 1 MiB blocks.
- **`wrap`.** Where `sudo -n true` succeeds and `unshare` and `setpriv` are on `PATH` (the CI runner), it gives `sudo -n unshare --net -- setpriv --reuid=<uid> --regid=<gid> --clear-groups -- env -i <env as K=V …> <command>`, with `True`. So the command has no network interface but a down loopback, and runs as the runner's own user. Elsewhere it gives `command` unchanged, with `False`, and the caller runs it with `env` alone.
- **`run_isolated`** is `wrap([sys.executable, "-m", "lmt", *argv], env=env)`, run with `subprocess.run(…, env=env, cwd=cwd, capture_output=True, text=True, check=False)`.

**`tests/test_isolation.py`** (the `test` job, no model), tagged `G1-13`:
- **`snapshot`:** a tree in `tmp_path` with a file, an empty file, a subdirectory holding a file, and a link to a path that doesn't exist gives exactly the expected dictionary, with each file's size and SHA-256 computed in the test. Snapshotting it twice gives equal results. Changing one byte of a file, adding a file, removing one, or retargeting the link each changes exactly that entry.
- **`wrap`,** with `command = [sys.executable, "-c", <code>]` and `env` holding `PATH`, `HOME` (set to `tmp_path`) and `LMT_TEST_MARK=1`, run as `run_isolated` runs it. The child prints its `os.environ` as JSON and its `os.getuid()`. Its environment holds `LMT_TEST_MARK` and not `LMT_TEST_PARENT`, a variable the test sets in its own environment with `monkeypatch`. Its uid is the test's.
- **Where `wrap` isolates,** a child that calls `socket.create_connection(("192.0.2.1", 80), timeout=3)` fails with `OSError`. That shows the namespace has no route. **Under `CI` on Linux**, `wrap` must isolate, and the test fails if it doesn't. Elsewhere the isolated case skips, saying so.
- **`run_isolated(["--version"], …)`** exits 0, and its stdout holds `lmt.__version__`.

**Test of P7b:** `tests/test_isolation.py`, in the PR's `test` job (tier 2, for `tests/`), with the ubuntu run's isolated case passing, not skipped.

### G1-13's test (P7c)

**`tests/test_g1_13.py`**, marked `models`, tagged `G1-13`:

1. Under `tmp_path`: empty `home`, `tmp`, `xdg` and `work` directories, and `net.log` beside them, outside every watched directory.
2. `env`: `PATH` (the job's), `HOME`, `TMPDIR` and `XDG_CACHE_HOME` set to the three, `LMT_CACHE_DIR` set to the job's model cache (`models.cache_dir()`), `PYTHONPATH=tests/netguard` (absolute), `LMT_NETGUARD_LOG` set to `net.log`, and `LANG=C.UTF-8`. Nothing else: no `HF_TOKEN`.
3. `before = snapshot(home, tmp, xdg, work, cache)`. Then `run_isolated(["transcribe", <two_speakers.wav, absolute>], env=env, cwd=work)`, which is the product run, writing to `work`.
4. It exits 0. Under `CI`, `isolated` is true. `net.log` doesn't exist or is empty.
5. `after = snapshot(...)`. The only difference from `before` is four new files, `work/two_speakers.{txt,srt,vtt,json}`. Nothing under `home`, `tmp`, `xdg` or the cache is new, changed or gone, the cache compared by path, size and SHA-256.
6. Each of the four is byte-identical to `two_speakers_run`'s, the run with the network up.

**Test of P7c.** A pull request runs tier 1 at most, so the PR's CI doesn't run this test. The PR shows the Developer's local `uv run --frozen pytest -m models` result, with `tests/test_g1_13.py` passing: the guard's log empty, the snapshot's only difference the four outputs, and the bytes equal. On the Mac, `wrap` can't isolate (no `unshare` or `setpriv`), so `isolated` is false there, and the PR says so. It fails without the change: on `main` there is no `tests/test_g1_13.py`.

**First confirmed on `main`, after the merge:** the test in `main`'s `test-models` (tier 2, for `tests/`), with `isolated` true, which is G1-13's `sudo unshare --net` check. If that run fails, it is `sev:1` (a broken `main`): revert first, as the next Developer item, then fix the cause. P10 marks G1-13 only after `main`'s `test-models` has passed with this test and `isolated` true. **If a library writes a file** (a config or cache under `home`, say) **or opens a socket,** that is a product finding. The Developer reports the path or address on the item for the Architect. The test doesn't allow it. The first such finding (#391) is P13's, and P7c's PR merges only after P13.

## P8. `lmt eval --set full` and `--update-readme`

G1-6 needs a test of every documented option, and these two are `eval`'s last. The Owner's run of them is stage 3's. They're built now, on P2a's runner, and tested on fakes.

- **`runner.evaluate_full(out_dir, *, update_readme)`.** It runs `evaluate("ci", …)` twice, into a temporary directory, then sets `determinism = {"runs": 2, "identical": report.same_accuracy(first, second)}` (G1-12's Mac half). Then it runs `evaluate("full", out_dir=out_dir, determinism=determinism)`, over the sets #123 adds (LS full, AMI full and the one-hour recording), one file at a time (G1-9). With `update_readme`, it ends with `readme.update(Path("README.md"), out_dir / "full.json")`. A tree with uncommitted changes gives `dirty: true`, so `readme.render` refuses the update with exit 3, after `full.json` is written.
- **`cli.py`:** `--set full` calls it and prints `full.json`'s path.
- **The README table's RTF note** (P2a, "The three RTFs' timing bases"). `readme.render` adds one paragraph after the table, when the file has figures: "RTF is wall-clock time over audio duration. For the product, it runs from process start to exit, model loading included. Whisper alone and pyannote alone come from that same run: each is its own stage's model loading and inference, without start-up, decoding or export, and, with diarization on, while the other stage runs beside it. So the three RTFs aren't like for like." The placeholder's render doesn't change, so the committed README still passes `--check-readme`.
- **`tests/test_readme_table.py`:** its expected string for a file with figures gains the note, and its `--check-readme` test is tagged `G1-6`.
- **`tests/test_eval_full.py`** (the `test` job, tagged `G1-6`), with `datasets.fetch` faked for `ci` and `full`, and P2a's fake worker. `--set full` writes `full.json` with `determinism` `{"runs": 2, "identical": true}`. With the fake changed to give different words on the second `ci` run, `identical` is `false`. `--set full --update-readme`, in a temporary git repository with a committed README, rewrites the table between the markers, and `--check-readme` then exits 0.

**Test of the item:** those tests, and the `readme` job's `--check-readme`, on the PR.

## P9. `lmt.transcript.load`, `jsonschema` at run time, and #286's code

**`load(path) -> Transcript`** (`g3-stage1.md` assumes it):

1. It reads the bytes. An `OSError` is `InputError(str(path), "can't read: <strerror>")`.
2. It parses them as UTF-8 JSON. A failure is `InputError(str(path), "not JSON: <msg>")`, and a top level that isn't an object is `"not a transcript"`.
3. If `schema_version` is a string whose part before the first `.` isn't `1`, that is `InputError(str(path), f"schema version {v} isn't supported; this lmt reads 1.x")`. This check comes before the schema's, so the message is clear.
4. It calls `schema.validate(doc)`, and re-raises its error as `InputError(str(path), e.problem)`.
5. It returns `from_dict(doc)`.

**`jsonschema` at run time.** It moves from the `dev` group to `[project] dependencies`, at the lock's version (`jsonschema>=<locked major.minor>`), and `uv lock` refreshes `uv.lock`. Its tree is already locked and licence-checked as part of `dev`, so the inventory doesn't change. The PR shows `check_licences.py` passing on both platforms.

**#286's code.** #286 is decided in `g1-slice.md` S4 (PR #303), and P9 builds that text as it stands; this file doesn't restate it. That is: "The schema"'s patterns and its "Every pattern ends with `(?![\s\S])`" rule, in both schema copies; `write`'s `os.open(…, 0o666)` and "An output's mode", in `src/lmt/export/__init__.py`; and S4's Tests for both, in `tests/test_export.py`. Where S4 and this paragraph differ, S4 wins.

**Tests.** `tests/test_transcript.py`:
- `load` of the committed `tests/fixtures/export/transcript.json` gives `test_export.py`'s `small()` and renders JSON byte-identical to that file.
- `test_export_formats.py`'s `small()`, written as JSON to `tmp_path` and read back with `load`, renders JSON, txt, srt and vtt byte-identical to the written file and to `transcript.{txt,srt,vtt}`. (The committed `transcript.json` is a different, two-segment transcript, so it can't be compared with those three.)
- A missing file, a directory, `{` alone, `[]`, a document without `segments`, and `schema_version` `"2.0"` each raise `InputError` naming the path, with the problems above.

`tests/test_export.py`: every #286 case in `g1-slice.md` S4's Tests that the file doesn't already have.

**Test of the item:** those tests, in the `test` job, and the licence check passing.

## P10. The registry

`tests/criteria.toml` gains a block for each criterion whose checks have all passed on `main`, each with a comment naming its tests, as `[G1-1]` and `[G1-2]` have:

| Criterion | Complete when | Its tests |
| --- | --- | --- |
| G1-3 | P5 | `tests/test_g1_3.py` |
| G1-4 | P3, P6a and P6b, with `main`'s `test-models` passing `tests/test_g1_4.py` | `tests/test_g1_4.py`, `tests/test_subtitle_checks.py`, `tests/test_cli.py` (`test_default_formats`) |
| G1-5 | P2b | `tests/test_eval_ci.py` |
| G1-6 | P3, P2a and P8 | `tests/test_cli.py`, `tests/test_g1_6.py`, `tests/test_models.py`, `tests/test_readme_table.py`, `tests/test_eval_runner.py`, `tests/test_eval_full.py` |
| G1-7 | P3 and #110, with the Reviewer's reading of `public-api.md` on this PR | `tests/test_asr.py`, `tests/test_manifests.py`, `tests/test_cli.py` |
| G1-8c | P2b | `tests/test_eval_ci.py` |
| G1-11 | P4 | `tests/test_g1_11.py`, `tests/test_decode_fuzz.py` |
| G1-13 | P7a, P7b and P7c, with `main`'s `test-models` passing `tests/test_g1_13.py` with `isolated` true (its `owner` line stays) | `tests/test_g1_13.py`, `tests/test_netguard.py`, `tests/test_isolation.py` |

**G1-12 stays incomplete.** Its Mac half, the two runs before the full run, is read from `results/full.json` by stage 3's `check_results.py` (`criteria.md` §2).

`.github/scripts/test_criteria.py`'s `RealSpecTest.test_real_registry_loads` lists the complete criteria, and gains the same IDs. #300 says `against_base.py` refuses a change to that file. If #300 isn't fixed by then, the PR says so for the Reviewer.

**Test of the item:** `tests/test_criteria.py` and `.github/scripts/test_criteria.py`. `criteria.py` on `main`'s latest records then gives `pass` for each criterion marked, and the PR shows that output.

## P11. onnxruntime's log down to errors

**The finding** (#345, PR #364's `test-models`, run 40946404376). On the Linux runner, `silence.wav` and `noise.wav` exit 4 with the right error line, but onnxruntime prints `[W:onnxruntime:Default, device_discovery.cc:95 GetPciBusId] Skipping pci_bus_id …` on stderr ahead of it, so stderr has two lines. onnxruntime (1.31.1 in `uv.lock`) is faster-whisper's, for the Silero VAD that `vad_filter=True` turns on. The line comes from its default logger, when its environment is created and discovers devices. faster-whisper's own `SessionOptions.log_severity_level` covers only the session's logger, and Python's `logging` and `warnings`, which `diarize._quiet` sets, never see it. macOS prints no such line, so P4 passes there.

**`asr.quiet_onnxruntime()`**, called first in `asr.load`, before `WhisperModel`: `import onnxruntime`, then `onnxruntime.set_default_logger_severity(3)` (errors and fatal only). onnxruntime's own errors still print. It keeps no flag: every call does the same, and a second call is harmless, since the severity is the same and `get_vad_model` (below) is cached. faster-whisper creates the VAD session later, inside `transcribe`, so the severity is set before onnxruntime's environment discovers devices. Nothing else changes: no setting of `transcribe`, no threads, no model.

**If the line still prints** on Linux with the severity set (the test below says so: for example, onnxruntime creates its environment, and discovers devices, inside that call or at `import`), `quiet_onnxruntime` also does this, in the same item. Around the import, the severity call and `faster_whisper.vad.get_vad_model()` (cached, so `transcribe` reuses that session), it flushes `sys.stderr` and points file descriptor 2 at a `tempfile.TemporaryFile`. Afterwards, in a `finally`, it restores descriptor 2 and writes back to `sys.stderr` every captured line that doesn't start with `[V:onnxruntime`, `[I:onnxruntime` or `[W:onnxruntime`. So only onnxruntime's verbose, info and warning lines are dropped. Its errors, and anything else, still print, and an exception still propagates. The PR says which of the two it needed, with the CI run's link.

**The capture runs alongside diarization, and that's accepted.** `asr.load` runs in the ASR worker thread while `diarizer.load` runs in the other (`pipeline.PARALLEL`), and descriptor 2 belongs to the whole process. So anything diarization writes to stderr inside the window is written back a moment late, after the window closes. Nothing of it is lost: the only lines dropped are onnxruntime's `V`, `I` and `W` lines, and diarization doesn't use onnxruntime (pyannote-audio 3.4.0 runs on PyTorch, and `diarize.py` never imports it). Its Python warnings and logging are already off (`diarize._quiet`). The window covers only the import and one small model's load. Moving the call ahead of the pool, into `pipeline.py`, would avoid the overlap, but it would add a file and a fake to `tests/test_pipeline.py` for no change in what the user sees.

**Tests.** `tests/test_asr.py`:
- **The `fake` fixture** also puts a fake `onnxruntime` in `sys.modules`: a `types.SimpleNamespace` whose `set_default_logger_severity` records its argument in a list the test can read. With the fallback, it puts a fake `faster_whisper.vad` there too, whose `get_vad_model` records its call and returns `None`, and `quiet_onnxruntime` imports it as `from faster_whisper.vad import get_vad_model`, so the fake `faster_whisper` namespace needs no `vad` attribute. So `test_load`, `test_transcribe`, `test_initial_prompt_is_passed` and `test_words_are_stripped_and_empty_ones_dropped` run as they do now, without importing the real onnxruntime or setting its process-wide severity.
- **Order:** with the `fake` fixture, `asr.load` calls `set_default_logger_severity(3)` (and, with the fallback, `get_vad_model`) before it builds the `WhisperModel`. Each fake records `len(FakeWhisperModel.instances)` when it's called, and the test checks it was 0.
- **Empty stderr, in a fresh process:** `subprocess.run([sys.executable, "-c", …], capture_output=True)` runs `asr.quiet_onnxruntime()`, then `faster_whisper.vad.get_speech_timestamps(numpy.zeros(16_000, numpy.float32))`. That is the path `transcribe(vad_filter=True)` takes: it loads the cached VAD model and pads the audio to a multiple of 512 samples before calling it, which the model asserts (faster-whisper 1.2.1, `vad.py`). The test checks the exit code is 0 and stderr is empty, and on failure shows stderr. The VAD model ships inside faster-whisper's wheel, so this needs no download and runs in the `test` job. It fails on the Linux runner without the change.
- **With the fallback:** the fake `set_default_logger_severity` writes `[W:onnxruntime:x] w` and `[E:onnxruntime:x] e` lines, and a plain `other` line, straight to descriptor 2 with `os.write(2, …)`. Read with `capfd`, stderr afterwards holds the `[E:onnxruntime` line and `other`, in that order, and not the `W` line. A second test has the fake raise after writing: the exception propagates, the `E` line is still written back, and descriptor 2 points where it did before (a later `os.write(2, …)` shows in `capfd`).

**How the PR shows the failure on Linux.** macOS prints no line, so on a Mac `system/gate/against_base.py` shows the empty-stderr test failing on the base only because `quiet_onnxruntime` doesn't exist there, not because of the line. The Developer pushes the PR's first commit with the tests alone, and `asr.quiet_onnxruntime` as a stub that does nothing, so the tests import. The `test` job's ubuntu run on that commit is red, with the empty-stderr test failing on the `[W:onnxruntime` line. The next commit has the change, and the same job is green on both platforms. The PR body links both runs, with the commit of each, and quotes the red run's failing stderr. If the severity alone leaves the ubuntu run red, a third commit adds the fallback, and the PR links that run too.

**Test of the item:** those tests in the `test` job on both platforms, the red and green ubuntu runs above, and G1-1's test still passing in `test-models`. Then #364, rebased onto P11, shows `silence.wav` and `noise.wav` passing in `test-models` with their test unchanged.

## P12. Turns-first segments

**The finding** (#372: the builder's measurement at ba2eb44, one AMI-ci product run, ES2004a's 300 s, rescored offline with `score.der`'s metric and UEM). The product's DER is 0.426, and 0.390 of that is missed speech. Words-first segments run from their first word's start to their last word's end, and Whisper's word times sit inside the speech. So 48 s of the 55 s that no segment covers is in 67 slivers under 2 s each, at segment edges and pauses. Splitting at pauses, clipping to turns and padding (#372's H3, H4 and H7) don't reach the bound. Segments that take the diarization turns' spans and speakers (H8) give **0.203** (miss 0.144, false alarm 0.035, confusion 0.025), against pyannote alone's 0.181. So, when there are turns, `align.build` makes its segments from the turns, not from runs of words. That adds no parameter: `MAX_SEGMENT` is today's, and nothing is fitted to ES2004a. G1-8c's bounds and scoring, and G1-1 to G1-4, stay exactly as the spec gives them.

### `align.build` with turns

Words are rounded first, by `_rounded`, as now (`g1-slice.md` S4, "Times, rounded once"). Everything below is in whole milliseconds, as integers.

1. **The turns, rounded and clipped.** Each turn's `start` and `end` become `round(t × 1000)`, clipped to `[0, D]`. A turn whose `end` isn't after its `start` is dropped. The rest are ordered by `(start, end, index in the input)`. "The turns" below are these, and "earlier" means earlier in this order.
2. **Each word goes to one turn:** the turns whose `[start, end)` holds the word's midpoint, tested as `2 × start ≤ word.start + word.end < 2 × end`. Of those, the one that overlaps the word most (`min(ends) − max(starts)`), and on a tie the earlier.
3. **A stray word,** whose midpoint no turn holds, goes to the nearest turn by the gap `max(turn.start − word.end, word.start − turn.end, 0)`, however far, and on a tie the earlier. `NEAREST` doesn't apply. Once every word is placed, each turn that took stray words stretches to cover them: `start = min(start, their starts)` and `end = max(end, their ends)`. So no word is lost, and every word's midpoint lies inside its turn.
4. **A turn with no words is dropped,** since the schema needs `text` on every segment. A diarization speaker left with no turn doesn't appear.
5. **Each turn left is a segment:** the turn's `start`, `end` and speaker, its words in ASR's order, and `segment_text(words)` as its text. No pause and no sentence end breaks it.
6. **A turn longer than `MAX_SEGMENT` splits at word boundaries,** greedily. The first piece starts at the turn's `start`. Walking the turn's words in order, the current piece ends before word `w` when all four hold: the piece already holds a word; `w.end − piece start > 30 000` (`breaks`' rule); `w.start` is at or after the end of every earlier word in the piece; and `w.start > piece start`. That piece ends at `w.start`, where the next one starts, and the last piece ends at the turn's `end`. So every piece holds a word, as step 4 needs, and every word's midpoint lies inside its piece. `export/cues.py` needs that: a cue runs from a word's start to a word's end, the first from the segment's start and the last to its end, so each cue has `start < end`. A piece passes 30 s only where no word boundary allows less. The speech after a piece's last word, up to the next piece's first word or the turn's end, stays in it, so DER loses none.
7. **Order and speakers.** The segments are sorted by `start`, stably, after being made in step 1's turn order with each turn's pieces in order. Speakers are numbered by first appearance in that order, `S1`, `S2`, …, labelled `Speaker 1`, ….

**Where turns overlap,** their segments overlap in time. `public-api.md`'s rules allow that: segments sorted by `start`, with 0 ≤ `start` < `end` ≤ `source.duration`, and every segment with `speaker` and `text`. The transcript's words then follow segment order, which can differ from ASR's where a word went to a turn that starts later, nested in a longer one. That can change the transcript's WER, so P12's PR measures it (below). Step 2's tie rule keeps such moves to words that overlap the nested turn more than the long one.

**Without turns** (`--no-diarize`, diarization finding none, or none left after step 1), **today's rule stands, unchanged:** segments are runs of words, broken at a pause of 1 s or more, at a sentence end and at 30 s (`breaks`), all one speaker, `S1`. `--no-diarize`'s outputs are byte-identical to `main`'s, LS-ci's figures with them, since LS-ci runs with `--no-diarize`. The turn branch of `_speakers_of`, and the first word's earliest-turn rule with it, go: `build` no longer uses them.

**What else stays.** `assign_speaker`, `breaks`, `ends_sentence`, `segment_text`, `PAUSE`, `MAX_SEGMENT` and `NEAREST` stay as they are, with their tests. G2's live join uses them (`g2-stage1.md`, item 3a) and stays words-first. `build`'s signature and the `Transcript` it returns don't change, and neither do the exports, the schema, `pipeline` or the eval code.

**`architecture.md`'s alignment paragraph** ("Pipeline") changes in this design PR, which says so for the Owner's approval, and `g1-slice.md` S4's "Segments" bullet points here. Until it merges, this item waits.

### Tests

`tests/test_align.py` gains `TurnsFirstTest`, one test per rule, each building with `samples = 16_000 × 60` unless it says otherwise:

| Rule | Words | Turns | Segments `(start, end, speaker, text)` |
| --- | --- | --- | --- |
| A turn's span and speaker | `[1.5, 2.0] a`, `[2.5, 3.0] b` | A `[1.0, 4.0]` | `(1.0, 4.0, S1, "a b")` |
| The midpoint, `[start, end)` | `[0.9, 1.1] x` (midpoint 1.0) | A `[0.0, 1.0]`, B `[1.0, 2.0]` | `(1.0, 2.0, S1, "x")` |
| The midpoint, not the most overlap | `[0.0, 1.2] x` (midpoint 0.6; A overlaps it 0.1, B 0.5) | A `[0.55, 0.65]`, B `[0.7, 3.0]` | `(0.55, 0.65, S1, "x")`; B, wordless, is gone |
| Two turns hold it: most overlap | `[0.5, 1.0] x`, `[2.0, 2.5] y` | A `[0.0, 2.3]`, B `[2.0, 4.0]` | `(0.0, 2.3, S1, "x")`, `(2.0, 4.0, S2, "y")` |
| Two turns hold it: a tie goes to the earlier | `[0.5, 1.0] x`, `[2.2, 2.6] y` | A `[0.0, 5.0]`, B `[2.0, 3.0]` | `(0.0, 5.0, S1, "x y")` |
| A wordless turn goes, with its speaker | `[0.2, 0.5] a`, `[4.2, 4.5] b` | A `[0.0, 1.0]`, B `[2.0, 3.0]`, A `[4.0, 5.0]` | `(0.0, 1.0, S1, "a")`, `(4.0, 5.0, S1, "b")`; one speaker |
| A stray word joins the nearest turn, which stretches | `[0.2, 0.5] a`, `[1.6, 1.9] s`, `[3.2, 3.5] b` | A `[0.0, 1.0]`, B `[3.0, 4.0]` | `(0.0, 1.9, S1, "a s")`, `(3.0, 4.0, S2, "b")` |
| A stray word's tie goes to the earlier | `[0.2, 0.5] a`, `[1.25, 1.75] s`, `[2.2, 2.5] b` | A `[0.0, 1.0]`, B `[2.0, 3.0]` | `(0.0, 1.75, S1, "a s")`, `(2.0, 3.0, S2, "b")` |
| However far | `[0.2, 0.5] a`, `[6.0, 6.5] s` | A `[0.0, 1.0]` | `(0.0, 6.5, S1, "a s")` |
| Turns rounded and clipped (`samples = 16_000`, so `D` = 1000) | `[0.1, 0.3] a`, `[0.7, 0.9] b` | A `[−0.5, 0.4]`, C `[0.45, 0.4504]`, B `[0.6, 3.0]` | `(0.0, 0.4, S1, "a")`, `(0.6, 1.0, S2, "b")`; C, rounded to zero length, is gone |
| Order and numbering by first segment | `[0.2, 0.5] a`, `[2.2, 2.5] b` | B `[2.0, 3.0]`, A `[0.0, 1.0]` | `(0.0, 1.0, S1, "a")`, `(2.0, 3.0, S2, "b")`; `S1` is A |

- **Over 30 s:** one turn A `[0.0, 40.0]` and words `[i × 0.5, i × 0.5 + 0.5]` for `i` in 0 to 79 give `(0.0, 30.0)` with 60 words and `(30.0, 40.0)` with 20, both `S1`. **An overlapping word moves the cut:** turn A `[0.0, 32.0]`, the words `[i × 0.5, i × 0.5 + 0.5]` for `i` in 0 to 58, then `[29.4, 30.2]`, `[30.1, 30.6]` and `[30.6, 31.0]`, give `(0.0, 30.6)` with 61 words and `(30.6, 32.0)` with 1. **No piece without a word:** turn A `[0.0, 1.0]` with words `[0.2, 0.5] a` and the stray `[40.0, 40.5] s` stretches to `[0.0, 40.5]` and gives `(0.0, 40.0, S1, "a")` and `(40.0, 40.5, S1, "s")`; with `s` alone, it gives `(0.0, 40.5, S1, "s")`, one piece over 30 s, since its only word has no boundary before it.
- **Without turns, today's rule.** Every existing test with no turns stands as it is. `test_build_breaks_at_a_pause_a_sentence_and_a_speaker` becomes two cases: its four words with no turns give `["a", "b.", "c d"]`; with its turns, A `[0.0, 2.6]` and B `[2.6, 3.5]`, they give `["a b. c", "d"]`, since nothing but a turn breaks a segment there. Turns that step 1 drops entirely (`[Turn(0.5, 0.5, "A")]`) give exactly the transcript that `None` gives.
- **`test_first_word_with_no_turn_near_takes_the_earliest_turns_speaker` goes,** along with its rule. The stray-word rows replace it. `AssignSpeakerTest`'s other tests call `assign_speaker` directly and stay.
- **`test_random_words_always_valid`** keeps its 200 cases and its checks for every case: 0 ≤ `start` < `end` ≤ `D` for every segment and word, segments sorted by `start`, each segment's words with starts in order, and `speakers` exactly the segments' ones, numbered by first appearance. Without turns, the joined text is still the input's, in order. With turns, the segments' words, as `(start, end, text)`, are the rounded input words, each exactly once (compared as sorted lists), and each word's midpoint lies in its segment: `2 × start ≤ w.start + w.end < 2 × end`, in milliseconds. The check that word starts are in order across segments applies only without turns.

**Test of the item:**
- `tests/test_align.py` in the `test` job.
- G1-1's, G1-2's, G1-3's and G1-4's tests passing, unchanged, in the PR's `test-models` (tier 3, for `src/lmt/`).
- The PR body gives one local `uv run --frozen lmt eval --set ci` at the PR's head, with `dirty: false`. AMI-ci's product DER must be below 0.250 after rounding (P2b's rule), with AMI-ci's product WER ≤ 0.250 and LS-ci's ≤ 0.050 (LS-ci's should be unchanged at 0.006912). If any of them misses, the Developer reports the figures on the item and holds it for the Architect (`needs-decision:architect`), with no bound, scoring, fixture or subset changed.
- After P12 merges, #343's PR #368 refreshes from `main`, and its `eval-ci` job takes G1-8c's reading in CI. Nothing in P2b's design changes.

## P13. No library writes outside the outputs

**The finding** (#391, PR #400's local `pytest -m models` on the Mac). G1-13's test (P7c) finds a product run writing outside its outputs, under the fresh `HOME` and `TMPDIR`:
- `home/.matplotlib/fontlist-v3.11.0.json`. `diarize.load` imports `pyannote.audio.pipelines`, whose `__init__` imports `voice_activity_detection`, which imports `pyannote.audio.tasks`, and `tasks/segmentation/mixins.py` imports `matplotlib.pyplot` at module level (pyannote-audio 3.4.0). `pyplot` loads `font_manager`, which writes its font list under `MPLCONFIGDIR`, or `~/.matplotlib` on macOS and `$XDG_CACHE_HOME/matplotlib` on Linux without it. Importing a submodule runs the package's `__init__`, so `lmt` can't avoid the import.
- `home/Library/Application Support/Microsoft/DeveloperTools/.onnxruntime/deviceid`, `onnxruntime.db`, `-shm` and `-wal`. onnxruntime 1.31.1, which faster-whisper uses for the Silero VAD, ships Microsoft's 1DS telemetry on both platforms: `core/platform/telemetry_1ds.cc`, a SQLite event store, and the collector `https://mobile.events.data.microsoft.com/OneCollector/1.0/`, all strings in the pinned macOS and manylinux wheels. On Linux its directory is `$XDG_CACHE_HOME/Microsoft/DeveloperTools/.onnxruntime`. Both wheels hold the switch `ORT_DISABLE_TELEMETRY`. So this is more than a stray file. It breaks G1-13's "No package sends telemetry". The upload comes from native code, outside Python's `socket`, so P7a's guard can't see it. On CI, `unshare --net` blocks it. The file check is what found it.
- `tmp/.ses`, not yet traced. The 1DS library keeps a session file, so it is most likely the same source. P13's test shows whether it goes with the switch.

**G1-13's words** are: "After the run, the only new files under them [`HOME`, `TMPDIR`, `XDG_CACHE_HOME` and the working directory] and the output directory are the requested outputs, and nothing in `LMT_CACHE_DIR` has changed. No package sends telemetry." So a library's state can't go to `LMT_CACHE_DIR`, or to any lasting place under those four directories. A directory that exists only while the run does, and is gone after it, meets the words. Turning telemetry off meets the last sentence. Hiding or deleting telemetry's files would not.

### The change

**`asr.py`, onnxruntime's telemetry off.** At module level, beside the imports: `os.environ["ORT_DISABLE_TELEMETRY"] = "1"  # before onnxruntime is imported (Q8)`. This is the same form as `models.py`'s `HF_HUB_DISABLE_TELEMETRY`. `asr` is imported before any thread starts, since `diarize` imports it at the top, and `quiet_onnxruntime` is the process's first import of onnxruntime. `os.environ`'s assignment calls `putenv`, so onnxruntime's native code reads the switch when it starts its telemetry. The value is set unconditionally: a user's environment doesn't turn the product's telemetry back on.

**`diarize.py`, matplotlib's cache in a scratch directory.** `scratch_matplotlib() -> Path` comes first in `load`, before the config is read:
- On the first call in a process, it makes `tempfile.mkdtemp(prefix="lmt-matplotlib-")`, which goes under `TMPDIR`, and sets `os.environ["MPLCONFIGDIR"]` to it unconditionally. It registers `atexit.register(shutil.rmtree, path, ignore_errors=True)` and keeps the path in a module global, `_scratch`.
- A later call returns the same path and makes nothing.
- matplotlib reads `MPLCONFIGDIR` the first time it needs its directory, which is the `pyplot` import, inside `load`. Nothing in a product run imports matplotlib before that.

`atexit` runs on a normal exit, on `sys.exit`, and after `KeyboardInterrupt` (`cli.main` returns 130, and `run` calls `sys.exit`). So every run that ends through `cli.main` removes the directory: success, an `LmtError` and an internal error alike. A process killed by a signal leaves it in `TMPDIR`, the system's place for temporary files. That's accepted, since G1-13 measures a run that ends. `--no-diarize` never calls `load`, so it makes nothing. Each `lmt eval` worker is its own process, so it makes and removes its own directory.

matplotlib rebuilds its font list in each process that diarizes, because the cache never lasts. That costs some start-up time, more on macOS, which has more system fonts. The PR reports it (below). No bound applies to it here: Q7's RTF is measured in stage 3, and this is the price of G1-13's words.

**matplotlib's warning stays off stderr** (#402, PR #403's finding). Whenever it has no font list, `font_manager` logs `Matplotlib is building the font cache; this may take a moment.` at `WARNING`. With no logging configured, Python's last-resort handler prints that to stderr. On `main` it prints once per machine, since the list lasts in `~/.matplotlib`. With the scratch directory it prints on every diarizing run, and G1-11's silence and noise cases see a second line. So `diarize.LOGGERS` becomes `("lightning", "pytorch_lightning", "pyannote", "matplotlib")`, extending S3's quiet loggers (`g1-slice.md`). `load` already imports pyannote inside `_quiet()`, which sets those loggers to `ERROR` before `pyplot` loads, and `font_manager`'s logger, `matplotlib.font_manager`, takes its level from `matplotlib`. The warning goes, and matplotlib's errors still print. The other ways out don't hold up. A lasting font list breaks G1-13's words. A prebuilt list depends on each machine's fonts. Filtering stderr would hide real errors.

**Nothing else changes:** no setting of the models, the pipeline, the outputs or the CLI. The four outputs stay byte-identical, so G1-1 to G1-4 and #400's comparison of the outputs are unaffected.

**If either source still writes** with the change in place, the Developer handles it in this item, in this order. If any onnxruntime file still appears, `quiet_onnxruntime` also calls `onnxruntime.disable_telemetry_events()` straight after the import, and the `fake` fixture's `onnxruntime` namespace (P11) gains that function. If `tmp/.ses` or an onnxruntime file still remains after that, or a file from another library appears, the Developer reports its path on the item and holds it for the Architect (`needs-decision:architect`). The test doesn't change, and no file is deleted after the fact.

### Tests

**`tests/test_library_writes.py`** (new, the `test` job on both platforms, no model, tagged `G1-13`). Each case runs a fresh process, `[sys.executable, "-c", <code>]`. Its `env` holds `PATH`, `LANG=C.UTF-8`, and `HOME`, `TMPDIR` and `XDG_CACHE_HOME` set to empty directories `home`, `tmp` and `xdg` under `tmp_path`. Its `cwd` is an empty `work`. Nothing else is set: no `MPLCONFIGDIR` and no `ORT_DISABLE_TELEMETRY`.
- **Nothing is left, from either library.** The child runs the product's paths for both libraries. It calls `diarize.scratch_matplotlib()`, then `import pyannote.audio.pipelines` inside `with diarize._quiet():`, as `load` does, and prints `matplotlib.get_cachedir()`. Then it calls `asr.quiet_onnxruntime()` and `faster_whisper.vad.get_speech_timestamps(numpy.zeros(16_000, numpy.float32))`, P11's VAD path, which starts onnxruntime's environment and runs a session. The child exits 0. The printed directory is under `tmp`. No line of the child's stderr contains `matplotlib`, compared without case (the font list is always built here, so without `"matplotlib"` in `LOGGERS` the warning prints). After the exit, `isolation.snapshot(home, tmp, xdg, work)` is `{}`. On failure, the test shows the snapshot's paths. It fails on `main` on both platforms: on macOS with the four files above, and on Linux with matplotlib's and onnxruntime's directories under `xdg`.
- **The scratch directory is the process's own, and goes at exit.** The child calls `diarize.scratch_matplotlib()` twice and prints both paths, `os.environ["MPLCONFIGDIR"]`, and whether the path is a directory. The two paths and the variable are equal, the path is a directory under `tmp`, and after the exit it is gone and `tmp` is empty.
- **The switch is set.** The child does `import lmt.asr` and prints `os.environ.get("ORT_DISABLE_TELEMETRY")`, which is `1`.

**`tests/test_diarize.py`:**
- **`load` calls it first.** With `diarize.scratch_matplotlib` monkeypatched to raise a sentinel exception, `diarize.load({})` raises the sentinel, not `KeyError`.
- **The `fake` fixture** starts with `monkeypatch.delenv("MPLCONFIGDIR", raising=False)` and `monkeypatch.setattr(diarize, "_scratch", None)`. So the in-process `load` tests leave no `MPLCONFIGDIR` behind in pytest's environment. The directory they make goes at pytest's exit.

**How the PR shows the failure.** The `test` job runs on a pull request, so the Developer pushes the PR's first commit with the tests alone, and `diarize.scratch_matplotlib` as a stub that returns `Path(tempfile.gettempdir())` and sets nothing. The first commit's `test` job is red on both platforms, with the snapshot's paths in the failure. The next commit has the change, and the same job is green on both. The PR body links both runs, with each commit, and quotes the red runs' paths. If the fallback above was needed, a third commit adds it, and the PR links that run too. **On #403**, whose first two commits are already pushed, the stderr check and `"matplotlib"` in `LOGGERS` come as one more commit. The PR shows the check failing locally without the `LOGGERS` change (`uv run --frozen pytest -q tests/test_library_writes.py`, quoting the matplotlib line), and passing with it, and links that commit's `test` runs.

**Test of the item:**
- Those tests in the `test` job on both platforms, red and then green as above.
- The Developer's local `uv run --frozen pytest -m models --durations=0`, at the PR's head, with G1-1's to G1-4's tests and G1-11's (`tests/test_g1_11.py`, the silence and noise cases among them) passing unchanged. The PR gives `two_speakers_run`'s setup time beside #391's figure, 282 s on the Mac, for the font list's cost.
- After P13 merges, #400 merges `main` and shows its local `uv run --frozen pytest -m models -rA tests/test_g1_13.py` passing, with the snapshot's only difference the four outputs. Only then does #400 merge, and `main`'s `test-models` confirms it with `isolated` true (P7c).

## Risks

- **G1-8c's first reading** may miss a bound, most likely AMI-ci's DER or WER on one 300 s meeting. That goes to the Architect (P2b, above), and only P2b waits. The bounds don't move. It missed AMI-ci's DER (0.426, #343), and P12 is the fix.
- **P12 rests on one meeting.** #372 measured turns-first on ES2004a alone, which is all of AMI-ci. AMI full, in stage 3 (G1-8), tests whether it holds across meetings. P12's other risk is WER where turns overlap (P12, "Where turns overlap"): its PR measures AMI-ci's WER, and #343's 0.182 leaves 0.068 to the bound.
- **Determinism of the double run.** ASR and diarization run side by side. If the two runs differ, the Developer sets `pipeline.PARALLEL = False`, as `g1-slice.md` S6 allows, and says so on the item. That changes the product, so the PR is tier 3.
- **`test-models` time.** These items add about 10 product runs on 60 s clips (P4's silence, noise and mutations; P5; P7c), on top of G1-1's and G1-2's six. The total comes to about 16 runs, 20 to 25 minutes, inside the job's 30-minute timeout and over the architecture's estimate of about 8 runs. The first PR that passes 1.5 times the estimate says so on its item, and the Architect re-sizes the job in `architecture.md` ("CI"), or splits it.
- **FFmpeg's output on stderr.** Decode already keeps FFmpeg's own log off through `av.logging` (`src/lmt/audio.py`, its docstring). If FFmpeg's output still reaches stderr on a corrupt input, breaking "one line", P4's test finds it, and that's a product finding for the Architect (P4, above).
- **Other libraries' output on stderr.** onnxruntime's was the first (P11), and matplotlib's font-cache warning the second (P13). Any other library line that reaches stderr is a product finding too, fixed in the stage that loads the library. The test that found it doesn't change.
- **Native connections are invisible to the guard.** P7a's guard wraps Python's `socket`, and onnxruntime's telemetry posts from native code (P13). On CI, `unshare --net` covers that. On the Mac, which can't isolate, the Owner's Wi-Fi-off run is the check. A library that keeps no file and posts from native code would be caught only there, and by `unshare` on CI. P13 turns off the one such sender found so far.
