# Internal design: G2 stage 1 (the live pipeline, checked in CI)

| Date (PT) | By | Change |
| --- | --- | --- |
| 2026-10-28 | architect, #157 | First version: phase 2.1's five items, with `lmt live` split into 3a (join, events, lockstep session), 3b (the command and its outputs) and 3c (real time and signals) |
| 2026-10-28 | architect, #157 | The Reviewer's findings on #163: item 5's figures for `the` corrected; item 5 ensures `default_models`, so it needs nothing from item 1; 3b wires `--max-speakers` and names a test per option, plus G2-5 (iii)'s exit 0 and the silent file; `save` removes its temporary files on any exception; reading 9 |
| 2026-10-29 | architect, #208 | The Owner's "Break down L and XL items into S items" (2026-10-29): the seven items become 29 S items (5a–5d, 1a–1e, 2a–2c, 4a–4d, 3a1–3a4, 3b1–3b5, 3c1–3c4), each with its own files, test, Needs and tier. "What stage 1 assumes from G1's stage 2" becomes what G1.2 merged, so each item's Needs are its real blockers. The live join stays words-first (`align.assign_speaker` and `breaks`), per P12. Model tests are shown by the Developer's local run, since a PR runs tier 1 at most. No G2 criterion, bound or fixture changes |
| 2026-10-29 | architect, #208 | The Reviewer's finding on #405: `default_models` stays offline-only, so `lmt transcribe`, `eval --set ci/full`, `demo` and G3's cache key never ensure the live model. 1d adds `download_defaults`, which only `lmt models download`/`list` and 5b's `run_live` call, plus a `tests/test_pipeline.py` case; 5b now needs 1d. Notes: #164's overlap with 3b1, and #400's helper for 3b5 |
| 2026-10-29 | architect, #434 | 2c's first measurement (#468) missed 90 % on time only because the RTTM's turns include pauses that diarization leaves unlabelled; the offline system that passes G1-3 misses it too. 2c now takes its 90 % purity over each speaker's labelled time, and adds a 60 % coverage floor (the Reviewer's finding on #468). The 90 % doesn't move. G2-3, on words in 3a4, doesn't change |
| 2026-10-30 | architect, #433 | 1e's first measurement missed G2-6c's 2.0 s at U = 1.0 s (ASR's p95 2.100 s, 2.220 s on a second machine). The provisional U becomes 0.8 s (12,800 samples), the architecture's first remedy: p95 1.520 s, and G2-2's WER 2.27 %. 1e also makes that change, with the two unit tests' helpers pinned to U = 1.0 s, so it is tier 3. No bound moves |
| 2026-10-30 | architect, #437 | 3a3's held decision: `run_lockstep` and `run_threaded` take keyword-only `source_info` and `models`, the two dicts `EventWriter.start` needs, and write `start` with them; 3b3's command passes them. "Through `source.lockstep`" becomes `lmt.live.source.lockstep(source, asr, diarizer)`, the module function |
| 2026-10-31 | architect, #567 | 3c4's second SIGINT, sent 0.1 s after the first, was lost on a loaded runner (sev:1 #558): two SIGINTs that arrive before the main thread runs its handler are one to CPython. The second is now sent once a test-only probe, `tests/live_stop_probe.py`, has seen the first stop handled, not after a fixed gap. Reading 10 says a Ctrl-C the handler never sees as a second isn't one. No product code, public API, criterion or other case changes |

This is the detail a Developer needs to build each of G2 stage 1's items in one run. It works inside `spec/acceptance.md` G2, `design/architecture.md` ("Live mode (G2)", "CI"), `design/public-api.md` (`lmt live`, live events 1.0, `lmt eval --set live`, `results/live.json`, transcript JSON 1.1), the Owner's answers 1a–8a on #82, `design/internal/g1-stage1.md`, `g1-slice.md` and `g1-stage2.md`. Where this file and those disagree, they win, and this file is the one to fix. The Reviewer reviews this file. The Architect changes it.

## Items, files and order

The coordinator's five items became seven (1, 2, 3a, 3b, 3c, 4 and 5, the § numbers below), and each of those was about 1.5 h. On the Owner's "Break down L and XL items into S items" (2026-10-29), they become **29 S items**. An S item is one Developer run and one PR, up to about 45 minutes. Each has its own files, its own test, its Needs and its tier. The § sections below keep the method; each one starts with a **Split** paragraph that says which part each S item builds and where its tests go. The criteria are `spec/acceptance.md` G2's, unchanged: no bound, rule or fixture moves.

| Item | What | Needs | Files it creates or changes | Tier | Its test (job) |
| --- | --- | --- | --- | --- | --- |
| **5a** | Matching, delays, nearest-rank percentiles and reading an event log (§5) | — | `src/lmt/eval/live.py` (new), `tests/test_eval_live.py` (new), `tests/fixtures/eval/live/ref_words.json`, `run1.jsonl`, `run2.jsonl`, `run3.jsonl` (new) | 3 | `tests/test_eval_live.py` (`test`) |
| **5b** | The runs: `run_once` timestamps each event's arrival, `run_live` ensures the models and runs three times (§5) | 1d, 5a | `src/lmt/eval/live.py`, `tests/fake_live.py` (new), `tests/test_eval_live_run.py` (new) | 3 | `tests/test_eval_live_run.py` (`test`) |
| **5c** | The figure, and the live timing fields in `report.py` (§5) | 5b | `src/lmt/eval/live.py`, `src/lmt/eval/report.py`, `tests/fixtures/eval/live/run1.json`, `run2.json`, `run3.json` (new), `tests/test_eval_live_figure.py` (new) | 3 | `tests/test_eval_live_figure.py`, `tests/test_report.py` unchanged (`test`) |
| **5d** | `lmt eval --set live`: AMI-ci's word times, the command and `results/live.json` (§5) | 5c | `src/lmt/eval/datasets.py`, `src/lmt/eval/live.py`, `src/lmt/eval/cli.py`, `src/lmt/cli.py` (`--set`'s choices only), `tests/test_eval_live_cli.py` (new) | 3 | `tests/test_eval_live_cli.py` (`test`) |
| **1a** | The file source and lockstep (§1) | — | `src/lmt/live/__init__.py` (empty), `src/lmt/live/source.py`, `tests/test_live_source.py` | 3 | `tests/test_live_source.py` (`test`) |
| **1b** | Streaming ASR: LocalAgreement-2 over the rolling buffer, without the pause rule (§1, steps 1–3 and 5–7) | — | `src/lmt/live/__init__.py` (empty), `src/lmt/live/asr.py`, `tests/test_live_asr.py` | 3 | `tests/test_live_asr.py` (`test`) |
| **1c** | Streaming ASR's pause rule, on Silero VAD's gaps (§1, step 4) | 1b | `src/lmt/live/asr.py`, `tests/test_live_asr.py` (its helper passes `speech`), `tests/test_live_asr_pause.py` (new) | 3 | `tests/test_live_asr_pause.py` (`test`; its one `models` case locally) |
| **1d** | The live default model in the manifest, and `download_defaults` for `lmt models` (§1, "The live default model") | — | `src/lmt/models.toml`, `src/lmt/models.py`, `tests/test_models_live.py` (new), `tests/test_pipeline.py` (one case) | 3 | `tests/test_models_live.py`, `tests/test_pipeline.py` (`test`) |
| **1e** | G2-2, and ASR's half of G2-6c, on the models in lockstep; the provisional U of 0.8 s (§1) | 1a, 1c, 1d, 5a | `tests/test_live_asr_models.py` (new), `src/lmt/live/asr.py` (`AsrConfig.update` only), `tests/test_live_asr.py`, `tests/test_live_asr_pause.py` | 3 | `tests/test_live_asr_models.py` (`test-models`; local run in the PR) |
| **2a** | Online diarization's clustering: matching, centroids, accumulation, finalization, `replay` and `NullDiarizer` (§2, steps 3–6) | — | `src/lmt/live/__init__.py` (empty), `src/lmt/live/diarize.py`, `tests/test_live_diarize.py` | 3 | `tests/test_live_diarize.py` (`test`) |
| **2b** | Online diarization's steps: segmentation, overlap-aware embeddings, the schedule and catch-up, `record`, `flush` (§2, steps 1–2) | 2a | `src/lmt/live/diarize.py`, `tests/test_live_diarize_online.py` (new) | 3 | `tests/test_live_diarize_online.py` (`test`) |
| **2c** | G2-3's speaker rule on time, on the models in lockstep (§2) | 1a, 2b | `tests/test_live_diarize_models.py` (new) | 2 | `tests/test_live_diarize_models.py` (`test-models`; local run in the PR) |
| **4a** | `sounddevice` locked and vetted, and `libportaudio2` on the runner (§4, "First step") | — (its first step can stop for the Owner) | `pyproject.toml`, `uv.lock`, `toolchain.toml` (`[[licences.library]]`), `.github/workflows/product.yml` (`test` only), `tests/test_portaudio.py` (new) | 3 | The licence check and `tests/test_portaudio.py` (`test`, both platforms) |
| **4b** | `audio.Resampler`, extracted from `decode` (§4) | — | `src/lmt/audio.py`, `tests/test_audio.py` | 3 | `tests/test_audio.py` (`test`) |
| **4c** | Devices: the stand-in, `input_devices`, `resolve`, and G2-5 (ii) (§4) | 4a | `src/lmt/live/__init__.py` (empty), `src/lmt/live/mic.py`, `tests/fake_sounddevice.py`, `tests/test_live_mic.py` | 3 | `tests/test_live_mic.py` (`test`, its real case on the runner) |
| **4d** | `MicSource`: capture, resampling, re-blocking, stopping and the silent device, G2-5 (i) and (iii) (§4) | 4b, 4c | `src/lmt/live/mic.py`, `tests/test_live_mic_source.py` (new) | 3 | `tests/test_live_mic_source.py` (`test`) |
| **3a1** | The join, words-first (§3a, `join.py`) | 1b, 2a | `src/lmt/live/join.py`, `tests/test_live_join.py` | 3 | `tests/test_live_join.py` (`test`) |
| **3a2** | The events and their schema (§3a, `events.py`) | 3a1, 5a | `src/lmt/live/events.py`, `schema/live-events.schema.json`, `src/lmt/schema/live-events.schema.json`, `tests/test_live_events.py` | 3 | `tests/test_live_events.py` (`test`) |
| **3a3** | The lockstep session (§3a, `session.py`) | 1a, 3a2 | `src/lmt/live/session.py`, `tests/test_live_session.py` (new) | 3 | `tests/test_live_session.py` (`test`) |
| **3a4** | G2-1, G2-3 and G2-6c in process, on the models (§3a) | 1c, 1d, 1e, 2b, 3a3, 5a | `tests/test_live_session_models.py`, `tests/test_live_asr_models.py` (drops its two-speaker case) | 2 | `tests/test_live_session_models.py` (`test-models`; local run in the PR) |
| **3b1** | `lmt live`'s parser and its usage checks; G1-6's table test covers it (§3b, `cli.py`) | — | `src/lmt/cli.py`, `src/lmt/live/__init__.py` (empty), `src/lmt/live/command.py` (a stub), `tests/test_cli.py`, `tests/test_live_cli_args.py` (new) | 3 | `tests/test_live_cli_args.py`, `tests/test_cli.py` (`test`) |
| **3b2** | The outputs: the growing text, the WAV, `save` and the live transcript (§3b, `output.py`) | — | `src/lmt/live/__init__.py` (empty), `src/lmt/live/output.py`, `tests/test_live_output.py` | 3 | `tests/test_live_output.py` (`test`) |
| **3b3** | The command: the checks before capture, the session, the outputs and the exit codes; G2-7's before-capture cases and G2-8's bad input (§3b, `command.py`) | 1c, 1d, 2b, 3a3, 3b1, 3b2, 4d | `src/lmt/live/command.py`, `tests/live_lockstep.py`, `tests/test_live_cli.py` | 3 | `tests/test_live_cli.py` (`test`) |
| **3b4** | A test per option, and G2-5 (ii) and (iii) through the command (§3b) | 3b3 | `tests/test_live_options.py` (new) | 2, or 3 if it fixes `command.py` | `tests/test_live_options.py` (`test`) |
| **3b5** | The shared run: G2-8's network and files, G2-4's outputs in lockstep; G2-1, G2-3 and G2-6c move onto it (§3b) | 3a4, 3b3, #402 (G1's P13) | `tests/conftest.py` (`live_run`), `tests/test_live_shared_run.py`, `tests/test_live_session_models.py` | 2 | Both files (`test-models`; local run in the PR) |
| **3c1** | The threaded run, the stage timings and the "behind" warning (§3c) | 3a3 | `src/lmt/live/session.py`, `tests/test_live_realtime.py` | 3 | `tests/test_live_realtime.py` (`test`) |
| **3c2** | Signals, the second Ctrl-C, a bug's exit 1, and `-v` (§3c) | 3b4, 3c1 | `src/lmt/live/command.py`, `tests/live_fakes.py` (new), `tests/test_live_signals.py` (new) | 3 | `tests/test_live_signals.py` (`test`) |
| **3c3** | The tuning entry point (§3c) | 3b3 | `src/lmt/live/tuning.py`, `tests/test_live_tuning.py` | 3 | `tests/test_live_tuning.py` (`test`) |
| **3c4** | G2-4 at real-time pace, on the models (§3c) | 3c2, 5b | `tests/test_live_realtime_models.py`, `tests/live_stop_probe.py` (new, #567); `.github/workflows/product.yml` (`test-models`' `timeout-minutes`) only if its measured time needs it | 2, or 3 with `product.yml` | `tests/test_live_realtime_models.py` (`test-models`; local run in the PR) |

**The tiers** follow the architecture's table ("CI"): anything under `src/lmt/` is tier 3 (the eval harness included), as are `pyproject.toml`, `uv.lock`, `toolchain.toml` and the workflows; `tests/` and `schema/` alone are tier 2.

**Model tests in a PR.** A pull request runs tier 1 at most (`.github/scripts/tiers.py`, `PULL_REQUEST_MAX_TIER = 1`), so it never runs `test-models`. Each item whose test is marked `models` (1c's one case, 1e, 2c, 3a4, 3b5, 3c4) shows in its PR the Developer's local `uv run --frozen pytest -m models -rP <its test files>` result, with the figures the test prints. `main`'s `test-models` first confirms it after the merge. A failure there is `sev:1`: revert first, as the next Developer item, then fix the cause.

**A first measurement that misses a bound** (G2-2's 10.0 %, G2-3's 90 %, G2-6c's 2.0 s, or 2c's 90 % purity and 60 % coverage on time) goes to the Architect on the item, with the figures. The bound doesn't move. What may change is a provisional setting (U, L, the diarization thresholds), by the Architect in this file, or the live default model in stage 2. G2-6c's bound changes only by the Architect's proposal to the Owner, as the spec says.

**1e's first measurement** (#433) missed G2-6c at U = 1.0 s. In lockstep with `distil-large-v3`, ASR's p95 stream delay was 2.100 s on the Developer's machine (140 of 146 offline words matched) and 2.220 s on a second (137 matched, 9 words over 2.0 s). A word that ends just before an update boundary waits a third update, as the architecture's delay budget warned. Its first remedy is a shorter U, not a looser bound. On the second machine, with `dataclasses.replace(DEFAULT_ASR_CONFIG, update=…)` and nothing else changed:

| U | ASR's p95 on `two_speakers.wav` (≤ 2.0 s) | Matched | Words over 2.0 s | G2-2's WER on `clip.wav` (≤ 10.0 %) |
| --- | --- | --- | --- | --- |
| 1.0 s | 2.220 s | 137 of 146 | 9 | 3.41 % |
| 0.8 s | 1.520 s | 137 of 146 | 1 | 2.27 % |
| 0.5 s | 1.120 s | 138 of 146 | 0 | 9.09 % |

So the provisional U is **0.8 s** (12,800 samples, eight blocks). It leaves margin on both bounds, where 0.5 s leaves 0.9 points on G2-2, less than the 1.7 points the WER moved between the two machines at 1.0 s. The budget becomes max(2U, L + S) = max(1.6, 1.5) = 1.6 s. Lockstep runs take about 1.2 times as long (541 s against 466 s on the two-speaker clip). Stage 2's sweep still pins U; its pinned value must keep G2-6c passing, which rules 1.0 s out unless the remedy there is a model that agrees sooner. **1e** makes the change: `AsrConfig.update` defaults to 12,800; `tests/test_live_asr.py`'s and `tests/test_live_asr_pause.py`'s `make` helpers default to `AsrConfig(update=U)` (U = 16,000, as their scripted hypotheses assume), the pause test's `AsrConfig(pause=9601)` becomes `AsrConfig(update=U, pause=9601)`, and `ConfigTest` expects `update=12800`. Then all their cases pass unchanged.

**The old items:**

| Item | Is now |
| --- | --- |
| **1** (#211) | 1a, 1b, 1c, 1d, 1e |
| **2** (#210) | 2a, 2b, 2c |
| **3a** (#212) | 3a1, 3a2, 3a3, 3a4 |
| **3b** (#213) | 3b1, 3b2, 3b3, 3b4, 3b5 |
| **3c** (#214) | 3c1, 3c2, 3c3, 3c4 |
| **4** (#209) | 4a, 4b, 4c, 4d |
| **5** (#208) | 5a, 5b, 5c, 5d |

**Needs are the real blockers.** G1's stage 2 has merged what G2 calls (next section), so no S item waits on a G1 item except **3b5**, which waits on **#402 (G1's P13)**: until onnxruntime's telemetry and matplotlib's cache stop writing under `HOME` and `TMPDIR`, G2-8's "the only new files are the requested outputs" can't hold for `lmt live` any more than G1-13's does for `lmt transcribe`. "—" means nothing unmerged.

**Order.** An item can start once everything it needs has merged. The longest chain is 1b → 3a1 → 3a2 → 3a3 → 3b3 → 3b4 → 3c2 → 3c4, so its first links go first. With the four Developers (#392), in this order:

| # | Item | Needs |
| --- | --- | --- |
| 1 | 1b | — |
| 2 | 2a | — |
| 3 | 1a | — |
| 4 | 5a | — |
| 5 | 3b1 | — |
| 6 | 3b2 | — |
| 7 | 4a | — (its first step can stop for the Owner, so it starts early) |
| 8 | 4b | — |
| 9 | 1d | — |
| 10 | 3a1 | 1b, 2a |
| 11 | 1c | 1b |
| 12 | 2b | 2a |
| 13 | 5b | 1d, 5a |
| 14 | 4c | 4a |
| 15 | 3a2 | 3a1, 5a |
| 16 | 1e | 1a, 1c, 1d, 5a |
| 17 | 2c | 1a, 2b |
| 18 | 4d | 4b, 4c |
| 19 | 5c | 5b |
| 20 | 3a3 | 1a, 3a2 |
| 21 | 5d | 5c |
| 22 | 3b3 | 1c, 1d, 2b, 3a3, 3b1, 3b2, 4d |
| 23 | 3a4 | 1c, 1d, 1e, 2b, 3a3, 5a |
| 24 | 3c1 | 3a3 |
| 25 | 3b4 | 3b3 |
| 26 | 3b5 | 3a4, 3b3, #402 |
| 27 | 3c3 | 3b3 |
| 28 | 3c2 | 3b4, 3c1 |
| 29 | 3c4 | 3c2, 5b |

**Parallel-safe,** by the files in the table. Items that share a file are in sequence through their Needs (5a → 5b → 5c → 5d in `eval/live.py`; 1b → 1c; 2a → 2b; 4c → 4d; 3a3 → 3c1; 3b3 → 3c2; 1e → 3a4 → 3b5 in the model tests), except these, which may run at the same time:
- **`src/lmt/live/__init__.py`**, empty, is created by whichever of 1a, 1b, 2a, 3b1, 3b2 and 4c goes first. Two branches adding the same empty file merge cleanly.
- **`src/lmt/cli.py`:** 3b1 adds the `live` subparser and its checks; 5d adds `"live"` to `eval`'s `--set` choices, one line in another function. Git merges them cleanly; whichever merges second refreshes from `main`.
- **`.github/workflows/product.yml`:** 4a changes only the `test` job, and 3c4 only `test-models`' `timeout-minutes`, if at all.
- **4a** is the only item that changes `pyproject.toml`, `uv.lock` or `toolchain.toml`.

**Outside G2:** G3's #164 also changes `src/lmt/cli.py`, `tests/test_cli.py` and `LATER_GOAL`, so it and 3b1 will conflict in text. Neither waits on the other. Whichever merges second refreshes from `main` and keeps both changes, `LATER_GOAL`'s included.

**Every item's local checks:** `uv run --frozen ruff check`, `uv run --frozen pytest`, `uv run --frozen pytest -m models` for an item with model tests (the Developer's machine has the models), and `python3 -I system/gate/generic.py --base origin/main`. Each test that checks a G2 criterion carries its tag (`criteria.md` §1), and each PR shows `criteria.py --ref refs/pull/<n>/merge` giving its criteria `partial`, with no failed check.

## What G1's stage 2 gives (on `main`)

G1's stage 2 has merged decode, ASR, diarization with P12's turns-first segments, alignment, the exporters, the schema at 1.1 and `transcript.load` (`g1-slice.md`, `g1-stage2.md`). Checked on `main` at a34b9f8 (2026-10-29), these are the interfaces G2's items call, and where each differs from what this file first assumed:

| Interface | Used by | On `main` | For G2 |
| --- | --- | --- | --- |
| **Decode** (`lmt.audio`) | 1a, 4b | `decode(path) -> ndarray`, float32, 16 kHz, mono, one dimension; every failure is `InputError(str(path), …)`, an empty file and a truncated WAV included (P1). | As assumed. |
| **A resampler** (`lmt.audio`) | 4b, 4d | None: `decode` builds `av.AudioResampler(format="flt", layout="mono", rate=16000)` inline. | **4b extracts `Resampler`** (§4), with decode's output and tests unchanged. |
| **The ASR engine** (`lmt.asr`) | 1b, 1c, 3b3 | `load(model_dir) -> Engine`; `Engine.transcribe(audio, *, initial_prompt=None) -> list[Word]` with G1's settings and Silero's VAD filter. `quiet_onnxruntime()` keeps onnxruntime's log off stderr (P11). | As assumed. 1c's VAD calls go through `lmt.asr`, imported first, so P11's quiet log (and P13's telemetry setting, once #402 merges) covers them. |
| **The transcript types** (`lmt.transcript`) | 1b, 3a1, 3b2 | Frozen `Word(start, end, text, probability)`, `Turn(start, end, speaker)`, `Speaker(id, label)`, `Segment(start, end, speaker, text, words)` with `words` a **tuple**, `Transcript`, `to_dict`, `from_dict`, `load(path)` (P9). `SCHEMA_VERSION = "1.1"`. | Segments are built with tuples. |
| **Alignment's rules** (`lmt.align`) | 3a1 | `assign_speaker(word, turns, previous)`, `breaks(previous_word, word, segment_start)` ("its speaker aside"), `ends_sentence`, `segment_text`, and `build`. With turns, `build` is now **turns-first** (P12): each turn holding words is a segment. Without turns it is words-first. `align.py` says G2's live join reuses the words-first rules. | **The live join stays words-first** (P12): it labels each word with `assign_speaker` and breaks with `breaks` and a speaker change (§3a). It never calls `build`, and nothing changes in `align.py`. The final live transcript is the join's segments, so G2-4's "segments hold exactly the event stream's committed words" holds by construction. Turns-first needs a turn's end, which a live session has only once the speaker stops, so a long turn's segment couldn't close, nor its `<stem>.txt` line appear, until then. |
| **Diarization's setup** (`lmt.diarize`) | 2b, 3b3 | `configure_torch()`, `load_segmentation(model_dir)`, `load_embedding(model_dir)`, and the names `SEGMENTATION`, `EMBEDDING`, `DIARIZATION`. | As assumed. |
| **The exporters** (`lmt.export`) | 3b2, 3b3 | `FORMATS`, `render(transcript, fmt)`, `outputs`, `check(out_dir, stem, formats, *, overwrite)`, `write(...)`, and `export.txt.render_segment(segment, label)`, whose docstring already names G2's growing `<stem>.txt`. | 3b3's output checks use `export.check`. |
| **The schema** (`lmt.schema`, `schema/transcript.schema.json`) | 3a2, 3b2 | `validate(doc)` raises `InputError`. The schema is **1.1** and accepts `source.live` (`true`) and `source.device` (a string). `tests/test_export.py` checks that the published copy equals the package's. | **3b changes no schema, exporter or fixture.** 3a2's events schema gets its own copy check, in `tests/test_live_events.py`. |
| **The models** (`lmt.models`) | 1d, 3b3, 5b | `load_manifest`, `default_models(manifest, asr=None)`, `ensure(models, offline=False) -> {name: dir}`, `model_dir`. `pipeline.transcribe` ensures `default_models(manifest, asr=model)`, with `model` `None` without `--model`; `cli_models`'s `download` and `list` use `default_models` too. | 1d adds the live default and `download_defaults`, for `lmt models` and 5b only; `default_models` doesn't change, so `lmt transcribe`, `eval --set ci/full`, `demo` and G3's cache key never see the live model (§1). |
| **The harness** (`lmt.eval`) | 5a–5d | `score.wer`, `score.der`, `score.hypothesis_from_transcript`, `score.Item`, `score.Turn`; `report.build`, `write`, `strip_timing`, `same_accuracy` and `TIMING_FIELDS`; `datasets.fetch(set_name)`, `ami_words(files) -> [(start, end, text)]`, `crop_references`; `eval/cli.py`'s `cli_eval`, with `--set ci` and `full`. `cli.py`'s `eval --set` has `choices=("ci", "full")`. | **5d adds `"live"` to `cli.py`'s choices.** AMI's word times already exist, as triples, so 5d adds only AMI-ci's reference by itself (§5). |
| **The CLI** (`lmt.cli`) | 3b1 | `build_parser`, `validate`, `main`. There is no `live` subparser; `tests/test_cli.py`'s table test skips the "(G2)" section through `LATER_GOAL`. | 3b1 adds both. |
| **Test helpers** | 1e, 2c, 3a4, 3b3, 3b5 | `tests/conftest.py`'s `clip_run`, `two_speakers_run` and `run_lmt`; `tests/fixtures/clip.wav` with `clip.txt`, `two_speakers.wav` with `two_speakers.rttm`; `tests/isolation.py`'s `snapshot`, `wrap` and `run_isolated` (P7b); the guard, `tests/netguard/sitecustomize.py` (P7a); `tests/bad_inputs.py` (P4). | As assumed. G1-13's own test (#391, P7c) isn't needed: 3b5 uses the guard and `isolation.py` directly. If #400 has merged by 3b5 and exposes a helper for those checks, 3b5 calls it instead, so the two can't drift. |

## Shared conventions

- **Positions are counted in samples** at 16 kHz, as integers, and turned into seconds only for output. A block is 1,600 samples (0.1 s), the update interval U 12,800 (0.8 s), the diarization step S 8,000, its window W 80,000 and its latency L 16,000. So every boundary falls on a block boundary, and floating-point error can't move one.
- **Times written out** (word times, event `t`, segment times) are rounded to the millisecond once, when the word is committed or the event is written, as G1 rounds once (architecture, "One rendering path").
- **A stage** is an object with `feed(samples) -> Update` and `flush() -> Update`. `feed` takes any number of samples: one block in lockstep, or every block that has queued up in real time. It runs at most one update per call for ASR, and the steps the catch-up rule gives for diarization (2b). Stages never start threads. The session decides when to call them.
- **Settings** are a frozen dataclass in each stage's module, `AsrConfig` and `DiarConfig`, with the provisional values below as defaults, and a module-level `DEFAULT_ASR_CONFIG` or `DEFAULT_DIAR_CONFIG` that the command reads through the module when it builds the stages (`live.asr.DEFAULT_ASR_CONFIG`, never a name bound at import), so a replacement reaches it. Only `lmt.live.tuning` (3c3) replaces those, for stage 2's sweep.

## 1. Streaming ASR, the file source and lockstep

**Split.** **1a** is `source.py` and its test. **1b** is `asr.py` without the pause rule: an update is steps 1–3 and 5–7, with `n = len(A)` and the cut at the last committed word's end. **1c** adds step 4 and the `speech` argument, and changes 1b's test helper to pass an all-speech `speech`, so 1b's cases keep their meaning. **1d** is the live default model. **1e** is the model test, and the provisional U of 0.8 s (below). 1b and 1c touch no model: the engine is a fake, and so is `speech`, except in 1c's one `models` case.

### `src/lmt/live/source.py`

```python
BLOCK = 1600

class FileSource:
    def __init__(self, path, *, paced: bool, limit: int | None = None,
                 clock=time.monotonic, sleep=time.sleep): ...
    name: str                       # the file's base name (source.file)
    position: int                   # samples handed over so far; read from any thread
    reason: str | None              # "end-of-input", "duration" or "signal", once it stops
    def blocks(self) -> Iterator[np.ndarray]
    def stop(self) -> None          # thread-safe; the next block isn't handed over

def lockstep(source, *stages) -> Iterator[tuple[int, list]]
```

- **Decoding comes first.** The constructor calls `audio.decode(path)`, so a missing, empty or corrupt file is an `InputError` (3) before capture starts (G2-7, G2-8).
- **`blocks()`** hands over 1,600-sample blocks, the last one shorter if the file ends mid-block. With `limit` (`--duration`, in samples), it stops after exactly `limit` samples, trimming the last block, with `reason = "duration"`. A `stop()` gives `"signal"`; running out gives `"end-of-input"`. `position` is updated before each block is yielded.
- **Pacing.** With `paced=True`, block i is handed over at `t0 + (i + 1) × 0.1 s`, where `t0` is the clock when `blocks()` is first iterated: a block is handed over once its audio would have finished arriving. A block that is already late goes at once, so a slow consumer never makes the source drift from the clock. With `paced=False`, blocks go as fast as they're taken. That is lockstep's source.
- **`lockstep(source, *stages)`** is lockstep (spec, G2 "Terms"): for each block, every stage's `feed` returns before the next block is taken, and it yields `(source.position, [each stage's update])`. After the last block it yields `(position, [each stage's flush()])`. It is single-threaded, so its output doesn't depend on the machine's speed.

### `src/lmt/live/asr.py`

```python
@dataclass(frozen=True)
class AsrConfig:
    update: int = 12800           # U, samples (0.8 s, provisional; stage 2 sweeps 0.5 and 1.0 s)
    max_buffer: int = 240000      # 15 s
    pause: int = 8000             # 0.5 s of non-speech commits the buffer
    prompt_chars: int = 200

@dataclass(frozen=True)
class AsrUpdate:
    words: list[Word]             # committed now, in order, times absolute, rounded to ms
    done_until: int               # no later word can start before this sample

class StreamingASR:
    def __init__(self, engine, config=DEFAULT_ASR_CONFIG, *, speech=vad_speech): ...   # `speech` from 1c
    def feed(self, samples) -> AsrUpdate
    def flush(self) -> AsrUpdate

def vad_speech(buffer) -> list[tuple[int, int]]    # 1c: Silero's speech chunks, in samples from the buffer's start
```

The method is LocalAgreement-2 over a rolling buffer (architecture, "Streaming ASR"; #82, 3a). The state: the buffer (audio from `buffer_start` to the current position), the committed words, and `previous`, the uncommitted tail of the last update's hypothesis.

**When it updates.** `feed` appends the samples. If the position has reached the next boundary (a multiple of U), it runs one update on everything it holds, and the next boundary becomes the first multiple of U after the position. In lockstep, updates fall exactly on the multiples of U. In real time, a worker that fell behind gets several blocks at once and runs one update over all of them, so it catches up and never skips audio (architecture, "Threads").

**An update:**
1. **Transcribe.** `hyp = engine.transcribe(buffer, initial_prompt=prompt)`, where `prompt` is the committed words' text, joined by spaces, cut to its last `prompt_chars` characters at a word boundary, or `None` before the first commit. Shift the times by `buffer_start`, and clip every end to the buffer's end.
2. **Drop what's already committed.** Drop words that end at or before the last committed word's end. Then, if the first k words of `hyp` (k from 5 down to 1) equal the last k committed words by key (below), and the first starts within 1 s of `buffer_start`, drop those k. This is `whisper_streaming`'s n-gram check, for a word cut in two at the buffer's start.
3. **Agreement.** `A` is the longest common prefix of `previous` and `hyp`, comparing each word's **key**: the text casefolded, with leading and trailing punctuation (Unicode category P) and white space removed. Comparing keys means a flicker in punctuation or case doesn't hold back a commit. A committed word takes the current update's text, times and probability.
4. **Pause** (1c). `speech(buffer)` gives the buffer's speech chunks. `vad_speech`, the default, runs Silero VAD on the buffer through `faster_whisper.vad.get_speech_timestamps` with `VadOptions(min_silence_duration_ms=500, speech_pad_ms=0)`, after importing `lmt.asr` (see "What G1's stage 2 gives"). A gap is a stretch of at least `pause` samples with no speech: between two speech chunks, or from the last chunk to the buffer's end (the buffer with no speech at all is one gap). Take the last gap, `g`. It counts only if no word of `hyp` straddles it: every word starting before `g.end − 0.2 s` ends by `g.start + 0.2 s`. Then `P` is the prefix of `hyp` whose words end by `g.start + 0.2 s`, and the gap's cut is `g.end − 0.2 s`, keeping 0.2 s of lead-in for what follows.
5. **Commit.** `n = max(len(A), len(P))`; commit `hyp[:n]`.
   - Times are clamped so committed words never overlap: each word's start is at least the previous committed word's end, and its end at least its start plus 10 ms. Then they are rounded to the millisecond.
   - The buffer is cut at the gap's cut if a gap counted and `len(P) ≥ len(A)`, else at the last committed word's end, else (nothing committed) not at all. `previous = hyp[n:]`.
6. **Overflow.** If the buffer is still longer than `max_buffer`, commit every word of `hyp[n:]` that ends at least 2 s before the buffer's end, as in step 5, and cut after them. If none does, cut the buffer to its last `max_buffer` samples. Audio cut this way had no words in it. So memory stays within 15 s plus one update (architecture, "Memory").
7. **`done_until`** is `buffer_start` after the cut.

**`flush()`** transcribes what's left (if at least one block), commits every word, as in step 5, and returns `done_until` = the position.

**The live default model** (1d). `models.toml` gains `default_live_asr = "distil-large-v3"`, the offline default, until stage 2 pins it (architecture, "The live model"). `Manifest` gains `default_live_asr`: optional in the file, taking `default_asr` when absent, so the test manifests stay valid; when present it must name an `asr` model, else `load_manifest` fails as it does for `default_asr`. `models.py` gains `default_live_asr(manifest) -> Model`.

**`default_models` doesn't change.** It stays one ASR model and the three pyannote models, because `pipeline.transcribe` ensures exactly it (`src/lmt/pipeline.py:40`, with `asr=None` when `--model` isn't given), and so do `lmt eval --set ci/full` and `lmt demo --sample` through it, and G3's cache key hashes it (`g3-stage1.md`). The live default there would make them download a model they never load, make `--offline` exit 5 without it, and break G3-6's "`<work>/models` is unchanged". The architecture's "`lmt transcribe` downloads missing models on first use" means the models it uses.

The live default goes only where `public-api.md` puts it, through a new **`download_defaults(manifest, asr=None) -> list[Model]`**: with `asr` given (`--model`), it is `default_models(manifest, asr=asr)`, that model and the diarization models only, as `public-api.md` says; with no `asr`, it is `default_models(manifest)` with the live default inserted right after the default ASR model when it differs. Its callers are `cli_models`'s `download` (`models.py:231`) and `_list`'s defaults (`models.py:239`), so `lmt models download` fetches the live default and `lmt models list` marks it `DEFAULT yes` and counts it in `total-default`, and 5b's `run_live`. The model test that totals the default models' bytes then counts it too. Nothing else calls it.

### Tests

- **`tests/test_live_source.py`** (no model): a 1.05 s WAV gives 10 blocks of 1,600 and one of 800, `position` rising before each; `limit` trims at exactly `limit` samples with `reason = "duration"`; `stop()` gives `"signal"`; a missing file and an empty one raise `InputError` from the constructor. Pacing with a fake clock and sleep: block i is released at `t0 + (i + 1) × 0.1`, and a late block goes at once. `lockstep` with two recording stages: each sees each block before the next is taken, and the flushes come last.
- **`tests/test_live_asr.py`** (1b, no model): a fake engine that returns scripted hypotheses, keyed by the buffer's start and length. Cases: nothing is committed on the first update; two agreeing updates commit their common prefix, comparing keys (`"started?"` agrees with `"started"`), with the second update's text; a disagreement holds a word back one update; the n-gram check drops a repeated word at the buffer's start; times are clamped and never overlap; overflow at 15 s commits and cuts; `flush` commits the rest; a `feed` of 25 blocks at once runs one update; `done_until` is `buffer_start` after the cut. The fake engine records each `initial_prompt`, and the test checks its last 200 characters. 1c changes only its helper, which then builds `StreamingASR(engine, config, speech=lambda b: [(0, len(b))])`: all speech, so no gap.
- **`tests/test_live_asr_pause.py`** (1c): with the fake engine and a scripted `speech`, a gap commits the words before it and cuts at `g.end − 0.2 s`; a gap that a word straddles isn't used; a gap shorter than `pause` isn't one; a buffer with no speech at all is one gap; `n` is `max(len(A), len(P))`, and the cut is at the gap only when `len(P) ≥ len(A)`. One case is marked `models`, since it loads Silero's ONNX model and onnxruntime: `vad_speech` on 2 s of zeros gives `[]`, and on `clip.wav`'s first 5 s at least one chunk, every chunk inside the buffer.
- **`tests/test_models_live.py`** (1d, no model): on a test manifest with a second ASR model as `default_live_asr`, `download_defaults(manifest)` is the default, then the live default, then the three pyannote models, each once, and `default_models(manifest)` is the default and the three pyannote models only; with `default_live_asr` equal to `default_asr`, or absent, the live default isn't repeated; with `asr` given, `download_defaults` equals `default_models(manifest, asr=asr)` and holds no live default; `cli_models` with `download`, `download` replaced by a fake that records its argument, passes `download_defaults(manifest)`; `lmt models list --bytes` marks the live default `yes` and adds its bytes to `total-default`; a `default_live_asr` that names a diarization model, or no model, fails `load_manifest`; and on the real `models.toml`, `default_live_asr(load_manifest()).name == "distil-large-v3"`.
- **`tests/test_pipeline.py`** (1d, no model), one new case: with `models.MANIFEST_PATH` pointing at that test manifest (live default differing) and `test_pipeline.py`'s fakes, `lmt transcribe` ensures exactly the offline default and the three pyannote models, by their literal names, not through `default_models`, so the case can't move with it. The existing line 102 stays as it is.
- **`tests/test_live_asr_models.py`** (1e, `models`), in lockstep (`FileSource(paced=False)` through `lockstep`), ASR only, with the live default model:
  - **G2-2:** on `clip.wav`, the committed words, joined by spaces, score WER ≤ 10.0 % against the clip's reference with G1's `score.wer` (G1-1's scoring).
  - **ASR's half of G2-6c:** on `two_speakers.wav`, each committed word's stream delay is the position at its commit minus the matched offline word's end. Words are matched with `lmt.eval.live.match_words` (5a) against `two_speakers_run`'s word times, and p95 is `lmt.eval.live.percentile` (5a). p95 ≤ 2.0 s. A word's full delay is at least this one, so this is a necessary condition for G2-6c. 3a4 removes this case once G2-6c's own test runs, so that CI transcribes the clip in lockstep only once.
  - Both print their figures (WER, p95, the number of matched words) to the job's log. G2-2's case is tagged `G2-2`; the delay case `G2-6c`.

**Tests of the items:** 1a, `tests/test_live_source.py`; 1b, `tests/test_live_asr.py`; 1c, `tests/test_live_asr_pause.py`, with 1b's file still passing; 1d, `tests/test_models_live.py` and `tests/test_pipeline.py`'s new case, with `tests/test_models.py` and the rest of `tests/test_pipeline.py` still passing; all in the `test` job. 1e, `tests/test_live_asr_models.py` in `test-models`, shown by the local run in its PR.

## 2. Online diarization

**Split.** **2a** is steps 3–6, which need no model: a `Clusterer` that takes one step's local activity and embeddings, plus `DiarConfig`, `Piece`, `DiarUpdate`, `NullDiarizer` and `replay`. **2b** is `OnlineDiarizer`: when it steps, steps 1 and 2 on the models, `record`, and `flush`, each step handed to the `Clusterer`. **2c** is the model test. So `replay` is the `Clusterer` run over recorded steps, and can't drift from the live path.

```python
@dataclass(frozen=True)
class Step:                       # 2a: what one step hands the clusterer, and what `record` keeps
    position: int                 # p, samples
    frames: np.ndarray            # (F,) int: each frame's index on the absolute grid, padding dropped
    activity: np.ndarray          # (F, 3) 0/1: the local speakers' hard activity
    embeddings: np.ndarray        # (3, D): L2-normalised, a row of NaN for an inactive local speaker
    weight: np.ndarray            # (3,): each local speaker's weights' sum, in seconds

class Clusterer:                  # 2a: steps 3–6
    def __init__(self, config, frame_step: int): ...   # frame_step: the model's frame step, in samples
    def step(self, step: Step) -> DiarUpdate
    def finish(self, end: int) -> DiarUpdate   # every frame final up to `end`

def replay(records: list[Step], config, frame_step: int, end: int) -> list[Piece]
```

### `src/lmt/live/diarize.py`

```python
@dataclass(frozen=True)
class DiarConfig:
    step: int = 8000              # S, 0.5 s
    window: int = 80000           # W, 5 s
    latency: int = 16000          # L, 1.0 s (provisional; stage 2 sweeps 0.5, 1.0 and 1.5 s)
    min_active: float = 0.5       # s of weighted activity for a local speaker to be embedded
    min_update: float = 1.0       # s of weighted activity for its centroid to be updated
    new_speaker: float = 0.70     # cosine distance beyond which a local speaker is new
    gamma: float = 3.0
    beta: float = 10.0
    max_speakers: int = 20

@dataclass(frozen=True)
class Piece:                      # final activity of one speaker
    start: int                    # samples
    end: int
    speaker: int                  # internal id, 0, 1, … in order of creation

@dataclass(frozen=True)
class DiarUpdate:
    pieces: list[Piece]           # newly final, within [previous final_until, final_until)
    final_until: int

class OnlineDiarizer:
    def __init__(self, segmentation, embedding, config=DEFAULT_DIAR_CONFIG, *, record=None): ...
    def feed(self, samples) -> DiarUpdate
    def flush(self) -> DiarUpdate

class NullDiarizer:               # --no-diarize: every sample is speaker 0, final at once
```

The method is Coria et al. (2021), as `diart` implements it, on the pinned models (architecture, "Incremental diarization"; #82, 4a). `configure_torch()` runs first.

**A step at position p** (a multiple of S):
1. **Segment.** The window is the audio in [p − W, p], padded with zeros on the left while p < W. `segmentation-3.0` gives powerset scores per frame. `pyannote.audio.utils.powerset.Powerset(3, 2).to_multilabel` turns them into hard 0/1 activity for three local speakers. Frame times come from the model's own sliding window (`model.receptive_field` in pyannote.audio 3.1 and later, else `model.example_output.frames`). Frames in the padding are ignored.
2. **Embed.** Each local speaker k gets frame weights `w_k(f) = a_k(f)^γ × softmax(β · a(f))_k^γ`, which keeps its frames and down-weights those it shares with another speaker (Coria et al.'s overlap-aware embedding; γ = 3, β = 10). A speaker whose weights sum to at least `min_active` seconds is **active**, and gets an embedding from `PretrainedSpeakerEmbedding(waveform, masks=weights)`. Its result is L2-normalised. A NaN result (too little audio) makes the speaker inactive.
3. **Match.** The cost of local speaker k against speaker g is the cosine distance between k's embedding and g's centroid. `scipy.optimize.linear_sum_assignment` pairs active local speakers with existing speakers, two local speakers never taking the same one. A pair farther than `new_speaker` is undone. A local speaker left unpaired becomes a new speaker, with its embedding as the centroid, unless there are already `max_speakers`. In that case it takes the nearest speaker not taken in this window, or is dropped if there is none. Ties go to the lower index, so the result is deterministic.
4. **Update centroids.** A matched speaker whose weights sum to at least `min_update` seconds adds its embedding to its centroid. A centroid is a sum of unit vectors, which cosine distance doesn't mind.
5. **Accumulate.** Each frame maps to the absolute frame grid (the model's frame step, from sample 0), at the nearest grid index. For every grid frame, the diarizer keeps how many windows covered it and, per speaker, the sum of its activity. An inactive or dropped local speaker adds nothing.
6. **Finalize.** Every grid frame that starts before `p − L` and isn't yet final becomes final. A speaker is active in it if its mean activity over the covering windows is at least 0.5. Runs of active frames become `Piece`s, and the frame accumulators before `final_until` are dropped, so memory stays bounded.

**When it steps, and catching up.** `feed` appends the samples and steps at the multiples of S it has passed. In lockstep that is at most one. When a worker in real time has fallen behind and several are pending, it steps at the last of them, and at earlier ones spaced `W − L` apart going back (4.0 s at L = 1.0 s), so that every frame is inside the window of the step that makes it final. Frames are never skipped, but a diarizer behind by 12 s takes 3 steps, not 24, to catch up.

**`flush()`** steps once at the end of the audio (window [end − W, end]) and makes every frame final up to the end.

**Labels never change** (#82, 4a): a frame, once final, is never touched again, and a speaker's id is fixed when it is created. The join maps ids to `S1`, `S2`, … (3a1).

**`record`** is for stage 2's tuning. When given a list, each step appends its `Step`. `replay(records, config, frame_step, end)` runs a fresh `Clusterer` over them and `finish(end)`, so new thresholds can be scored on AMI's dev meetings without running the models again.

**The provisional thresholds.** `new_speaker` = 0.70 is `speaker-diarization-3.1`'s own clustering threshold (0.7045…, in its `config.yaml`), for the same embedding model and distance. `min_active` and `min_update` are set so that a local speaker needs half a second to be embedded and a second to move its centroid. Stage 2 tunes all three on AMI's dev meetings, never its test meetings, with `replay`, and this file then records the values (architecture, "Incremental diarization").

### Tests

- **`tests/test_live_diarize.py`** (2a, no model), on scripted `Step`s straight into a `Clusterer`. Matching: a local speaker near a centroid is matched; one beyond `new_speaker` becomes new; two local speakers never take one speaker; at `max_speakers`, a would-be new speaker takes the nearest free one, or is dropped if none is free; ties go to the lower index; an inactive one adds nothing; a matched speaker below `min_update` leaves its centroid unchanged. Finalization: each step makes exactly the grid frames before `p − L` final; a speaker is active in a final frame when its mean activity over the covering windows is at least 0.5; a final frame never changes, which the test checks with later steps that disagree with it; the accumulators before `final_until` are dropped. `finish` makes everything final. `replay` of the same steps twice gives the same pieces. `NullDiarizer` gives speaker 0, final at once, for any `feed`.
- **`tests/test_live_diarize_online.py`** (2b, no model): fake segmentation and embedding models, scripted per window, with a `receptive_field` (and, in one case, only `example_output.frames`). `configure_torch` is called first. Weights: a frame shared by two speakers weighs less than one held alone. Padding: while p < W, frames in the padding reach no `Step`. Finalization: nothing is final before `L + S`. Catch-up: 12 s fed at once steps at 4, 8 and 12 s from a last step at 0, and every frame before 11 s is final and covered. `flush` makes everything final. With `record`, `replay` with the same config gives the same pieces as the live run.
- **`tests/test_live_diarize_models.py`** (2c, `models`, tagged `G2-3`): `two_speakers.wav` in lockstep (`FileSource(paced=False)`), diarization alone. The final pieces hold exactly two speakers. For each speaker in the clip's RTTM, take the part of their turns' time that some final piece covers:
  - **Purity:** at least 90 % of that covered time is on the speaker that covers most of it, and those two majority speakers differ. This is G2-3's rule on time, not words. Like G2-3 on words, where every committed word carries a label, it counts only time that has a label.
  - **Coverage:** that covered time is at least 60 % of the speaker's RTTM time, so a diarizer that labels little of a speaker can't pass on purity alone.

  The RTTM's turns are whole LibriSpeech utterances with their pauses, which diarization rightly leaves unlabelled. So coverage can't approach 100 %, even for the offline `speaker-diarization-3.1` that passes G1-3 (70.7 % and 84.2 %; online 77.4 % and 85.5 %; #434, 2026-10-29). The 60 % floor sits below both, and would fail a diarizer that misses about half of a speaker's speech. G2-3 itself is 3a4's, on words, and doesn't change. The test also prints the clip's DER and each speaker's covered and majority seconds.

**Tests of the items:** 2a, `tests/test_live_diarize.py`; 2b, `tests/test_live_diarize_online.py`, with 2a's file still passing; both in the `test` job. 2c, `tests/test_live_diarize_models.py` in `test-models`, shown by the local run in its PR.

## 3a. The join, the events and the lockstep session

**Split.** **3a1** is `join.py`, which needs only 1b's `AsrUpdate` and 2a's `DiarUpdate` and `Piece`. **3a2** is `events.py` and the events schema. **3a3** is `session.py`'s `run_lockstep`, tested with fake stages. **3a4** is the model test, which also drops 1e's two-speaker case.

**Words-first, per P12.** P12 made `align.build` turns-first when there are turns, for the offline product. The live join keeps the words-first rules: a word is labelled on its own, as soon as final activity covers it, and a segment closes on a speaker change or on `align.breaks`. It never calls `align.build`. The offline word times that G2's tests compare against come from `two_speakers_run`'s JSON. P12 changed that JSON's segments, not its word times. Where two turns overlap, though, its segments can hold words out of time order, so every G2 test that reads them takes the words of every segment and sorts them by `(start, end)` before matching.

### `src/lmt/live/join.py`

```python
@dataclass(frozen=True)
class WordsOut:      # → a "words" event
    segment: int; speaker: str; label: str; words: list[Word]
@dataclass(frozen=True)
class SegmentOut:    # → a "segment" event
    segment: Segment; number: int

class Join:
    def __init__(self): ...
    def add_words(self, update: AsrUpdate) -> None
    def add_activity(self, update: DiarUpdate) -> None
    def poll(self) -> list[WordsOut | SegmentOut]
    def finish(self) -> list[WordsOut | SegmentOut]
    speakers: list[Speaker]; segments: list[Segment]     # the transcript so far
```

- **Labelling.** Words are labelled in order. A word is labelled once `final_until` has reached its end (architecture, "Join"), with `align.assign_speaker(word, turns, previous)`. `turns` are the final pieces as `lmt.transcript.Turn`s in seconds, merged per speaker where they touch, **clipped at the word's end**. So the "nearest turn within 1 s" looks only back from the word. Looking ahead would make every such word wait up to 1 s more, against the delay budget. A word that `assign_speaker` leaves without a speaker (the first words, before any turn) takes the first final turn's speaker, and waits for one. At `finish`, if diarization found no speech at all, those words take a speaker of their own.
- **Ids.** An internal speaker gets the next id, `S1`, `S2`, …, and the label `Speaker N`, when its first word is labelled. So the ids follow the first appearance in the transcript, as `public-api.md` requires, and never change.
- **Segments** follow alignment's words-first rules: a labelled word starts a new segment when its speaker differs from the segment's, or `align.breaks(last word, word, segment start)`. A segment closes when the next labelled word breaks it; at once, when its last word ends a sentence; when ASR's `done_until` has passed its last word's end by 1 s and no word is waiting for a label, since no later word can then join it; and at `finish`. Its `text` is `align.segment_text(words)`.
- **`poll`** returns, in order, one `WordsOut` for each run of words labelled in the same segment, and a `SegmentOut` for each segment that closes. A segment's `SegmentOut` always comes before the next segment's words.
- **`finish`** labels every word left (final activity then reaches the end) and closes the last segment.
- Turns that ended more than 2 s before the oldest unlabelled word are dropped, so the join's memory stays bounded.

### `src/lmt/live/events.py`

```python
class EventWriter:
    def __init__(self, stream, *, jsonl: bool, clock_t: Callable[[], int]): ...
    def start(self, source: dict, models: dict) -> None
    def emit(self, out: WordsOut | SegmentOut) -> None
    def stop(self, reason: str) -> None
```

- **JSONL** (live events 1.0, `public-api.md`): one `json.dumps(event, ensure_ascii=False, separators=(",", ":"))` per line, with the fields in the table's order, then a flush. `t` is `clock_t()` in seconds, rounded to the millisecond: in lockstep, the position of the last block handed over; in real time, the source's `position` as the event is written. `start`'s `t` is 0, and its `schema_version` is `"1.0"`.
- **`start`'s `source`** is the transcript's `source` without `duration`, which isn't known yet: `file`, `live: true`, and `device` for a device.
- **`stop`** is written once the workers have finished the captured audio and the join has emitted every word, just before the final formats are written. Its `t` is the session's length. So `stop` is always the last event, and the time it arrives, against its `t`, is how far behind real time the pipeline ended (5a's `behind_seconds`).
- **Text** (without `--jsonl`): a segment's first words start a line, `[HH:MM:SS] Speaker 1: ` followed by the words joined by spaces. Later words in the segment add `" " + words` to it. Its `SegmentOut` ends the line. `HH:MM:SS` is the segment's start, rounded down, as the text export writes it. Every write is flushed.

### `schema/live-events.schema.json`

JSON Schema 2020-12: `oneOf` four objects, selected by `type` (`const`), each with exactly the fields of `public-api.md`'s table required and `additionalProperties` allowed, since a minor version adds fields. `t` is a number ≥ 0; `segment` an integer ≥ 1; `speaker` matches `^S[1-9][0-9]*$`; `words` is a non-empty array of `{start, end, text, probability}`; `reason` is one of `end-of-input`, `duration` or `signal`. `start`'s `models` is the transcript schema's `models` object. A copy goes in `src/lmt/schema/`, and `tests/test_live_events.py` checks the two are identical, as `tests/test_export.py` does for the transcript schema.

### `src/lmt/live/session.py`

```python
@dataclass
class Sinks:
    on_block: Callable[[np.ndarray], None] = lambda b: None      # --save-audio (3b3)
    on_segment: Callable[[Segment, str], None] = lambda s, l: None  # the growing <stem>.txt (3b3)

@dataclass(frozen=True)
class SessionResult:
    speakers: list[Speaker]; segments: list[Segment]; samples: int; reason: str

def run_lockstep(source, asr, diarizer, writer, sinks=Sinks(), *, source_info: dict, models: dict) -> SessionResult
```

`run_lockstep` writes `start` (`writer.start(source_info, models)`: `start`'s `source` and the models' field, which the caller has and the session can't derive), then, through `lmt.live.source.lockstep(source, asr, diarizer)`, after each block: `sinks.on_block`, the two updates into the join, `poll`, and each output through `sinks.on_segment` (for a `SegmentOut`, first) and the writer. At the end: the two flushes, `finish`, the same again, and `stop`. 3c1 adds the threaded run beside it.

### Tests

- **`tests/test_live_join.py`** (3a1, no model), with scripted `AsrUpdate`s and `DiarUpdate`s: a word waits until `final_until` reaches its end, then takes the overlapping speaker; the 1 s rule looks only back; the first words wait for the first turn; ids follow the first labelled word, not the diarizer's internal order; a speaker change, a 1 s pause, a sentence end, a 30 s segment and `done_until` each close a segment; `SegmentOut` comes before the next segment's words; `finish` labels and closes everything.
- **`tests/test_live_events.py`** (3a2, no model): each event validates against `schema/live-events.schema.json` and has its fields in order; the schema rejects a missing field, a `speaker` of `s1`, an empty `words` and an unknown `reason`; the published schema equals `src/lmt/schema/`'s copy; every event in 5a's fixture logs (`tests/fixtures/eval/live/run*.jsonl`) validates, so 5's fixtures are real events; a stream's lines arrive one per write through a pipe (`os.pipe`, read in another thread), so flushing works; the text form of a fixed sequence, against an expected string.
- **`tests/test_live_session.py`** (3a3, no model), with fake stages that return scripted updates and a writer into a `StringIO`: `start` comes first, carrying the `source_info` and `models` given, and `stop` last; each block reaches both stages before the next; for a `SegmentOut`, `sinks.on_segment` is called before the writer writes its event; `sinks.on_block` sees every block; the flushes and `finish` come after the last block; `SessionResult` holds the join's speakers and segments, the samples and the source's `reason`.
- **`tests/test_live_session_models.py`** (3a4, `models`), one lockstep run of the whole pipeline on `two_speakers.wav`, through `FileSource(paced=False)`, shared by the three cases below. Offline word times come from `two_speakers_run`, and words are matched with `lmt.eval.live.match_words`.
  - **G2-1:** every event validates; `start` first and `stop` last; every committed word has a speaker; words come in order of `start` and never overlap; no `(start, end, text)` appears twice. Every matched offline word whose end is at least 5 s before the clip's end is committed in an event whose `t` is before the clip's duration, so before the last block. The spec's "every word" is read as every matched word, since an unmatched one can't be found in the live stream; the test prints the share matched.
  - **G2-3:** exactly two speakers. For each reference speaker, a committed word belongs to the RTTM turn holding its midpoint (G1-3's rule, by word time). At least 90 % of each speaker's words carry their majority label, and the two majority labels differ.
  - **G2-6c:** each matched word's stream delay is its event's `t` minus the matched offline word's end. p95 by nearest rank (`lmt.eval.live.percentile`) ≤ 2.0 s. It prints p50, p95, the maximum and the number matched.
- **`tests/test_live_asr_models.py`** loses 1e's two-speaker case, which G2-6c now covers. Its G2-2 case stays.

**Tests of the items:** 3a1, `tests/test_live_join.py`; 3a2, `tests/test_live_events.py`; 3a3, `tests/test_live_session.py`; all in the `test` job. 3a4, `tests/test_live_session_models.py` in `test-models`, shown by the local run in its PR, with G2-1's share matched and G2-6c's p50, p95, maximum and count.

## 3b. `lmt live`: the command and its outputs

**Split.** **3b1** is the parser and `validate`, with a stub handler, so G1-6's table test covers `lmt live` early. **3b2** is `output.py`, which needs only the exporters. **3b3** replaces the stub with the command: the checks before capture, the stages, the session and the outputs. **3b4** is the test per option and G2-5 (ii) and (iii) through the command. **3b5** is the shared run. G1.2 already writes transcript JSON 1.1 with `source.live` and `source.device` in its schema, so no 3b item touches the schema, `export/json.py` or a fixture.

### `src/lmt/cli.py` (3b1)

Adds the `live` subcommand, after `transcribe`, with exactly `public-api.md`'s options and defaults, and `set_defaults(handler="lmt.live.command:cli_live")`. `tests/test_cli.py`'s `LATER_GOAL` stops matching "(G2)", and its two tests that list the sections change with it, so the table test covers `lmt live` (G1-6, G2-7). Until 3b3, `src/lmt/live/command.py` is a stub whose `cli_live` raises `NotBuilt("lmt live")` (exit 1, one `lmt: error:` line), as `cli.py`'s docstring has later items replace a stub module. Its message says "G1 stage 2", the only form `NotBuilt` has; it lasts until 3b3.

`validate` gains `lmt live`'s rules, each a `UsageError` (2) naming the option: `--formats` as for `transcribe`; `--max-speakers` from 1 to 20; `--no-diarize` with `--max-speakers`; `--device` with `--from-file`; `--duration` a number above 0; `--name` a plain file name (not empty, no `/`, not starting with `.`); `--model` an ASR model in the manifest. With `--list-devices`, none of these is checked, since it lists and exits 0 whatever else is given.

### `src/lmt/live/command.py` (3b3)

```python
LOCKSTEP = False      # set only by tests/live_lockstep.py: lockstep, not reachable from the CLI
def cli_live(args) -> int
def load_stages(args, manifest) -> tuple[StreamingASR, OnlineDiarizer | NullDiarizer, dict]   # steps 5 and 6; tests replace it
```

**Before capture** (G2-7: every error that can be found before capture is found before it, and nothing is written):
1. `--list-devices`: print the input devices (4c's `mic.input_devices()`), one per line, `<index>\t<name>\t<channels> ch\t<rate> Hz`, with `*` after the index of the default. With none, print `No input devices.` Exit 0, whatever else is given.
2. The stem: `--name`, else `live-` and the local start time as `YYYYMMDD-HHMMSS`.
3. `export.check(out_dir, stem, formats + ["wav"] with --save-audio, overwrite=…)`: the output directory exists and is writable, else `InputError` (3). Each `<stem>.<fmt>`, and `<stem>.wav` with `--save-audio`, doesn't exist, unless `--overwrite`, else `UsageError` (2) naming the file.
4. The source. `--from-file`: `FileSource(path, paced=not LOCKSTEP, limit=…)`, which decodes the file now (3 for a missing, empty, corrupt or unsupported file, as `lmt transcribe` gives; G2-8). A device: `mic.resolve(args.device)` and `MicSource` (4c, 4d), 3 for no input device, an unknown one, or PortAudio missing. The stream isn't opened yet.
5. The models (`load_stages`): `models.ensure(...)` for the ASR model (`--model`, else `models.default_live_asr`) and, unless `--no-diarize`, `segmentation-3.0` and the embedding model, honouring `--offline` (5). Then load them, with `lmt.asr.load`, `lmt.diarize.load_segmentation` and `load_embedding`.
6. The stages (`load_stages`), from the options, with the settings read through their modules (Shared conventions):
   - ASR: `StreamingASR(asr.load(<the ASR model's directory>), live.asr.DEFAULT_ASR_CONFIG)`.
   - Diarization: with `--no-diarize`, `NullDiarizer()`, so every segment is `S1`, and `models.diarization` is `null`. Otherwise `OnlineDiarizer(segmentation, embedding, config)`, where `config` is `DEFAULT_DIAR_CONFIG`, or `dataclasses.replace(DEFAULT_DIAR_CONFIG, max_speakers=N)` with `--max-speakers N`. With the option not set, the default's 20 holds, the most the option allows.

**Capture** starts when the stream opens (a device) or the first block is taken (a file). `<stem>.txt` (if `txt` is among the formats) and `<stem>.wav` (with `--save-audio`) are created at that moment, not before. The session runs, given `source_info` (`start`'s `source`: 3b2's transcript `source` without `duration`) and `models` (the models' field below, which `live_transcript` also takes): `run_lockstep` in 3b3, with a paced source unless `LOCKSTEP`; 3c2 switches to the threaded run unless `LOCKSTEP`. A device that fails to open is `InputError` (3), and nothing has been written.

**The models' field**, in the transcript and the `start` event: `asr` is the live model's manifest entry (`name`, `repository`, `revision`). `diarization` is `speaker-diarization-3.1`'s entry, as `lmt transcribe` writes it, since the live method runs on the models that entry's pipeline names, each pinned in the same manifest. It is `null` with `--no-diarize`. `source.live: true` marks the method.

**Stopping in 3b3:** the end of the file and `--duration`. Ctrl-C still raises `KeyboardInterrupt`, which `cli.main` turns into 130. 3c2 gives it its own meaning.

**Exit codes:** 0 when the session ends and the outputs are written, even with no speech: a live session's silence isn't an error (G2-5 (iii)), so `lmt live` never exits 4. It writes a transcript with no segments.

### `src/lmt/live/output.py` (3b2)

- **`GrowingText(path)`:** opened at capture start (truncated, since step 3 checked it). `append(segment, label)` writes `export.txt.render_segment(segment, label)` and a newline, then flushes. The session calls it for each `SegmentOut` **before** writing the `segment` event, so a reader who has seen the event finds the line in the file (G2-4).
- **`WavWriter(path)`:** 16 kHz mono 16-bit PCM. It writes a 44-byte RIFF header, then each block as it arrives (samples clipped to [−1, 1], times 32,767, rounded, little-endian `int16`, as G3's demo writes WAV). After each block it rewrites the header's two sizes, so the file is a valid WAV of everything so far if the process dies (`public-api.md`, "What a failed session keeps").
- **`save(transcript, out_dir, stem, formats, *, abandon: threading.Event)`:** renders every format with `export.render`, writes each to a temporary file in `out_dir`, then renames them all into place. Before the renames it checks `abandon` (set by 3c2's second SIGINT), and renames nothing if it is set. The temporary files are created and renamed inside a `try`, whose `finally` removes every temporary file not yet renamed. Each file gets the mode `export.write` gives its outputs (#286: `0o666` less the umask). So any exception while writing them, 3c2's `KeyboardInterrupt` from a second SIGINT among them, leaves no temporary file and no final format (`public-api.md`, exit 130: "Partial outputs are deleted"). `<stem>.txt` is replaced by the final rendering, which equals what was appended, since both come from `render_segment`.
- **The transcript** (`live_transcript(result, source, models)`) is `Transcript(transcript.SCHEMA_VERSION, lmt_version, source, models, speakers, segments)`, from the `SessionResult`. `source` is `{"file": <the file's base name, or the stem>, "duration": <samples / 16000, to the ms>, "live": true}`, plus `"device": <name>` for a device (`public-api.md`, transcript JSON 1.1).

### `tests/live_lockstep.py` (3b3)

The one way to reach lockstep from a subprocess: it sets `lmt.live.command.LOCKSTEP = True`, then exits with `lmt.cli.main(sys.argv[1:])`. It isn't part of the package.

### Tests

- **`tests/test_live_cli_args.py`** (3b1, no model, tagged `G2-7`): `lmt live --help` exits 0; each `validate` rule gives exit 2 and one `lmt: error:` line naming its option; `--list-devices` with otherwise conflicting options isn't rejected by `validate`; a valid command line passes `validate`, called directly on the parsed arguments, with every default as `public-api.md` gives it. `tests/test_cli.py`'s table test passes with `live` in the documented set.
- **`tests/test_live_cli.py`** (3b3, no model, tagged `G2-7` and `G2-8`; `load_stages` replaced by fake stages where a case gets that far): each case of G2-7, checking exit code, one `lmt: error:` line naming the file or option, no file written, and no audio captured (the fake device's stream was never opened, and no `start` event): an unknown device (3), a missing `--from-file` input (3), an existing output without `--overwrite` (2), `<stem>.wav` existing with `--save-audio` (2), an unwritable output directory (3). The default `--name` has the documented form. `--list-devices` prints the stand-in's devices in the documented form, `*` on the default. A `--from-file` run on a short WAV with fake stages exits 0 and writes the four outputs, whose JSON validates with `source.live` true, and a `--jsonl` run's stdout is `start`, the events, `stop`. **G2-8, bad input:** G1-11's empty file, random bytes named `.wav`, and a `.txt` file (from `tests/bad_inputs.py`) each exit 3 through `lmt live --from-file`, with one `lmt: error:` line and no outputs, as `lmt transcribe` does.
- **`tests/test_live_options.py`** (3b4, no model, tagged `G2-7`, and `G2-5` for its two cases):
  - **What each option does** (G2-7: each option has a test), with fake stages, `tests/fake_sounddevice.py` in `sys.modules["sounddevice"]` (`mic` imports it inside its functions), and `asr.load` and the diarization loaders replaced by fakes that record what they were given:
    - `--max-speakers 3`: the diarizer is built with `config.max_speakers == 3`; without the option, 20.
    - `--no-diarize`: the diarizer is a `NullDiarizer`, every segment of the JSON is `S1`, and `models.diarization` is `null`.
    - `--model <a second ASR model in a test manifest>`: `models.ensure` is asked for that model, and `asr.load` gets its directory; without the option, the live default's.
    - `--device 1` and `--device <a unique part of device 1's name>`: the stand-in's stream opens with `device=1`, and the JSON's `source.device` is that device's name.
    - `-f srt,json`: no `<stem>.txt` is created, at capture start or after; `<stem>.srt` and `<stem>.json` are.
    - `--offline` with an empty `LMT_CACHE_DIR` and the real `models.ensure`: exit 5, one `lmt: error:` line, no output, and no audio captured.
    - `-o <dir> -n meeting`: the outputs are `<dir>/meeting.<fmt>`, and nothing is written in the working directory.

    `-v` is 3c2's.
  - **G2-5 (ii) through the command:** with the stand-in holding no input device, `lmt live` exits 3 with one `lmt: error:` line, and `lmt live --list-devices` exits 0 and prints `No input devices.`. In CI (`CI=true`), the same through the real `sounddevice`, as 4c's test does.
  - **G2-5 (iii) through the command:** with the stand-in's device silent throughout and `--duration 4`, `lmt live` exits 0, stderr holds exactly one `lmt: warning:` line, the silent-device warning, and the JSON has no segments. With a 4 s WAV of exact zeros, `lmt live --from-file` exits 0, stderr holds no `lmt: warning:` line, and the JSON has no segments.
- **`tests/test_live_output.py`** (3b2, no model): `GrowingText` holds one line per appended segment and is flushed; `WavWriter`'s file reads back with `wave` after every block, with the right frame count; `save` renames nothing when `abandon` is set, and leaves no temporary file either way. An exception raised between two temporary writes (a patched writer that raises `KeyboardInterrupt` on the second format) propagates, and leaves no temporary file and no final format in `out_dir`. `live_transcript` gives a document that validates against the schema, with `source.live` true, and `source.device` only for a device.
- **`tests/test_live_shared_run.py`** (3b5, `models`, tagged `G2-8` and `G2-4`): **the shared run**, the session fixture `live_run` in `tests/conftest.py`, since `test_live_session_models.py` shares it. It runs `tests/live_lockstep.py live --from-file two_speakers.wav --jsonl --save-audio -o <dir>` through `tests/isolation.py`'s `run_isolated`, with fresh `HOME`, `TMPDIR`, `XDG_CACHE_HOME` and working directory, and snapshots before and after. Its cases:
  - **G2-8, network and files:** exit 0; no connection (the guard's log, `LMT_NETGUARD_LOG`, empty or absent, with `PYTHONPATH=tests/netguard`, as G1-13's test sets it up); under `CI`, `isolated` is true; the only new files are the four outputs and `<stem>.wav`; nothing under `HOME`, `TMPDIR`, `XDG_CACHE_HOME` or `LMT_CACHE_DIR` is new, changed or gone. This needs #402 (P13), without which onnxruntime and matplotlib write under them.
  - **G2-4's outputs, in lockstep:** the JSON validates against `schema/transcript.schema.json`, has `schema_version` `1.1` and `source.live` `true`, and its segments' words are exactly the events' committed words, in order, with the same speakers. The text file equals the text exporter's rendering of the JSON. `<stem>.wav` decodes to the clip's samples, within one 16-bit step.
- **`tests/test_live_session_models.py`** (3b5): G2-1, G2-3 and G2-6c move onto `live_run`'s events, whose `t` in lockstep is the position at each event, and its in-process run goes. So CI runs the two-speaker clip in lockstep once. Their checks are unchanged.

**Tests of the items:** 3b1, `tests/test_live_cli_args.py` and `tests/test_cli.py`; 3b2, `tests/test_live_output.py`; 3b3, `tests/test_live_cli.py`; 3b4, `tests/test_live_options.py`; all in the `test` job. 3b5, `tests/test_live_shared_run.py` and `tests/test_live_session_models.py` in `test-models`, shown by the local run in its PR (on the Mac, `isolated` is false, and the PR says so, as P7c's does).

## 3c. Real time, signals and the tuning entry point

**Split.** **3c1** is `run_threaded` and its stage timings, tested in process with fake stages. **3c2** puts it into the command, with signals, the second Ctrl-C, a bug's exit 1 and `-v`, tested in subprocesses on fake stages through a new helper, `tests/live_fakes.py`, so signals are checked without a model. **3c3** is the tuning entry point. **3c4** is G2-4's model test at real-time pace.

### The threaded run (`src/lmt/live/session.py`, 3c1)

`run_threaded(source, asr, diarizer, writer, sinks, *, source_info: dict, models: dict) -> SessionResult`, which writes `start` with them as `run_lockstep` does, and which `cli_live` uses unless `LOCKSTEP` (from 3c2):
- **The capture thread** iterates `source.blocks()`. For each block, it calls `sinks.on_block` (the WAV writer) and puts the block on the ASR queue and the diarization queue. At the end, it puts a stop marker on both.
- **Two worker threads**, one per stage. Each takes every block that has queued up, concatenates them and calls `feed` once, so it catches up rather than drifting. At the stop marker it feeds what came before it, calls `flush` and finishes. Each puts `(stage, update, samples processed)` on the main queue. An exception in a worker goes on the main queue too, and the main thread raises it.
- **The main thread** takes from the main queue with a 0.1 s timeout, feeds the join, and writes what `poll` returns, as `run_lockstep` does, with `t` = `source.position` at each write. After both workers finish: `finish`, then `stop`.
- **Behind.** `behind = source.position − min(samples processed by each worker)`. When it first exceeds 5 s, stderr gets one `lmt: warning: live: <n> s behind real time`. It warns again only after `behind` has dropped below 5 s and risen past it again.
- **The microphone's callback** only copies into a queue (4d), so the capture thread can't make it drop audio.
- **Timings.** Each worker times each `feed` and `flush` with `time.perf_counter`. `SessionResult` gains `stats`: the count, mean and maximum seconds of ASR updates and of diarization steps, and the largest `behind`, in seconds. `run_lockstep` fills it too, with `behind` 0. 3c2's `-v` prints it.

### Signals and stopping (`src/lmt/live/command.py`, 3c2)

- **The first SIGINT, or SIGTERM:** `source.stop()`, with `reason = "signal"`. The SIGINT handler is then swapped for the second one. Capture stops, the workers finish the captured audio, and the outputs are written. Exit 0.
- **The second SIGINT,** at any time after the first until exit (the "saving" phase, `public-api.md`): if `save` has started its renames, it only sets `abandon`, too late to matter, and the save finishes with exit 0. Otherwise it raises `KeyboardInterrupt` in the main thread, which waits on its queue with a timeout, so it is woken at once. `cli.main` gives 130. No final format is written, since `save` writes only through temporary files and renames. If the main thread is inside `save`, writing its temporary files, the exception passes through `save`'s `finally`, which removes them (3b2, `output.py`). `<stem>.txt` and `<stem>.wav` stay as written so far. The worker threads are daemon threads, so they don't hold up the exit.
- **Further SIGTERMs** after the first are ignored.
- **A bug** in a worker or the main thread exits 1 with the error report (`public-api.md`, exit codes), and keeps `<stem>.txt` and `<stem>.wav`.

### `-v` (3c2)

At the end, from `SessionResult.stats`, one stderr line per stage: the number of ASR updates with their mean and maximum seconds; the number of diarization steps, likewise; and the largest `behind`. For a device, one more line with `MicSource`'s input-overflow count. Stage 2 reads these.

### `tests/live_fakes.py` (3c2)

Like `tests/live_lockstep.py`, a script outside the package: it replaces `lmt.live.command.load_stages` with one that returns fake stages, then exits with `lmt.cli.main(sys.argv[1:])`. The fake ASR stage commits one scripted word per second of audio; the fake diarizer makes everything speaker 0, final at once. `LMT_FAKE_LIVE_SLOW` (seconds) makes each fake `flush` sleep that long, so a test can land a signal while the workers are still finishing. `LMT_FAKE_LIVE_FAIL=asr` makes the ASR stage raise on its fifth `feed`. Only tests set these; the product never reads them.

### `tests/live_stop_probe.py` (3c4, #567)

Like `tests/live_lockstep.py`, a script outside the package, run as `python tests/live_stop_probe.py <marker> live …`. It wraps `lmt.live.command._Signals._handle` before the command runs: the wrapper calls the original, then, the first time `self._stopped` is true after it returns, creates the file `<marker>`. Then it exits with `lmt.cli.main(<the arguments after the marker>)`. It only observes, so the real models, the real handler and the real `save` run unchanged. Since `_handle` may raise `KeyboardInterrupt` on the second SIGINT, the marker is created only after a call that returned, and creating it is the wrapper's last step.

### `src/lmt/live/tuning.py` (3c3)

```
python -m lmt.live.tuning [--set asr.update=8000] [--set diar.latency=24000] … -- live --from-file X --jsonl …
```

It replaces fields of `DEFAULT_ASR_CONFIG` and `DEFAULT_DIAR_CONFIG` with `dataclasses.replace`, each value parsed as the field's type, prints the effective settings to stderr, then exits with `lmt.cli.main(<the arguments after -->)`. An unknown key, or a value that doesn't parse, exits 2. It is internal, like `python -m lmt.eval.datasets`, and isn't in the public API.

### Tests

- **`tests/test_live_realtime.py`** (3c1, no model), calling `run_threaded` in process with a paced `FileSource` on a fake clock or a short WAV, and fake stages, some made slow with sleeps: a worker that falls 6 s behind gets one `feed` covering all the queued blocks, and the warning appears once, then again only after it has caught up and fallen behind again; every block reaches both stages, in order; a worker's exception is raised from `run_threaded`, after the `on_segment` calls already made; the main thread's `t` follows `source.position`; `stats` counts every `feed` and `flush`.
- **`tests/test_live_signals.py`** (3c2, no model, tagged `G2-4`), each `tests/live_fakes.py live --from-file <a 30 s WAV> --jsonl -f txt,srt,vtt,json` in a subprocess at real-time pace, the cases at the same time as each other: SIGINT after 3 s and SIGTERM after 3 s each exit 0 with `stop`'s reason `signal` and the four formats written; a second SIGINT 0.1 s after the first, with `LMT_FAKE_LIVE_SLOW=2`, exits 130, with no `.srt`, `.vtt` or `.json`, no temporary file, and `<stem>.txt` as written before the stop; a second SIGTERM is ignored (exit 0); `LMT_FAKE_LIVE_FAIL=asr` exits 1 with one `lmt: error: internal:` line and keeps `<stem>.txt` and `<stem>.wav` (with `--save-audio`); `-v` prints the documented lines.
- **`tests/test_live_realtime_models.py`** (3c4, `models`, tagged `G2-4`), G2-4, each `lmt live --from-file two_speakers.wav --jsonl -f txt,srt,vtt,json` in a subprocess at real-time pace. The stop cases run at the same time as each other, since they check behaviour, not speed. The run to the end of the file runs alone.
  - **The end of the file:** exit 0, `stop`'s reason `end-of-input`. Each time a `segment` event arrives, `<stem>.txt` already holds a line for every segment closed so far. Its p95 delay, by 5a's and 5b's functions (`run_once`'s arrivals, `match_words`, `percentile`), with arrival times against the offline word times, goes to the log, and isn't checked.
  - **`--duration 20`:** exit 0, reason `duration`, `source.duration` 20.0.
  - **SIGINT at 20 s, and SIGTERM at 20 s** (after the `start` event's arrival): exit 0, reason `signal`, and no segment ends after 21 s.
  - **For each of the four:** the final formats exist, the JSON validates, and its segments hold exactly the events' committed words, in order, with the same speakers.
  - **The second SIGINT:** SIGINT at 20 s, then again as soon as the first stop has been handled, while the workers are still finishing: exit 130; no `.srt`, `.vtt` or `.json`, and no temporary file; `<stem>.txt` holds what was written before the stop. This case alone runs through `tests/live_stop_probe.py` (below) rather than `python -m lmt`, with its marker path outside the output directory. After the first SIGINT, the timer thread polls for the marker every 0.01 s, then sends the second. If the marker hasn't appeared by the case's timeout, the case fails, saying so. A fixed gap can't work: two SIGINTs that reach the process before its main thread runs the handler are one call to it (CPython's C handler only sets a flag, and the kernel keeps one pending SIGINT), so on a loaded runner, 5 s behind, 0.1 s merged them (#558, #567).
- **`tests/test_live_tuning.py`** (3c3, no model): an override reaches the stage the command builds (`asr.load` and the diarization loaders replaced by fakes, and the real `load_stages`, so the built stages' configs carry the override); an unknown key, and a value that doesn't parse, exit 2; with no `--set`, the configs are the defaults.

If 3c4's runs push `test-models` past its `timeout-minutes`, 3c4 raises the timeout and reports the job's measured time on the item. That changes no check.

**Tests of the items:** 3c1, `tests/test_live_realtime.py`; 3c2, `tests/test_live_signals.py`; 3c3, `tests/test_live_tuning.py`; all in the `test` job. 3c4, `tests/test_live_realtime_models.py` in `test-models`, shown by the local run in its PR.

## 4. The microphone source

**First step, before any PR:** add `sounddevice` to `dependencies`, `uv lock`, and run G1's licence check (`check_licences.py --inventory`) on both platforms' installs, as G1's item 1b did. Post both tables on the item. Expected: `sounddevice` (MIT), with `cffi` (MIT) and `pycparser` (BSD-3-Clause) probably already in the tree through `soundfile`, and on macOS the bundled `_sounddevice_data/portaudio-binaries/libportaudio.dylib` (PortAudio, MIT), which gets a `[[licences.library]]` entry for `macos-arm64`. If anything falls outside the Owner's answer 2a (`project_requirements.md` §7), escalate it to the Owner and stop before the PR.

**Split.** **4a** is that first step and its PR: the dependency, the lock, the `[[licences.library]]` entries, `libportaudio2` in the `test` job, and `tests/test_portaudio.py`. **4b** extracts `audio.Resampler`. **4c** is the stand-in, `input_devices`, `resolve` and the PortAudio error. **4d** is `MicSource`. Only 4a can stop for the Owner, and 4b needs nothing, so both start early.

### `audio.Resampler` (`src/lmt/audio.py`, 4b)

```python
class Resampler:
    def __init__(self, in_rate: int, channels: int): ...
    def push(self, samples: np.ndarray) -> np.ndarray   # float32 (frames, channels) in; 16 kHz mono float32 out
    def flush(self) -> np.ndarray
```

It holds one `av.AudioResampler(format="flt", layout="mono", rate=16000)`, the settings `decode` uses now, and wraps each push in an `av.AudioFrame` (`fltp` planar for float input) with the right rate and layout and a running `pts`. `decode` resamples through the same settings, so both paths give the same samples. `decode` keeps feeding decoded frames straight to its resampler; only the settings move to one place (`audio.RESAMPLE`), so decode's output, its errors and `tests/test_audio.py`'s existing cases don't change.

### `src/lmt/live/mic.py` (4c, 4d)

```python
@dataclass(frozen=True)
class Device:
    index: int; name: str; channels: int; rate: int; default: bool

def input_devices(backend=None) -> list[Device]
def resolve(spec: str | None, backend=None) -> Device
class MicSource:                  # the same interface as FileSource
    def __init__(self, device: Device, *, limit=None, backend=None, warn=print_warning): ...
```

- **`backend`** is the `sounddevice` module, imported inside these functions, never at the top, so `lmt transcribe` and the rest never load PortAudio (architecture, "Capture"). Tests pass `tests/fake_sounddevice.py` instead. If the import fails (Linux without `libportaudio2`), it is `InputError("--device", "can't load PortAudio (<error>); on Linux, install libportaudio2")` (3).
- **`input_devices`:** `backend.query_devices()`, keeping those with `max_input_channels > 0`. `default` marks `backend.default.device[0]`. `channels` is `min(max_input_channels, 2)`, so a many-channel interface isn't mixed down from inputs that carry nothing. `rate` is the device's `default_samplerate`.
- **`resolve`:** `None` is the default input device. A number is an index. Otherwise an exact name, else a unique case-insensitive substring of one. No input device at all is `InputError("--device", "no input device found")`. An unknown one is `InputError("--device", "no input device '<spec>' (lmt live --list-devices lists them)")`. Both 3.
- **`MicSource`** (4d) opens `backend.InputStream(device=index, samplerate=rate, channels=channels, dtype="float32", callback=…)` when `blocks()` is first iterated, which is when capture starts. The callback only copies `indata` into a `queue.SimpleQueue`, which has no bound, so a slow stage never makes it drop audio. A status flag (input overflow) is counted, and `-v` reports the count. `blocks()` takes from the queue, resamples through `audio.Resampler(rate, channels)`, and re-blocks into exact 1,600-sample blocks. At the stop it closes the stream, flushes the resampler, and hands over what's left. `name` is the device's name, `position` and `reason` work as for `FileSource`, and so do `limit` and `stop()`.
- **The silent device** (4d, G2-5 (iii)): the device's own samples, before resampling, are checked for their first 3 s (`3 × rate` frames). If every one is exactly 0.0, `warn` writes once: `lmt: warning: <device name>: no sound for 3 s; the microphone may be blocked (System Settings, Privacy & Security, Microphone)` (`public-api.md`). Capture goes on. Any non-zero sample in the first 3 s means no warning, and nothing is checked after them. `FileSource` has no such check.

### `tests/fake_sounddevice.py` (4c)

The whole stand-in lands with 4c, its stream included, so 4d, 3b3 and 3b4 only use it. A stand-in for the module: `query_devices()`, `default.device`, and an `InputStream` with the same constructor and `start`, `stop`, `close`, used as a context manager. Its stream calls the callback from its own thread with an array it was given, in blocks of a size it was given, as `(indata, frames, time, status)`. It records whether it was opened, so G2-7's "no audio captured" can be checked. Constructed with a list of devices, possibly none.

### Tests

- **`tests/test_portaudio.py`** (4a, tagged `G2-5`): `import sounddevice` succeeds and loads PortAudio. Under `CI` it must, on both platforms (on Linux through `libportaudio2`, on macOS through the bundled library). Elsewhere, if PortAudio can't load (a Linux machine without it), it is skipped, saying so. With the licence check (`check_licences.py`) passing in the `test` job on both platforms' installs, that is 4a's test. Both run in the PR, since `test` is tier 1.
- **`tests/test_audio.py`** (4b) keeps every case, and gains: `Resampler(48000, 2)` fed a 48 kHz stereo signal in 512-frame and in 1,000-frame pushes, then `flush`, gives the same length as one push of it all, and samples within 1 × 10⁻⁴ of it; `Resampler(16000, 1)` on 16 kHz mono gives back its input within 1 × 10⁻⁶; an empty push gives an empty array.
- **`tests/test_live_mic.py`** (4c, tagged `G2-5`): (ii) and `resolve`'s cases below, and the PortAudio error, with an import hook making `sounddevice` fail: exit 3 and the documented message.
- **`tests/test_live_mic_source.py`** (4d, tagged `G2-5`): (i), (iii), the slow consumer, and `MicSource`'s `limit`, `stop()`, `position` and `reason`, as for `FileSource`.

The cases:

- **(i) Resampling:** the test makes `X`: `clip.wav` resampled to 48 kHz with PyAV, duplicated to two channels, and quantized to 16 bits. It writes `X` as a 48 kHz stereo 16-bit WAV. The expected samples are `audio.decode(<that WAV>)`. The stand-in delivers `X / 32768` as float32 in 512-frame blocks, and again in 1,000-frame blocks. Each time, the concatenated blocks `MicSource` hands over have the expected length, and no sample differs by more than 1 × 10⁻⁴.
- **(ii) No device:** with the stand-in holding no input devices (only an output device), `resolve(None)` raises exit 3 with the message above, and `input_devices()` is empty. **For real:** a test calls `input_devices()` with the real `sounddevice`. In CI (`CI=true`) it must return no devices. Elsewhere, such as a Developer's Mac, which has a microphone, it is skipped, saying so. If the runner turns out to list an input device, the Developer reports it to the Architect rather than changing the test. 3b4 adds the same case through `lmt live` and `lmt live --list-devices`.
- **(iii) Silence:** a device that gives exact zeros for 3 s and then speech gets one warning, in the documented form, and capture continues to the stop. One with a single non-zero sample at 2.9 s gets none. One silent throughout gets one warning, and the session ends normally.
- `resolve` by index, exact name, unique substring, and an ambiguous substring (3). A slow consumer: the callback never blocks, and every frame arrives.

### `product.yml` (4a)

The `test` job gains `sudo apt-get install -y libportaudio2` before `uv sync`, on its Linux runner only, so (ii) runs for real on the runner (spec, G2-5). 3b4's `lmt live` cases then run there too.

**Tests of the items:** 4a, the inventory posted on the item, the licence check passing on both platforms and `tests/test_portaudio.py`; 4b, `tests/test_audio.py`; 4c, `tests/test_live_mic.py`, its real case on the runner; 4d, `tests/test_live_mic_source.py`; all in the `test` job.

## 5. `lmt eval --set live` and `results/live.json`

**Split.** Four items, each on its own test file, in sequence through `src/lmt/eval/live.py`:
- **5a**, the definitions: `RefWord`, `key`, `match_words`, `delays`, `percentile`, `RunLog` (the type) and `read_events`, with the fixture logs and the hand-computed figures. 1e, 3a2 and 3a4 use it, so it goes first.
- **5b**, the runs: `run_once` and `run_live`, with `tests/fake_live.py`. It needs 1d, for `models.download_defaults`.
- **5c**, the figure: `figure` and the live timing fields in `report.py`, with three fixture transcripts.
- **5d**, the command: AMI-ci's reference with its word times (`datasets.live_reference`), `cli_eval_live`, the branch in `eval/cli.py`, and `"live"` in `cli.py`'s `--set` choices.

None of them needs a model or `lmt live`: 5b runs a fake, and 5d replaces the runs with the fixture logs. All four are tier 3 (`src/lmt/eval/`), and every test runs in the `test` job, so each PR's own CI runs it.

### `src/lmt/eval/datasets.py` (5d)

AMI's word times are already there: `ami_words(files)` gives `(start, end, text)` for every `<w>` (punctuation skipped, a missing `endtime` taking the start), sorted by start, and `_ami` crops them with `crop_references` (a word's midpoint before the crop) before joining their texts into `ref_text`. 5d adds one function, and changes no recipe:

```python
def live_reference(name: str = SAMPLE_MEETING) -> tuple[Item, list[tuple[float, float, str]]]
```

It loads the manifests, fetches that dataset's own sources alone (`_source_ids`, then `fetch_source`), so `--set live` downloads no LibriSpeech, and returns the item exactly as `fetch("ci")` gives it for AMI-ci, with the word triples its `ref_text` is made from, in the same order and crop. `_ami` and `live_reference` share one helper for the meeting's cropped words and turns, so the two can't differ.

### `src/lmt/eval/live.py`

```python
class RefWord(NamedTuple): start: float; end: float; text: str     # 5a; datasets' triples are RefWord(*w)
def key(text) -> str                                  # 5a: casefold; drop Unicode punctuation (category P); strip
def match_words(ref: Sequence[RefWord], hyp: Sequence[tuple[Word, float]]) -> list[tuple[RefWord, float]]   # 5a
def delays(matches) -> list[float]                    # 5a: time − ref.end, per matched word
def percentile(values, q) -> float                    # 5a: nearest rank, the ⌈q·n⌉-th smallest
@dataclass(frozen=True)
class RunLog: lines: list[tuple[float, dict]]; wall_seconds: float; transcript: dict   # 5a
def read_events(lines) -> tuple[list[tuple[Word, float]], float]   # 5a: committed words with arrival; behind_seconds
def run_once(command: list[str], out_dir: Path, stem: str) -> RunLog                 # 5b
def run_live(wav: Path, work_dir: Path, *, runs=3, command_prefix=None) -> list[RunLog]   # 5b
def figure(item, ref_words, logs) -> dict             # 5c
def cli_eval_live(args) -> int                        # 5d
```

`jiwer` is imported inside `match_words`, as `score` imports it, so `lmt.eval.live` imports without the `eval` extra.

- **Matched words** (spec, G2 "Terms"): both sides go through `key`, and words whose key is empty are dropped. Then `jiwer.process_words(" ".join(ref_keys), " ".join(hyp_keys))`, and every `equal` chunk of its alignment pairs a reference word with a committed word. Each committed word carries a time: its event's `t` in lockstep (the stream delay, 1e and 3a4), or its event's arrival (Q10's delay). This is the one definition, for CI and the Mac. A reference word or committed word appears in at most one pair, and the pairs come in reference order.
- **`run_once`** (5b) starts `command` with `stdout=PIPE` and stderr to `out_dir/.lmt-live-stderr.txt`. It reads lines with `readline()` and stamps each with `time.monotonic()` as it returns. Arrivals are counted from the `start` event's arrival (spec, G2 "Terms"). `wall_seconds` runs from process start to exit. A non-zero exit raises `InputError("lmt live", "exited <code>: <last stderr line>")` (exit 3). `transcript` is `transcript.to_dict(transcript.load(out_dir / f"{stem}.json"))`, so a run whose JSON fails the schema fails here.
- **`read_events`** (5a) checks that the stream starts with `start`, ends with `stop`, and that `t` never falls; any of these failing is `InputError("lmt live", …)`. It returns each committed word with its event's arrival, and `behind_seconds` = the `stop` event's arrival minus its `t` (3a2 writes `stop` once the pipeline has finished).
- **The command** (5b) for each of three runs: `command_prefix + ["live", "--from-file", <AMI-ci's WAV>, "--jsonl", "--offline", "-f", "json", "-n", f"run{i}", "-o", <work_dir>, "--overwrite"]`, `i` from 1. `command_prefix` defaults to `[sys.executable, "-m", "lmt"]`, so stage 2's sweep can pass `[sys.executable, "-m", "lmt.live.tuning", "--set", …, "--"]`. Before the runs, `run_live` calls `models.ensure(models.download_defaults(models.load_manifest()), offline=False)`, so no run downloads. 1d's `download_defaults` includes the live default (§1), so 5b needs 1d and never names `default_live_asr`. The runs go one after another, with no other evaluation running (G2-6).
- **`figure`** (5c) pools the three runs, in `public-api.md`'s key order. Its first eight keys are G1's figure for the three runs as three items: `score._figure("AMI-ci", "product-live", [item] * 3, hyps)`, where each run's hypothesis is `hypothesis_from_transcript(log.transcript)` with that run's `wall_seconds`. So `dataset`, `system`, `wer`, `der`, `audio_seconds` (3 × the clip's duration), `wall_seconds` (the sum), `rtf` and `peak_rss_bytes` (`null`, since no run reports one) are scored and rounded exactly as G1's are. Then `p50_delay_seconds`, `p95_delay_seconds` and `max_delay_seconds` over every matched word of every run, `matched_words`, and `runs`: each run's `p95_delay_seconds` and `behind_seconds`, in run order. Delays and seconds are rounded to 3 decimal places.
- **`report.py`** (5c): `TIMING_FIELDS` gains `p50_delay_seconds`, `p95_delay_seconds` and `max_delay_seconds`, and `strip_timing` also removes `p95_delay_seconds` and `behind_seconds` inside each `runs` entry, keeping the entries (`public-api.md`, "Timing fields"). A figure without `runs` (`ci.json`, `full.json`) strips as before.
- **`cli_eval_live`** (5d): `live_reference()`, then `run_live(item.audio, <a temporary directory under out_dir, removed after>)`, then `figure`, then `report.write(out_dir / "live.json", report.build("live", [figure], models, determinism=None, out_dir=out_dir))`, where `models` is the first run's transcript's. It prints the file's path, as `--set ci` does.
- **`eval/cli.py`** (5d): `--set live` calls `live.cli_eval_live(args)`. **`cli.py`** (5d): `eval`'s `--set` choices become `("ci", "full", "live")`. Its help and `validate` need no other change (`--update-readme` stays `full`'s alone).

### Fixtures (`tests/fixtures/eval/live/`) and the hand-computed figures

`ref_words.json` (5a), six reference words: `okay` 0.50–0.80, `so` 0.90–1.00, `let's` 1.10–1.40, `start` 1.40–1.90, `the` 2.50–2.60, `meeting` 2.60–3.10. Three event logs (5a), `run1.jsonl` to `run3.jsonl`, each line `{"arrival": <s>, "event": {…}}`, with a `start` at arrival 0.000 and a 4.0 s clip. Every event carries every field of `public-api.md`'s live events 1.0 table, so 3a2's test validates them against the events schema. A `words` event's `t` is its arrival capped at 4.0, so `t` never falls; its `segment` is 1, `speaker` `S1`, `label` `Speaker 1`, and each word's `start` and `end` its reference word's (or, for a word that matches none, the previous word's end and 0.1 s later), with `probability` 0.9.

| Run | `words` events (arrival: texts) | `stop` arrival (`t` 4.0) | Matched delays | Run p95 | Behind |
| --- | --- | --- | --- | --- | --- |
| 1 | 2.300: `Okay,` `so`; 3.200: `let's` `start.`; 4.600: `a` `meeting` | 5.100 | 1.5, 1.3, 1.8, 1.3, 1.5 (`a` against `the` doesn't match) | 1.8 | 1.1 |
| 2 | 1.900: `okay` `so`; 2.900: `let's` `start`; 4.100: `the` `meeting` | 4.300 | 1.1, 0.9, 1.5, 1.0, 1.5, 1.0 | 1.5 | 0.3 |
| 3 | 2.000: `okay`; 2.600: `so` `let's` `start`; 3.900: `the` `meeting` `meeting` | 4.000 | 1.2, 1.6, 1.2, 0.7, 1.3, 0.8 (one `meeting` is an insertion; both arrive at 3.900) | 1.6 | 0.0 |

Pooled over the 17 matched words, sorted: 0.7, 0.8, 0.9, 1.0, 1.0, 1.1, 1.2, 1.2, 1.3, 1.3, 1.3, 1.5, 1.5, 1.5, 1.5, 1.6, 1.8. **p50** is the 9th (⌈8.5⌉) = 1.3. **p95** is the 17th (⌈16.15⌉) = 1.8. **max** 1.8. `matched_words` 17. Linear interpolation would give 1.64 for p95, so the test proves the nearest-rank method. `key` makes `Okay,` match `okay`, `start.` match `start`, and `let's` match `let's` (both `lets`). The test compares each figure with these, after rounding to 3 decimal places as `figure` rounds (4.100 − 2.60 is 1.4999… in floating point), and must never be adjusted to whatever the code prints. If the locked `jiwer` aligns run 3's `meeting`s otherwise, the delay is the same, since both arrive together.

**The fixture transcripts** (5c), `run1.json` to `run3.json`: transcript JSON 1.1, each valid against the schema, with `source` `{"file": "run<i>", "duration": 4.0, "live": true}`, one speaker `S1`, and one segment from 0.5 to 3.1 holding that run's committed words, in order, its `text` their texts joined by spaces. The test's item is `Item("AMI-ci", "ES2004a", <any path>, 4.0, ref_text="okay so let's start the meeting", ref_turns=(Turn(0.5, 3.1, "A"),))`, and each `RunLog`'s `wall_seconds` is 5.2, 4.4 and 4.1. So `audio_seconds` is 12.0, `wall_seconds` 13.7 and `rtf` 1.142 (13.7 / 12, rounded to 3 places); `der` is 0.0, since each run's one turn is the reference turn exactly; and `peak_rss_bytes` is `null`. `wer` is `round(score.wer(<the three (ref_text, hypothesis text) pairs>), 6)`, computed in the test with G1's own `score.wer`, whose tests are G1's; it is above 0, since run 1 says `a` for `the` and run 3 repeats `meeting`.

### Tests (no model, the `test` job)

- **`tests/test_eval_live.py`** (5a, tagged `G2-6c`, whose delays these functions compute): `key` on `Okay,`, `start.`, `let's` and a word of punctuation alone (empty); `match_words`, `delays` and `percentile` on the fixtures, against the table, run by run and pooled; `percentile` on 1 value, and on 20 values at 0.95 (the 19th); `read_events` on each fixture log gives its committed words with their arrivals, and `behind_seconds` 1.1, 0.3 and 0.0; it rejects a stream not starting with `start`, not ending with `stop`, or with `t` falling (exit 3).
5b's, 5c's and 5d's tests carry no criterion tag: G2-6 runs on the Mac, and its check is the Owner's `results/live.json` (spec, G2 "Fresh evidence"). They are its mechanics.

- **`tests/test_eval_live_run.py`** (5b): **`run_once`** on `tests/fake_live.py`, a script run as `[sys.executable, <its path>, *args]` that prints a scripted `start`, sleeps 0.3 s, prints a `words` event, sleeps 0.2 s, prints `stop`, writes a valid transcript to `-o`/`-n`'s `<stem>.json`, and exits. The arrivals are 0.3 and 0.5 s, each within ±0.1 s, and `transcript` is the JSON it wrote. A script that exits 1 raises exit 3 with its last stderr line. **`run_live`** with `command_prefix=[sys.executable, <fake_live.py>]` and `models.ensure` replaced by a fake that records its argument: the argument equals `models.download_defaults(models.load_manifest())`, the fake was called before the first run, and the three runs' argv are the documented command with `run1`, `run2` and `run3`, in order. `fake_live.py` appends its argv, as one JSON line, to the file `LMT_FAKE_LIVE_ARGV` names, which the test sets.
- **`tests/test_eval_live_figure.py`** (5c): `figure` on the fixture logs and transcripts gives exactly the figures above, in `public-api.md`'s key order (`dataset`, `system`, `wer`, `der`, `audio_seconds`, `wall_seconds`, `rtf`, `peak_rss_bytes`, `p50_delay_seconds`, `p95_delay_seconds`, `max_delay_seconds`, `matched_words`, `runs`). `report.strip_timing` removes the three delay fields and each run's `p95_delay_seconds` and `behind_seconds`, keeping three `runs` entries; `report.same_accuracy` holds between two results that differ only in those, and not between two whose `wer` differs. `tests/test_report.py` passes unchanged.
- **`tests/test_eval_live_cli.py`** (5d): **`lmt eval --set live --out <tmp>`** through `cli.main`, with `live_reference` replaced by the fixture item and words, `run_live` by one returning the three fixture logs, and `models.ensure` untouched (it isn't reached): exit 0, the path printed, and `<tmp>/live.json` has `set` `"live"`, `schema_version` `"1.0"`, `determinism` `null`, the first transcript's `models`, and one figure equal to 5c's. `lmt eval --help` lists `live` among `--set`'s choices, and `--update-readme` with `--set live` is exit 2. **`live_reference`**, on the dataset fixtures `tests/test_datasets.py` uses for `_ami`: the item equals the one `fetch` gives for that dataset; its words' texts, joined, are its `ref_text`; every word's midpoint is before the crop; and `fetch_source` is called for that dataset's sources only.

**Tests of the items:** each item's file above, in the `test` job, with every earlier item's file still passing.

## CI cost

**The 29 S items** are 24 at tier 3 and 5 at tier 2 (the model tests, but 1e, which changes `asr.py`). A pull request runs tier 1 at most, about 12 minutes (architecture, "CI": 10, plus 2 for G3-7's install), so their PRs come to about 29 × 4 × 12 ≈ 1,400 minutes at the architecture's 4 runs a PR. Each merge then runs its own tier on `main`: about 24 × 39 + 5 × 26 ≈ 1,050 minutes before G2's model tests land, more as they do (below). That is about 2,450 minutes for G2's stage 1, against about 1,100 for the seven items when a PR ran its full tier. More, smaller PRs cost more runs, but each is cheaper, and the model runs happen once per merge rather than per PR push. With G1's and G3's runs in the same month, the 3,000-minute signal (`system/sizing.md`, "CI") can be reached. That is a signal, not a cap, on a public repository's free runners; #91 is where the builder tracks it.

**G2's model tests,** once all have landed, add to `test-models`:

| Run | Estimate |
| --- | --- |
| `clip.wav`, lockstep, ASR only (G2-2) | about 60 updates of the live model at 3–4 s each on the runner: 3–4 min |
| `two_speakers.wav`, lockstep, the shared run (G2-1, G2-3, G2-6c, G2-8, G2-4's outputs) | 3–4 min |
| `two_speakers.wav`, diarization only (2c) | under 1 min |
| G2-4's real-time runs (the stops together, then the whole file) | about 2 min of audio, plus model loading: 3 min |

That is about 10–12 minutes, not the architecture's 5, mostly because each update is a full encoder pass of `distil-large-v3` (architecture, "Streaming ASR"). Tier 3 would then take about 45–50 minutes a run. The first runs measure it. Per the architecture's rule, the Architect re-sizes the tiers there if `test-models` takes more than 1.5 times its estimate, and the architecture's figures for G2 are corrected in the same change. Stage 2 may also pin a smaller live model, which would cut this by about two thirds. The design already keeps CI's cost down: the two-speaker clip runs once in lockstep, shared by five checks, and the real-time stop cases run side by side.

## What stage 2's Mac investigation needs from these items

Stage 2 measures the candidate live models, the update interval and the diarization latency on the Mac against Q10, and pins the defaults (spec, G2 "Stages"; architecture, "The live model").

| It needs | From |
| --- | --- |
| U, L and the diarization thresholds as settings, which can be changed without editing code | 1b and 2a (`AsrConfig`, `DiarConfig`), and `python -m lmt.live.tuning` (3c3) |
| Q10's measurement with any settings and any model | 5b's `run_live(command_prefix=…)` with the tuning entry point; `--model` (3b1, 3b3) |
| Each update's and step's compute time, and how far behind it ended | `-v` (3c1, 3c2); `behind_seconds` in `results/live.json` (5c) |
| The diarization thresholds tuned without re-running the models | 2a's `Clusterer` and `replay`, on 2b's `record` |
| G2-3 and G2-6c checked for each candidate setting before it's pinned | 3a4's and 3b5's tests, run under `python -m lmt.live.tuning` settings |

**Two things it needs that stage 1 doesn't build,** since no stage-1 check uses them:
- **The candidate models in the manifest:** `distil-small.en` and `base.en`, pinned by revision and SHA-256, as G1's investigation adds its candidates. With `default_live_asr`, stage 2's choice is a one-line change.
- **AMI dev meetings** in the dataset manifests, for tuning the diarization thresholds, never on test meetings (architecture). Recommended: the first 600 s of one meeting from each of the dev split's ES, IS and TS series (ES2011a, IS1008a and TS3004a, once checked against the BUT setup's dev list), with their RTTMs. That is a small item, before the investigation.

**After the investigation,** this file records the tuned thresholds and the pinned U and L, and `models.toml` the live default.

## Readings of the spec and public API

These are interpretations within the approved spec and design (the Architect's to make). The Reviewer should check each one. If one is wrong, it goes to the Owner as a change to the spec or the public API.

1. **The join looks only back** for alignment's "nearest turn within 1 s" (3a1). Looking ahead would delay such words by up to 1 s, against G2-6c's budget. It stays words-first, as P12 left alignment's rules for it (3a).
2. **`stop` is the last event,** written once the captured audio is finished, just before the final formats (`public-api.md`: "Capture stops. The final formats follow."). 5a's `behind_seconds` is read from it.
3. **`start`'s `source` has no `duration`,** since nothing has been captured yet. Otherwise it is the transcript's `source`.
4. **`lmt live` never exits 4.** A silent session writes a transcript with no segments and exits 0, as G2-5 (iii) requires for a silent device, and `--from-file` follows the same path.
5. **A live transcript's `models.diarization`** is `speaker-diarization-3.1`'s manifest entry, as for `lmt transcribe`; `source.live` marks the live method. This adds no field to the schema.
6. **G2-1's "every word"** is every matched offline word, since an unmatched one can't be found in the live stream.
7. **"While it saves"** is everything from the first stop to the exit. A second Ctrl-C that lands during the final renames, a few milliseconds long, lets them finish with exit 0, so a set of final formats is never left half renamed.
8. **The live default model** is a manifest key, `default_live_asr`, as the architecture's "separate live default" requires.
9. **G2-1, G2-3 and G2-6c run on the shared subprocess run** (3b5), not in process, though G2-1's "How it's checked" says "a test runs the live pipeline in process". The subprocess runs lockstep in process through `tests/live_lockstep.py`, so each event's `t` is still the stream position, and G2-8 needs that run anyway. 3a4 checks them in process until 3b5 moves them, so CI runs the two-speaker clip in lockstep once.
10. **A second Ctrl-C is one the handler sees as a second** (#567). Two SIGINTs that reach the process before its main thread runs the handler for the first are one stop to it: CPython calls the handler once for them, and the kernel may already have merged them. Such a session saves and exits 0. That isn't "a second Ctrl-C while it's saving" (`public-api.md`), since saving hadn't started, and no product change can recover a signal the kernel merged. A person's second press comes long after the first is handled, unless the machine is starved for seconds.
