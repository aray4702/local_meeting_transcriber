# Internal design: G1-2, the reference clip's encodings and their test

| Date (PT) | By | Change |
| --- | --- | --- |
| 2026-10-29 | architect, #291 | First version: the five encodings' ffmpeg recipe in the dataset tool, the committed files, and G1-2's test, as one Developer item |
| 2026-10-29 | architect, #295 | MP4/MOV: the still track's length is fixed at its source (`d=57`) and `-shortest` is dropped, because `-shortest` gave different bytes on every run with ffmpeg 8.0 (#296) |
| 2026-10-29 | architect, #299 | MP4/MOV: `-max_interleave_delta 0` added, because with `d=57` the files' bytes and sizes still varied from run to run (#296), as a varying packet interleave makes them; MP4/MOV must reproduce on five checks, not three |

This is what a Developer needs to build **G1-2** in `spec/acceptance.md` in one run, unchanged: the reference clip as FLAC, MP3, M4A, MP4 and MOV each transcribes with a WER within 1.0 percentage point of the WAV's WER, by the same test run once per format, in CI. The encodings are the spec's Terms: FLAC; MP3 at 128 kbit/s; M4A (AAC-LC) at 128 kbit/s; MP4 and MOV with an AAC track and a still video track. It builds on `g1-slice.md`: S1's dataset tool and `sets.toml`, S2's `audio.decode` (which reads all five unchanged, as the architecture's "Decode" says) and S6's product run in tests. Where this file and those disagree, they win, and this file is the one to fix. The Reviewer reviews this file. The Architect changes it.

**What doesn't change.** G1-1's clip, its reference, the scoring (#109's `wer`), decode and the product's defaults. The encodings are fixed below before any WER is measured on them. If a format misses the bound, the product is what gets fixed, never the recipe, the clip or the bound.

## The item

| Item | What | Needs | Files it creates or changes | Tier |
| --- | --- | --- | --- | --- |
| **E1** | The five encodings, their recipe and G1-2's test | S1, S2, S6 (merged) | `src/lmt/eval/datasets.py`, `src/lmt/eval/manifests/sets.toml`, `tests/fixtures/clip.{flac,mp3,m4a,mp4,mov}`, `tests/test_datasets.py`, `tests/test_manifests.py`, `tests/test_encodings.py` (new), `tests/test_g1_2.py` (new), `tests/criteria.toml`, `.github/scripts/test_criteria.py` | 3 (`src/lmt/eval/`) |

## The recipe

ffmpeg's command-line tool makes the files. Agents can't run ffmpeg directly (`toolchain.toml`), so the recipe lives in the dataset tool, which a Developer run may run: `uv run --frozen python -m lmt.eval.datasets encode-fixture clip [--write]`. The arguments are a constant in `datasets.py`, never read from the manifest, so the tool can only run these five commands, on the fixture's WAV, writing beside it.

Each command is `ffmpeg` followed by exactly these arguments, with `<wav>` the absolute path of `tests/fixtures/clip.wav` and `<out>` a temporary file in the same directory:

| Format | Arguments |
| --- | --- |
| `flac` | `-nostdin -v error -y -i <wav> -map 0:a:0 -map_metadata -1 -fflags +bitexact -flags:a +bitexact -threads 1 -c:a flac -compression_level 8 -sample_fmt s16 -ar 16000 -ac 1 -f flac <out>` |
| `mp3` | `-nostdin -v error -y -i <wav> -map 0:a:0 -map_metadata -1 -fflags +bitexact -flags:a +bitexact -threads 1 -c:a libmp3lame -b:a 128k -ar 44100 -ac 1 -f mp3 <out>` |
| `m4a` | `-nostdin -v error -y -i <wav> -map 0:a:0 -map_metadata -1 -fflags +bitexact -flags:a +bitexact -threads 1 -c:a aac -profile:a aac_low -b:a 128k -ar 48000 -ac 1 -f ipod <out>` |
| `mp4` | `-nostdin -v error -y -i <wav> -f lavfi -i color=c=black:s=320x240:r=1:d=57 -map 0:a:0 -map 1:v:0 -map_metadata -1 -fflags +bitexact -flags:a +bitexact -flags:v +bitexact -threads 1 -c:a aac -profile:a aac_low -b:a 128k -ar 48000 -ac 1 -c:v mpeg4 -pix_fmt yuv420p -max_interleave_delta 0 -f mp4 <out>` |
| `mov` | the `mp4` arguments with `-f mov` in place of `-f mp4` |

Why these choices:

- **The rates.** FLAC is lossless, so it keeps the clip's 16 kHz. ffmpeg's AAC encoder caps a channel at 6,144 bits per 1,024 samples, which is 96 kbit/s at 16 kHz. So 128 kbit/s, as the spec requires, needs a higher rate: 48 kHz for AAC, and 44.1 kHz, MP3's usual rate, for MP3. That also puts decode's resampler on the path, as most users' files do. Mono stays mono.
- **The encoders.** `libmp3lame` with `-b:a` is constant bit rate. `aac` is ffmpeg's own encoder, named explicitly so that macOS's `aac_at` is never picked, and `-profile:a aac_low` is AAC-LC. The still video track is a black 320×240 frame at 1 frame/s, made by `lavfi`'s `color` source, in ffmpeg's own `mpeg4` encoder, which every ffmpeg build has. The source's `d=57` makes exactly 57 frames, so the track covers the clip's 56.565 s (905,040 samples at 16 kHz) and stops by itself; the file's length is the video's 57 s, and the audio stream keeps the clip's length.
- **Reproducible bytes for one ffmpeg version.** `-map_metadata -1`, the `bitexact` flags and `-threads 1` keep version strings, tags and thread timing out of the files. Every input is finite, so no option cuts a stream short. `-shortest` did, and with ffmpeg 8.0 its cut point varied from run to run, as did the files' bytes and sizes (#296); it is not used. **The interleave** is the other source of variation in a two-stream file. ffmpeg 8 runs each input and encoder in its own thread, which `-threads 1` doesn't control, so the order packets reach the muxer varies. By default the muxer waits for every stream only until the buffered packets span 10 s, then writes what it has. The 57 one-second video packets come long before the audio, so how many it writes early depends on timing, and that moves the chunk boundaries and so the chunk tables' sizes. With `d=57` the sizes still changed between runs, by 4 bytes in MOV and 56 in MP4, which fits this (#296). `-max_interleave_delta 0` makes the muxer buffer until it has a packet from each stream, so it writes them in timestamp order alone, whatever the thread timing. M4A has one stream, so it needs none of this. Bytes still vary between ffmpeg versions, so the files are committed and their hashes recorded with the version that made them. Tests use the committed files and never re-encode them.

### `sets.toml`

The clip's `[[fixture]]` gains two keys:

```toml
ffmpeg = "<version>"     # the token after "ffmpeg version " on the first line of `ffmpeg -version`
encodings = [            # each file is tests/fixtures/clip.<format>, made by the recipe in design/internal/g1-formats.md
  {format = "flac", sha256 = "<64 hex>"},
  {format = "mp3",  sha256 = "<64 hex>"},
  {format = "m4a",  sha256 = "<64 hex>"},
  {format = "mp4",  sha256 = "<64 hex>"},
  {format = "mov",  sha256 = "<64 hex>"},
]
```

`load_manifests` reads them into `Fixture.ffmpeg: str | None` and `Fixture.encodings: tuple[Encoding(format, sha256), ...]`, default empty. It raises `ValueError` if one key is given without the other, if a format isn't one of the five, if a format repeats, or if a hash isn't 64 lower-case hex. A file's path is never in the manifest: it is the fixture's `path` with the format as its suffix, so the tool can't be pointed elsewhere.

### `src/lmt/eval/datasets.py`

```python
ENCODINGS: dict[str, tuple[str, ...]]     # the table above, <wav> and <out> as placeholders
def ffmpeg_version() -> str               # runs `ffmpeg -version`; InputError("ffmpeg", "not found on PATH") if absent
def encode(fixture: Fixture, fmt: str, out: Path) -> None   # one command, subprocess.run(check=False, capture_output)
```

**`encode-fixture <name> [--write]`** checks that the fixture has `encodings`, then encodes each of the five, in the order above, to a temporary file beside the WAV (`tempfile.mkstemp(dir=..., suffix=f".{fmt}.tmp")`, deleted on any failure), and prints `<path> <sha256>` for each and then `ffmpeg <version>`. A non-zero ffmpeg exit raises `InputError(<the encoding's path>, "ffmpeg failed: <its stderr's last line>")`. With `--write`, it renames each file into place first. Then it compares: if the local version differs from `ffmpeg` in `sets.toml`, it exits 3 with `lmt: error: ffmpeg: version <local> here, sets.toml records <recorded>; the hashes can't be compared`. Otherwise it exits 0 if every hash matches, and 3 naming the first file that doesn't. Without `--write`, nothing in the repository changes.

**Making the files** (once, in E1): add the two keys with 64 zeros for each hash and the local version, run `encode-fixture clip --write`, copy the printed hashes into `sets.toml`, then run `encode-fixture clip` five more times, each of which must exit 0. Five, not three, because MP4 and MOV have failed this before. The PR shows these outputs and `ffmpeg -version`'s first line, through the tool's output.

## Tests

- **`tests/test_datasets.py`**, no ffmpeg: with `subprocess.run` replaced by a fake that records its argv and writes fixed bytes to the last argument, `encode-fixture clip --write` calls `ffmpeg` with exactly the table's arguments for each format, in order (asserted as literal lists, so any change to the recipe fails here); writes `clip.<format>` beside a WAV in a temporary fixture directory; exits 0 when the hashes match and 3 when one doesn't; exits 3 on a version mismatch; leaves no temporary file when the fake fails; and without `--write` writes nothing.
- **`tests/test_manifests.py`:** the clip has all five encodings, each hash 64 hex, and an `ffmpeg` version; the bad cases above raise `ValueError`.
- **`tests/test_encodings.py`**, in the `test` job, no model: each committed file's SHA-256 equals `sets.toml`'s, so a file can't change without its manifest. With PyAV (`av.open`), each has exactly one audio stream, mono: FLAC's codec is `flac`; MP3's is MP3, with a stream bit rate of 128,000; M4A's, MP4's and MOV's are `aac` with profile `LC` and a bit rate within 128 kbit/s ± 10 %, the encoder's own variation; MP4 and MOV each have exactly one video stream, and FLAC, MP3 and M4A none. `lmt.audio.decode` on each gives a length within 1,600 samples (0.1 s) of `clip.wav`'s frame count, which allows for encoder padding.
- **`tests/test_g1_2.py`**, G1-2's test, marked `models` and `criterion("G1-2")`, parametrized over `FORMATS = ("flac", "mp3", "m4a", "mp4", "mov")`, so it is the same test run once per format:
  - The WAV's WER comes from S6's session fixture `clip_run`, the same run G1-1 scores, so it is from the same session.
  - The format's run is the product run: `run_lmt(["transcribe", <the absolute path of tests/fixtures/clip.<format>>], cwd=tmp_path)`, with no option, as `clip_run` makes it (`from conftest import run_lmt`). It exits 0, and `tmp_path / "clip.json"` exists.
  - Both WERs are `wer([(reference, hypothesis_from_transcript(doc).text)])` against `tests/fixtures/clip.txt`, scored as G1-1 scores them. The assertion is `abs(wer_format - wer_wav) <= DELTA_BOUND + 1e-9`, with `DELTA_BOUND = 0.010` and a comment citing `spec/acceptance.md` G1-2 (1.0 percentage point, inclusive). The `1e-9` only absorbs float rounding at an exact tie: both WERs have the same denominator `N`, the reference's word count, so a real miss exceeds the bound by at least `1 / (100 N)`, far above `1e-9` for any `N` below 10⁷.
  - Both WERs and their difference go into the assertion's message, the test's output and `$GITHUB_STEP_SUMMARY`, pass or fail, one line per format, as G1-1's test reports.
- **`tests/criteria.toml`** gains, after `[G1-1]`:

  ```toml
  # G1-2: tests/test_g1_2.py runs the product run on each of the clip's five encodings in test-models and
  # compares each WER with the WAV's from the same session (design/internal/g1-formats.md), which is the
  # whole of its check.
  [G1-2]
  complete = true
  ```

  `.github/scripts/test_criteria.py`'s `RealSpecTest.test_real_registry_loads` lists the complete criteria, so E1 adds `G1-2` to that set, as S6 added `G1-1` (3ba2f1a).

## CI

No new job and no workflow change: `test-models` already runs `pytest -m models`, and the test only decodes, through PyAV, so the runner needs no ffmpeg. It adds five product runs on the 60 s clip, about 1 minute each, so about 5 minutes. That is inside the architecture's estimate for `test-models` ("about 8 runs on the 60-second clips", 22 minutes for tier 2) and its 30-minute timeout. The PR shows the job's time. If the job passes 1.5 times its estimate, the Developer says so on the item, and the Architect re-sizes it, as `architecture.md` "CI" says. The five files add about 4.5 MB to the repository.

**Test of the item:** the tests above in the `test` job; G1-2's five cases passing in the PR's `test-models` job, with each format's WER, the WAV's and the difference in the job's summary; the PR's `criteria-test-models` record giving `G1-2` `passed`, and `criteria.py --ref refs/pull/<n>/merge` giving `pass` for G1-2; and the tool's output, `encode-fixture clip --write` and then `encode-fixture clip` exiting 0 on each of five runs.

## Risks

- **No ffmpeg, or one without `libmp3lame`,** on the Developer's machine. The tool fails with one `lmt: error:` line. The Developer doesn't install it outside the tools agents are allowed: the item is held for the Owner with `needs-decision:owner`, asking for ffmpeg on that machine.
- **A file's bytes still vary between runs.** The Developer reports each run's hashes and sizes on the item and holds it for the Architect with `needs-decision:architect`, without trying other arguments. If MP4/MOV still vary with `-max_interleave_delta 0`, the Architect's next step is to stop requiring the same bytes for those two files: the committed file stays what the tests use, and `encode-fixture` compares each stream's packets instead of the file's hash.
- **A format misses the bound.** That is a product finding, most likely in decode's resampling. The Developer reports the five readings on the item, and the Architect designs the fix in decode. The recipe, the clip and the bound don't change.
