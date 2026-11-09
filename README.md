# Local Meeting Transcriber

## What it is

Local Meeting Transcriber turns a meeting recording into an accurate transcript with timestamps that says who said what, running entirely on your Mac (Apple silicon, macOS 26 or later), on its GPU or Neural Engine, so the audio never leaves it, with its accuracy measured and published. It transcribes WAV, MP3, M4A, FLAC and MP4 or MOV audio into text, subtitles and JSON with a speaker label on every line, lets you give the speakers their names, and shows a transcript with its audio in a page on your own computer. It is built by this repository's development system, which [`blueprint.md`](blueprint.md) describes. Its requirements are in [`project_requirements.md`](project_requirements.md).

## Install

You need a Mac with Apple silicon and macOS 26 or later, and [uv](https://docs.astral.sh/uv/getting-started/installation/), installed by its own installer. Nothing else: uv fetches a suitable Python if you don't have one.

```sh
uv tool install git+https://github.com/aray4702/local_meeting_transcriber@v0.2.0
```

The speaker models are gated on Hugging Face. Once, before the first download: make a free account, accept the conditions on the pages of [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1), [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0) and [pyannote/wespeaker-voxceleb-resnet34-LM](https://huggingface.co/pyannote/wespeaker-voxceleb-resnet34-LM), create a read token, and set it as `HF_TOKEN` for `lmt models download`. After that, nothing needs the network.

## Use

Download the models once, with your Hugging Face token. After that, nothing below needs the network.

```sh
HF_TOKEN=<your token> lmt models download
```

Transcribe a recording. It writes `meeting.txt`, `meeting.srt`, `meeting.vtt` and `meeting.json` in the current directory, each line with a speaker label and timestamps; `-f` picks a subset and `-o` another directory.

```sh
lmt transcribe meeting.m4a
```

Two speech engines are built in. Kyutai STT 1B, the default, runs on the Mac's GPU. Apple's own on-device recognizer runs on the Neural Engine; choose it with `--engine apple`, in `lmt transcribe` and `lmt live` alike. It needs the Xcode Command Line Tools (`xcode-select --install`) to build its small Swift helper, and its English speech model, which macOS installs once:

```sh
lmt models download --engine apple
lmt transcribe meeting.m4a --engine apple
```

List the speakers it found, then give them names. Every format is written again with the names.

```sh
lmt rename meeting.json
lmt rename meeting.json S1="Alice" S2="Bob"
```

Show a transcript and play its audio in a page on this computer: click a line to hear it. Ctrl-C stops it.

```sh
lmt demo meeting.json
```

Or try it on a sample meeting (AMI ES2004a, CC BY 4.0). The first run downloads the meeting and transcribes it once, which takes several minutes; later runs open at once, offline.

```sh
lmt demo --sample
```

Or transcribe live in a page: `lmt app` opens one where you pick the engine, press Start and speak. The text appears as you speak, and each line gets its speaker a moment later. Stop saves the transcript and opens it in the same page.

```sh
lmt app
```

## Build

Prerequisites:

- git;
- Python 3.11 or later;
- [uv](https://docs.astral.sh/uv/), the toolchain's installer, at version 0.13.6, as [`toolchain.toml`](toolchain.toml) pins it.

Get a working copy, install the product with its locked dependencies ([`uv.lock`](uv.lock)), and run it:

```sh
git clone https://github.com/aray4702/local_meeting_transcriber.git
cd local_meeting_transcriber
uv sync --locked
uv run lmt --help
```

## Checks

The gate ([`.github/workflows/gate.yml`](.github/workflows/gate.yml)) is the one required check: a change merges only when it passes. Run its generic checks locally, from the root of the working copy:

```sh
python3 -I system/gate/generic.py --base origin/main
```

The product's CI jobs live in [`.github/workflows/product.yml`](.github/workflows/product.yml), which the gate calls. Among them, the `readme` job checks this file against its criteria in [`spec/acceptance.md`](spec/acceptance.md), and the `test` job runs the product's tests, which you can run with `uv run --frozen pytest`. The `eval-ci` job runs the evaluation on the CI subset twice, with `uv run --frozen lmt eval --set ci`, which downloads and caches the subset and writes `results/ci.json`; it checks that the two runs give identical accuracy figures and that the figures meet the accuracy bounds.

## Results

### Quick benchmark: GPU and Neural Engine

A short run on the CI subset, about 8 minutes of audio: LS-ci, 20 LibriSpeech test-clean utterances (162 s), and AMI-ci, the first 300 s of AMI meeting ES2004a (four speakers). It ran on an Apple M4 (16 GB, macOS 27.0.1) on 2026-11-01, at commit `69d1b9383023`, with lmt 0.2.0, by `lmt eval --set ci` (Kyutai STT 1B, on the GPU) and `lmt eval --set ci --engine apple` (Apple's SpeechTranscriber, on the Neural Engine). Diarization is pyannote's `speaker-diarization-3.1` on the CPU with either engine.

| Set | System | WER, GPU | WER, NPU | DER, GPU | DER, NPU | RTF, GPU | RTF, NPU |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| LS-ci | product | 1.8 % | 0.7 % | — | — | 0.82 | 0.06 |
| LS-ci | the engine alone | 1.8 % | 0.7 % | — | — | 0.79 | 0.04 |
| AMI-ci | product | 20.4 % | 14.8 % | 23.6 % | 32.5 % | 0.86 | 0.65 |
| AMI-ci | the engine alone | 20.4 % | 14.8 % | — | — | 0.72 | 0.01 |
| AMI-ci | pyannote alone | — | — | 18.1 % | 18.1 % | 0.85 | 0.65 |

RTF is wall-clock time over audio duration, on the same basis as the full-set tables below. On the meeting, pyannote takes most of the time with either engine, so the product's RTF is close to pyannote's alone. The product's DER is higher than pyannote's alone because each word takes its speaker from its timestamps, so it depends on the engine's word timings too. The subset is small, so treat these as indicative. The full-set tables below are the published figures.

### Full sets

The tables below are rendered from the results of the full evaluation on a Mac, one file per engine: [`results/full.json`](results/full.json) for Kyutai STT 1B on the GPU, and `results/full-apple.json` for Apple's recognizer on the Neural Engine, once it exists. `lmt eval --set full --update-readme` measures Kyutai and regenerates them; add `--engine apple` for Apple's. `lmt eval --check-readme` checks that they equal what the results files render, and the `readme` job runs that check, so the tables can't drift from their results files.

<!-- results:start -->
**Full sets, Kyutai STT 1B** (`results/full.json`)

No full-set results yet. The Owner's run of `lmt eval --set full` fills this table (G1 stage 3).
<!-- results:end -->

## Licences

The product is licensed under the MIT License ([`LICENSE`](LICENSE)); [`NOTICE`](NOTICE) gives the licence of each model it downloads. The speech recognition model, [`kyutai/stt-1b-en_fr-mlx`](https://huggingface.co/kyutai/stt-1b-en_fr-mlx), by Kyutai, is under CC BY 4.0, with its attribution in [`NOTICE`](NOTICE). It also knows French, which `lmt` neither supports nor evaluates. Apple's recognizer is part of macOS: `lmt` downloads and redistributes nothing of it. The diarization pipeline, [`pyannote/speaker-diarization-3.1`](https://huggingface.co/pyannote/speaker-diarization-3.1), by pyannote (Hervé Bredin and Alexis Plaquet), is under the MIT License. Its segmentation model, [`pyannote/segmentation-3.0`](https://huggingface.co/pyannote/segmentation-3.0), by pyannote (Hervé Bredin and Alexis Plaquet), is under the MIT License. Its speaker embedding model, [`pyannote/wespeaker-voxceleb-resnet34-LM`](https://huggingface.co/pyannote/wespeaker-voxceleb-resnet34-LM), by the WeSpeaker project, packaged for pyannote.audio by pyannote, is under CC BY 4.0, with its attribution in [`NOTICE`](NOTICE).
