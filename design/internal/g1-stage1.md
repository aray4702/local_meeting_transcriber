# Internal design: G1 stage 1 (toolchain, CI and the harness)

| Date (PT) | By | Change |
| --- | --- | --- |
| 2026-10-27 | architect, #104 | First version: phase 1.1's items, #106 to #111, with item 1 and item 5 each split in two |
| 2026-10-27 | architect, #104 | Reviewer's changes on #119: one order the Coordinator can follow, with the `test` job's two edits; the filter's own tier recorded as open (#121); `dirty` excludes the output directory only inside the work tree; the WER fixture's word counts spelled out |
| 2026-10-28 | architect, #82 | `public-api.md` now documents `lmt live` (G2): G1-6's table test skips the sections marked "(G2)", and G2's `lmt live` item adds the subcommand to `cli.py` |
| 2026-10-28 | architect, #82 | Merged `main` (G3, #129) into #125: the table test's skip and the `cli.py` exception also cover G3's `lmt rename` and `lmt demo`, which G3's items add |
| 2026-10-28 | architect, #206 | §1a's `pyproject.toml` gains the wheel's `packages` and ruff's `include`, as #188 built them (the Owner's answer 1 on #188); `.github/scripts/` joins `include` in #222 |
| 2026-10-29 | architect, #123 | §5b's open points for the Developer: the two-speaker clip's rule is `g1-stage2.md`'s (#304); `pin --write-members`; LS full's own source and every-utterance form; AMI full as one dataset with per-meeting lists; the one-hour recording as a `concat` dataset of AMI full |
| 2026-10-31 | builder, #529 | The sample meeting (`ami-ES2004a`) is also served from this repository's pre-release `sample-data-ami`, tried before Edinburgh's mirror, which refused GitHub's macOS runners at times (the Owner: "host it here"). `URL_PREFIXES` gains that one release's download path; the file's size and SHA-256 are unchanged and checked as before |

This is the detail a Developer needs to build each of G1 stage 1's items in one run. It works inside `spec/acceptance.md` G1, `design/architecture.md` and `design/public-api.md`, and the Owner's answers 1a–14a on #81 and #105. Where this file and those disagree, they win, and this file is the one to fix. The Reviewer reviews this file. The Architect changes it.

## Items, files and order

Two items were too big for one run, so each is split. Item 1's dependency lock can stop for the Owner (spec, G1 "Stages"), so it no longer holds up the CLI and the README. Item 5's full sets aren't needed until stages 2 and 3.

| Item | What | Needs | Files it creates or changes |
| --- | --- | --- | --- |
| **1a** (#106) | Package skeleton and CLI, the `test` job, the README's S1 revision | — | `pyproject.toml`, `uv.lock`, `.python-version`, `.gitignore`, `LICENSE`, `NOTICE`, `toolchain.toml` (`[uv]`), `src/lmt/__init__.py`, `__main__.py`, `cli.py`, `errors.py`, the stubs `models.py`, `pipeline.py`, `eval/__init__.py`, `eval/cli.py`, `tests/test_cli.py`, `tests/test_toolchain.py`, `README.md`, `.github/scripts/check_readme.py`, `.github/scripts/test_check_readme.py`, `.github/workflows/product.yml` |
| **1b** (new) | The planned dependencies, locked for both platforms, and the licence check (G1-15) | 1a | `pyproject.toml`, `uv.lock`, `toolchain.toml` (`[licences]`), `.github/scripts/check_licences.py`, `.github/scripts/test_check_licences.py`, `tests/test_imports.py`, `.github/workflows/product.yml` (`test` job) |
| **2** (#107) | The tier filter | 1a | `.github/scripts/tiers.py`, `.github/scripts/test_tiers.py`, `.github/scripts/check_readme.py` (`--no-install`), `.github/scripts/test_check_readme.py`, `.github/workflows/product.yml` (every job) |
| **3** (#108) | Model manifest, download, cache, `lmt models` | 1b, 2 | `src/lmt/models.py` (replaces the stub), `src/lmt/models.toml`, `tests/test_models.py`, `.github/workflows/product.yml` (`test-models` job) |
| **4** (#109) | Harness scoring and the results file | 1b | `src/lmt/eval/score.py`, `src/lmt/eval/report.py`, `src/lmt/eval/normalizer/`, `tests/test_score.py`, `tests/test_report.py`, `tests/fixtures/eval/`, `NOTICE` (one line) |
| **5a** (#110) | Dataset manifests, cache and the CI subset | 4, 2 | `src/lmt/eval/datasets.py`, `src/lmt/eval/manifests/sources.toml`, `src/lmt/eval/manifests/sets.toml`, `tests/test_datasets.py`, `tests/test_manifests.py`, `.github/workflows/product.yml` (`eval-ci` job) |
| **5b** (new) | Full sets, the one-hour recording and the fixture clips' recipes | 5a | `src/lmt/eval/manifests/*.toml` (added entries), `src/lmt/eval/datasets.py` (the concatenation recipe), `tests/test_datasets.py` |
| **6** (#111) | The README results table | 1a, 2 | `src/lmt/eval/readme.py`, `src/lmt/eval/cli.py` (replaces the stub), `results/full.json`, `README.md` (`## Results`), `tests/test_readme_table.py`, `.github/workflows/product.yml` (`readme` job) |

**Order.** The "Needs" column is the order. An item can start once everything it needs has merged:

1. **1a.**
2. **After 1a:** 1b and 2, in parallel.
3. **After 2:** 6. It needs 2 because its `readme` step runs "at tier ≥ 1", a condition item 2 creates. It can run beside 1b.
4. **After 1b:** 4. **After 1b and 2:** 3.
5. **After 2 and 4:** 5a. **After 5a:** 5b.

**Parallel-safe,** by the files in the table. Items that may run at the same time share only `product.yml`, never the same lines of it:
- **1b and 2** both edit the `test` job. Item 2 adds `needs: changes` and its `if:` to the job's header, under `test:`. Item 1b inserts its steps after `uv sync --locked --all-extras`. The two edits are separated by unchanged lines (`runs-on`, `timeout-minutes`, `steps:`, the checkout and setup-uv steps), so git merges them cleanly. If the second PR does conflict, its Developer updates the branch from `main` and keeps both edits.
- **From item 2 on,** each job has its own block (below). Items 3, 5a and 6 each change only their own job's block (`test-models`, `eval-ci`, `readme`), so they merge without conflicts. Item 4 doesn't touch `product.yml`.
- **Other shared files:** none between items that can run at the same time.

Item 6 needs nothing from item 4: it reads the results file's documented format, not item 4's code. So #111 can drop its block on #109. Item 5a imports item 4's types, so it stays after item 4.

**Every item's local checks:** `uv run --frozen ruff check`, `uv run --frozen pytest`, and `python3 -I system/gate/generic.py --base origin/main`.

## 1a. Package skeleton and CLI (#106)

### `pyproject.toml`

```toml
[project]
name = "local-meeting-transcriber"
version = "0.1.0"
description = "Offline, speaker-labelled meeting transcription that runs entirely on your Mac."
readme = "README.md"
license = "MIT"
license-files = ["LICENSE", "NOTICE"]
requires-python = ">=3.11"
dependencies = []                      # 1b adds the planned ones

[project.scripts]
lmt = "lmt.cli:run"

[dependency-groups]
dev = ["pytest", "ruff"]               # 1b adds the eval extra's packages here too

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/lmt"]                 # the import package's name isn't the distribution's

[tool.uv]
environments = [
  "sys_platform == 'darwin' and platform_machine == 'arm64'",
  "sys_platform == 'linux' and platform_machine == 'x86_64'",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-m 'not models and not data'"
markers = [
  "models: needs the default models in LMT_CACHE_DIR (the test-models job)",
  "data: needs the CI subset in LMT_DATA_DIR (the eval-ci job)",
]

[tool.ruff]
target-version = "py311"
line-length = 110
include = ["src/**/*.py", "tests/**/*.py"]     # the product's code; system/ isn't the product's
extend-exclude = ["src/lmt/eval/normalizer"]   # vendored, kept as upstream wrote it
```

- **Wheel packages:** hatchling looks for a package named after the distribution (`local_meeting_transcriber`), so without `packages` it finds none and `uv sync` fails (the Owner's answer 1 on #188).
- **Ruff's scope:** `include` keeps `ruff check` to the product's Python; no rule is turned off (the Owner's answer 1 on #188). `.github/scripts/**/*.py` joins it in #222: the product's CI runs those scripts, so they get the same lint. They have ruff findings today, which #222 fixes first. `system/` stays out.
- **Versions:** `uv lock` picks them, with lower bounds only where a feature is needed. The lock is the pin (G1-15).
- **Markers:** `addopts` keeps model and data tests out of a plain `uv run --frozen pytest`, which is the agents' command and the `test` job's. A later `-m` wins, so `pytest -m models` runs only the model tests.

### `toolchain.toml`

Add a table beside `[agents]`, which the runner reads and leaves alone:

```toml
[uv]
version = "<x.y.z>"   # the uv release CI and the README use; the current release when 1a is built
```

`tests/test_toolchain.py` asserts that `.python-version` says `3.11`, and that `product.yml`'s `astral-sh/setup-uv` steps all pass this version (read with a regular expression: no YAML library is needed). `check_readme.py` checks that the README names it (below).

### Modules

```
src/lmt/__init__.py      __version__ = importlib.metadata.version("local-meeting-transcriber")
src/lmt/__main__.py      from lmt.cli import run; run()
src/lmt/errors.py        the error types below
src/lmt/cli.py           build_parser(), validate(args), main(argv) -> int, run()
src/lmt/models.py        stub: def cli_models(args): raise NotBuilt("models")         (item 3 replaces it)
src/lmt/pipeline.py      stub: def cli_transcribe(args): raise NotBuilt("transcribe") (stage 2)
src/lmt/eval/__init__.py empty
src/lmt/eval/cli.py      stub: def cli_eval(args): raise NotBuilt("eval")             (item 6 replaces it)
```

**`errors.py`.** Every error the product means to raise is an `LmtError`. `str(e)` is `"<subject>: <problem>"`, where the subject is the file or option at fault, so the one line printed is `lmt: error: <subject>: <problem>`.

| Class | `exit_code` | Raised for (`public-api.md`, "Exit codes") |
| --- | --- | --- |
| `LmtError(subject, problem)` | 1 | The base. Not raised directly. |
| `NotBuilt(command)` | 1 | A command whose item hasn't landed yet. The problem reads "not built yet (G1 stage 2)". It goes when stage 2 closes. |
| `UsageError` | 2 | Unknown option, bad value, conflicting options, an existing output without `--overwrite` |
| `InputError` | 3 | Missing, unreadable, empty, corrupt or unsupported input; no audio track; unwritable output directory; a missing or unreadable file for `--check-readme` |
| `NoSpeechError` | 4 | No speech found |
| `ModelError` | 5 | A model missing with `--offline`, a failed download, a checksum mismatch |
| `CheckFailed` | 6 | `lmt eval --check-readme` found the table differs |

**`cli.py`.**
- `build_parser()` builds the whole public CLI now: `transcribe`, `models` (`download`, `list`, `verify`) and `eval`, with exactly the options and defaults in `public-api.md`. Each subcommand calls `set_defaults(handler="lmt.pipeline:cli_transcribe")` (or `lmt.models:cli_models`, `lmt.eval.cli:cli_eval`). `main` imports the handler's module only when it runs, so `lmt --help` loads no heavy library. Later items replace a stub module, never `cli.py`. The exceptions are the later goals' items that add a command: G2's `lmt live` item adds `live`, and G3's items add `rename` and `demo` (`public-api.md`, the sections marked "(G2)" and "(G3, …)"). G1 builds none of them.
- The parser is a subclass of `argparse.ArgumentParser` whose `error(message)` raises `UsageError` instead of printing usage and exiting. So every usage error is one line, as G1-6 requires. The subject is the option argparse names, or `lmt` if it names none.
- `--version` prints `lmt 0.1.0`.
- `validate(args)` raises `UsageError` for what argparse can't express:
  - `--formats`: a comma-separated subset of `txt,srt,vtt,json`, kept in the order given, without repeats. Anything else names `--formats`.
  - `--num-speakers`, `--min-speakers`, `--max-speakers`: integers from 1 to 20, with min ≤ max. `--num-speakers` can't be combined with min or max, and `--no-diarize` with any of the three.
  - `eval`: exactly one of `--set` and `--check-readme`; `--update-readme` only with `--set full`.
  - `--model` isn't checked here. Stage 2 checks it against the model manifest.
- `main(argv=None) -> int`: parse, validate, call the handler, return its code (`None` is 0). It catches `LmtError` and prints `lmt: error: {e}` to stderr, returning `e.exit_code`; `KeyboardInterrupt` returns 130; any other exception prints `lmt: error: internal: <type>: <message>` and returns 1, never a traceback (Q6's full report comes with the pipeline). `run()` is `sys.exit(main())`.

**Tests (`tests/test_cli.py`):** `lmt --help` and every subcommand's `--help` exit 0; `--version`; one test per `validate` rule and per argparse error, each checking exit 2 and a single stderr line starting `lmt: error:` that names the option; a stub command exits 1 with one line; `KeyboardInterrupt` gives 130. Plus G1-6's table test: it reads the option tables in `design/public-api.md` (rows starting `` | `- ``) and compares each command's option strings with the parser's, both ways. It skips any section whose heading ends in a later goal's marker, "(G2)" or "(G3, …)", until the item that adds that section's command removes its skip (spec, G2-7 and G3-3).

### `NOTICE`, `LICENSE` and the README

- **`LICENSE`:** MIT (§7), naming the Owner as `aray4702`.
- **`NOTICE`:** the product is MIT; the models it downloads, each with its licence and a link to its model card, from the builder's table on #81 (19:57 PT): `Systran/faster-distil-whisper-large-v3` (MIT), `pyannote/speaker-diarization-3.1` and `pyannote/segmentation-3.0` (MIT), and `pyannote/wespeaker-voxceleb-resnet34-LM` (CC BY 4.0, with its attribution as the model card gives it), per the Owner's 13a.
- **`README.md`:** S1-1 to S1-4 as revised in the spec, plus a last section, `## Licences`, that gives the product's licence and the four models' licences in one sentence each, linking `NOTICE` (13a). The build block:

  ```sh
  git clone https://github.com/aray4702/local_meeting_transcriber.git
  cd local_meeting_transcriber
  uv sync --locked
  uv run lmt --help
  ```

  `## Checks` names the test command `uv run --frozen pytest` as inline code. **The evaluation command is left out for now.** S1-4 asks for it once the package exists, but S1-2 lets the README claim only what the gate tests, and `lmt eval --set ci` can't run until stage 2. The stage-2 item that adds the `eval-ci` run adds the command to the README and to `PRODUCT_COMMANDS` together.
- **`check_readme.py`:** `TITLE = "# Local Meeting Transcriber"`. S1-3 also checks that the build block's last line is `uv run lmt --help`, and that the README names `toolchain.toml`'s uv version. S1-4 also checks each string in `PRODUCT_COMMANDS = ["uv run --frozen pytest"]` appears in `README.md` outside fenced code and in `product.yml`. Its unit tests cover each new check, passing and failing.

### The `test` job

```yaml
test:
  runs-on: ubuntu-24.04
  timeout-minutes: 20
  steps:
    - actions/checkout (pinned SHA), persist-credentials: false
    - astral-sh/setup-uv (pinned SHA), version: <toolchain.toml [uv] version>, enable-cache: true
    - run: uv sync --locked --all-extras
    - run: uv run --frozen ruff check
    - run: uv run --frozen pytest
```

The `readme` job also needs `astral-sh/setup-uv`, since S1-3's block now runs `uv`.

**Test of the item:** `uv run lmt --help` exits 0; `tests/test_cli.py` and `tests/test_toolchain.py` pass; the `readme` and `test` jobs pass on the PR.

## 1b. Planned dependencies and the licence check (new item)

**First step,** before any PR: add the dependencies below, `uv lock`, install both platforms as the `test` job will (below), and run `check_licences.py --inventory` on each. Post both tables on the item. If anything falls outside the Owner's answer 2a (`project_requirements.md` §7), escalate it to the Owner in one batch, with a recommendation each, and stop before the PR. Licences that may well turn up outside 2a's list: `Zlib`, `0BSD` and `CC0-1.0` (numpy's metadata), `MIT-CMU` (pillow's), `bzip2-1.0.6` or `libpng` (bundled libraries). The allow list never gains one without the Owner's answer.

### Dependencies

```toml
dependencies = [
  "faster-whisper>=1.1",
  "pyannote.audio>=3.3,<4",       # answer 8a
  "torch>=2.5,<2.9",              # direct, so the CPU index applies on Linux; <2.9 while pyannote.audio 3.x reads audio through torchaudio's I/O
  "torchaudio>=2.5,<2.9",
  "huggingface_hub>=0.25",
]

[project.optional-dependencies]
eval = ["jiwer>=3.1", "pyannote.metrics>=3.2,<4", "regex", "more-itertools"]   # regex and more-itertools: the vendored normalizer

[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true

[tool.uv.sources]
torch = [{ index = "pytorch-cpu", marker = "sys_platform == 'linux'" }]
torchaudio = [{ index = "pytorch-cpu", marker = "sys_platform == 'linux'" }]
```

The `dev` group gains the eval extra (as `local-meeting-transcriber[eval]` if uv accepts the project referring to itself, otherwise by repeating the four packages), so the agents' `uv run --frozen pytest` has them. Stage 2's test libraries (`jsonschema`, `srt`, `webvtt-py`) also go into `dev` now, so the Owner sees one inventory, not two. If the bounds above don't lock, the Developer may move them, saying why on the item.

`tests/test_imports.py` imports `faster_whisper`, `pyannote.audio`, `huggingface_hub`, `jiwer` and `pyannote.metrics`, and checks `torch.version.cuda is None` on Linux (CPU-only wheels).

### `toolchain.toml`: the allow list

```toml
[licences]
# The Owner's answer 2a on #81, project_requirements.md §7. Only the Owner adds to these lists.
# Licences a distribution's own metadata may give.
distributions = ["MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "PSF-2.0", "ISC", "Unlicense", "HPND", "MPL-2.0"]
# Further licences a bundled shared library may carry. LGPL is accepted only as a bundled library.
bundled = [
  "LGPL-2.1-only", "LGPL-2.1-or-later", "LGPL-3.0-only", "LGPL-3.0-or-later",
  "GPL-3.0-or-later WITH GCC-exception-3.1",
  "LicenseRef-Intel-Simplified-Software-License",
  "Apache-2.0 WITH LLVM-exception",
]

# Where a distribution's metadata gives no clear SPDX licence. Pinned to the version that was read.
[[licences.override]]
distribution = "<name>"
version = "<version in uv.lock>"
licence = "<SPDX expression>"
source = "<URL the licence was read from>"

# One entry per bundled shared library (or a family, by glob).
[[licences.library]]
distribution = "av"
files = "av.libs/libavcodec-*.so*"       # fnmatch glob, relative to site-packages
library = "FFmpeg libavcodec"
licence = "LGPL-2.1-or-later"
platforms = ["linux-x86_64"]             # linux-x86_64, macos-arm64, or both
source = "<URL>"
```

A distribution's own libraries (torch's `torch/lib/libtorch_cpu.so`, for example) also get entries, with the distribution's licence.

### `.github/scripts/check_licences.py`

Standard library only, so the job's system Python runs it against both installs.

```
python3 -I .github/scripts/check_licences.py --site DIR --platform {linux-x86_64,macos-arm64}
                                             [--toolchain toolchain.toml] [--inventory]
```

- **Distributions:** `importlib.metadata.distributions(path=[DIR])`. Each one's licence is, in order: `License-Expression`; else its licence classifiers, mapped by a table in the script (MIT, Apache Software License → `Apache-2.0`, ISC License (ISCL) → `ISC`, Python Software Foundation License → `PSF-2.0`, Mozilla Public License 2.0 (MPL 2.0) → `MPL-2.0`, The Unlicense (Unlicense) → `Unlicense`, Historical Permission Notice and Disclaimer (HPND) → `HPND`), joined with `AND` when there are several; else `License`, if it parses as an SPDX expression. "BSD License" isn't a clear SPDX licence, so it needs an override, as does anything else unclear. An override applies only at its exact version, so an upgrade makes the Developer read the licence again.
- **The SPDX check:** a small parser for identifiers, `LicenseRef-…`, `AND`, `OR`, `WITH` and parentheses. `A OR B` passes if either passes, `A AND B` if both do, and `X WITH E` only if `"X WITH E"` is listed whole. A distribution passes against `distributions`; a library against `distributions` plus `bundled`.
- **Bundled libraries:** every file in a distribution's `RECORD` matching `*.so`, `*.so.*` or `*.dylib`, except Python extension modules. An extension module is a file whose name ends `.cpython-311-x86_64-linux-gnu.so`, `.cpython-311-darwin.so` or `.abi3.so`. Each library must match a `[[licences.library]]` entry for its distribution and platform, and that entry's licence must pass. An entry that matches nothing is a warning, not a failure, since the platforms differ.
- **Output:** one line per distribution and library, `PASS` or `FAIL`, name, version, licence and where the licence came from (metadata field, classifier, override); the same to `GITHUB_STEP_SUMMARY`, as `check_readme.py` does. Exit 1 if anything fails. `--inventory` prints the lines as a Markdown table and always exits 0, for the first step's post.
- **Tests (`test_check_licences.py`, `unittest`, so the `readme` job's existing `unittest discover` runs them):** a fake site directory of `*.dist-info` folders (`METADATA`, `RECORD`) and empty library files. Cases: allowed licences pass; an unlisted licence fails; an LGPL *distribution* fails; `OR` passes on one allowed branch; `WITH` passes only when listed whole; a classifier maps; "BSD License" without an override fails; an override at another version fails; an unlisted bundled library fails; a listed one passes only on its platform; extension modules are skipped.

### The `test` job's new steps

After `uv sync --locked --all-extras`:

```sh
python3 -I .github/scripts/check_licences.py --site .venv/lib/python3.11/site-packages --platform linux-x86_64
uv export --frozen --all-extras --no-emit-project -o "$RUNNER_TEMP/requirements.txt"
uv pip install --target "$RUNNER_TEMP/macos" --python-platform aarch64-apple-darwin --python-version 3.11 \
  --no-deps --require-hashes -r "$RUNNER_TEMP/requirements.txt"
python3 -I .github/scripts/check_licences.py --site "$RUNNER_TEMP/macos" --platform macos-arm64
```

macOS takes torch from PyPI. If the export carries the PyTorch CPU index for macOS's lines, the install adds `--index-url https://pypi.org/simple`. The product's own licence is checked in the Linux install.

**Test of the item:** both licence checks pass in the `test` job; the unit tests show the check fails on an unlisted licence and on an unlisted bundled library (G1-15).

## 2. The tier filter (#107)

### `.github/scripts/tiers.py`

Standard library only. The path rules are constants that copy `design/architecture.md`'s "CI" table, with a comment pointing to it:

```python
TIER1 = ("src/", "tests/", "schema/", "results/", "pyproject.toml", "uv.lock", "toolchain.toml",
         ".python-version", "README.md", ".github/scripts/", ".github/workflows/")
NOT_TIER2 = ("README.md", "results/", "src/lmt/eval/", ".github/scripts/")
TIER3_EXCEPT = ("src/lmt/export/txt.py", "src/lmt/export/srt.py", "src/lmt/export/vtt.py",
                "src/lmt/rename.py", "src/lmt/demo/")
TIER3_FILES = ("pyproject.toml", "uv.lock", "toolchain.toml", ".python-version",
               ".github/scripts/tiers.py")
# Tier 3: src/lmt/ except TIER3_EXCEPT, TIER3_FILES, or .github/workflows/.
```

An entry ending `/` matches by prefix, any other exactly.

`rename.py` and `demo/` leave tier 3 like the exporters, by the Owner's answers on #83 and #129. The filter itself, `.github/scripts/tiers.py`, is tier 3 beside the workflows, by the Owner's answer `1` on #121 (#134): it decides which jobs run, so a change to it isn't checked by its own filter. The other scripts in `.github/scripts/` stay at tier 1.

- `tier_for_path(path) -> int` is the highest tier whose rule matches, else 0. `tier_for_paths(paths)` is the highest over all paths (0 for none).
- `main(argv)`, with `--event`, `--base` and `--head`:
  - `workflow_dispatch` or `schedule`: 3.
  - Otherwise `git diff --name-only --no-renames <base>...<head>` (from their merge base). `--no-renames` lists a renamed file's old path too, so moving a file out of a tier can't hide it. For a push, the base is `github.event.before`. If the base is empty or all zeros, or `git` fails, the result is 3, and the reason is printed.
  - It writes `tier=<n>` to `$GITHUB_OUTPUT`, and the paths that set it to the step summary.

### `product.yml`

A first job, `changes`, checks out with `fetch-depth: 0` and `persist-credentials: false` and runs:

```sh
python3 -I .github/scripts/tiers.py --event "$EVENT" --base "$BASE" --head "$HEAD"
```

with `EVENT: ${{ github.event_name }}` (in a called workflow, the gate's event), `BASE: ${{ github.event.pull_request.base.sha || github.event.before }}` (as the gate's `generic` job uses) and `HEAD: ${{ github.sha }}`. Every other job has `needs: changes`:

| Job | Condition | Item 2 leaves it with |
| --- | --- | --- |
| `readme` | always | Tier 0: the unit tests, and `check_readme.py --root . --no-install`. Tier ≥ 1 (`if:` on the steps): setup-uv, then `check_readme.py --root .` in full |
| `test` | `fromJSON(needs.changes.outputs.tier) >= 1` | as item 1a or 1b left it |
| `test-models` | `>= 2` | checkout, setup-uv, `uv sync --locked --all-extras`. Item 3 adds its steps |
| `eval-ci` | `>= 3` | the same three steps. Item 5a adds its steps |

A job skipped by its `if` counts as passed in the called workflow, so the gate's `needs.product.result` stays `success`. The first PR shows this.

`check_readme.py --no-install` skips S1-3 and S1-4, the two checks that run a block. It runs S1-1, S1-2's heading and S1-5, as tier 0 lists.

**Tests (`test_tiers.py`, `unittest`):** one path per tier (`docs.md` → 0, `README.md` → 1, `tests/test_cli.py` → 2, `src/lmt/cli.py` → 3); `src/lmt/eval/score.py` → 3; `results/full.json` → 1; `schema/transcript.schema.json` → 2; each exporter left out of tier 3 → 2, and `export/json.py` → 3; `src/lmt/rename.py` and `src/lmt/demo/page.html` → 2, and `src/lmt/rename.py.orig` → 3 (an exact entry matches only exactly); `.github/workflows/gate.yml` → 3; `.github/scripts/x.py` → 1, and `.github/scripts/tiers.py` → 3; `uv.lock` → 3; moving `src/lmt/cli.py` to `notes.md` → 3, by its old path; the fallback (an all-zeros base, a base `git` can't resolve) → 3; `workflow_dispatch` and `schedule` → 3. Plus `--no-install` in `test_check_readme.py`.

**Test of the item:** the unit tests, and the PR's gate run, whose summary shows tier 3 (it touches `.github/workflows/`) with every job run.

## 3. Models (#108)

### `src/lmt/models.toml`

```toml
schema_version = 1
default_asr = "distil-large-v3"

[[model]]
name = "distil-large-v3"
role = "asr"                              # asr | diarization | segmentation | embedding
repository = "Systran/faster-distil-whisper-large-v3"
revision = "c3058b475261292e64a0412df1d2681c06260fab"
licence = "MIT"
card = "https://huggingface.co/Systran/faster-distil-whisper-large-v3"
gated = false

[[model.file]]
path = "model.bin"
sha256 = "<64 hex>"
size = <bytes>
```

- **The four default models,** at the builder's revisions (#81, 19:57 PT): the ASR model above; `pyannote/speaker-diarization-3.1` at `84fd25912480287da0247647c3d2b4853cb3ee5d` (role `diarization`, MIT, gated); `pyannote/segmentation-3.0` at `e66f3d3b9eb0873085418a7b813d3b369bf160bb` (`segmentation`, MIT, gated); `pyannote/wespeaker-voxceleb-resnet34-LM` at `837717ddb9ff5507820346191109dc79c958d614` (`embedding`, `CC-BY-4.0`, gated; 13a). The other ASR candidates come with stage 2's investigation.
- **Which files:** those the stage loads, not READMEs, images or `.gitattributes`. For faster-whisper: `config.json`, `model.bin`, `preprocessor_config.json`, `tokenizer.json` and `vocabulary.json`. For pyannote: each repository's `config.yaml` and `pytorch_model.bin`, where it has them.
- **Hashes and sizes:** computed from the files the builder cached on the Mac, `~/.cache/huggingface/hub/models--<org>--<name>/snapshots/<revision>/`. Large files are cross-checked against the Hub's own SHA-256 (`HfApi().model_info(repo, revision=..., files_metadata=True)`, the `lfs.sha256` of each file). If the Developer's run can't read that cache, it asks the builder, who can.

### `src/lmt/models.py`

```python
MANIFEST_PATH = Path(__file__).with_name("models.toml")   # tests point it at a small manifest
cache_dir() -> Path                       # LMT_CACHE_DIR, else ~/.cache/lmt/models
load_manifest(path=MANIFEST_PATH) -> Manifest          # dataclasses Model, ModelFile; checks the format
default_models(manifest, asr=None) -> list[Model]      # the ASR model (default_asr or `asr`) + the three pyannote models
model_dir(model) -> Path                  # cache_dir() / repository / revision
file_status(model, f) -> "verified" | "missing" | "mismatch"
download(models, token=None) -> None      # raises ModelError
verify(models) -> list[Path]              # deletes each mismatched file; returns them
ensure(models, offline=False) -> dict[str, Path]       # for stage 2: name -> verified model_dir
cli_models(args) -> int
```

- **Cache layout:** `<LMT_CACHE_DIR>/<repository>/<revision>/<path>`, our own and not Hugging Face's, so a stage loads a model from a local directory and never resolves a name over the network. Stage 2 loads pyannote's segmentation and embedding models from their directories, not by the names in 3.1's `config.yaml`.
- **Download:** for each file not already verified: `hf_hub_download(repo_id, filename, revision=<revision>, local_dir=<cache>/.partial/<random>, token=os.environ.get("HF_TOKEN") or False)`. `False` keeps `huggingface_hub` from reading a token file. Then check size and SHA-256 and `os.replace` the file into place. A mismatch deletes the file and raises `ModelError("<repository>/<path>", "SHA-256 doesn't match the manifest")`. A network or HTTP error raises `ModelError` naming the repository. A gated model with no `HF_TOKEN` raises `ModelError("HF_TOKEN", "needed to download the gated model <repository>")`. The staging directory is always removed. One progress line per file goes to stderr, never the token.
- **Before importing `huggingface_hub`,** set `HF_HUB_DISABLE_TELEMETRY=1` (Q8).
- **`ensure`:** checks every file's SHA-256 once per process, then sets `HF_HUB_OFFLINE=1` (architecture, "Model handling"). A mismatch is deleted and raises `ModelError` (exit 5, G1-15). A missing file downloads, or raises `ModelError` under `offline`.
- **Hashing:** SHA-256 in 1 MiB chunks.

### `lmt models` (as `public-api.md` gives it)

- **`download [--model NAME]`:** `default_models(manifest, asr=NAME)`; downloads what's missing or mismatched; prints nothing to stdout. An unknown `NAME` is a `UsageError` naming `--model`.
- **`list [--bytes]`:** stdout, tab-separated, a header line, then one line per model in manifest order: `NAME ROLE REVISION DEFAULT STATUS`, with `DEFAULT` `yes` or `no` and `STATUS` `verified`, `missing` or `mismatch` (the worst of its files). `--bytes` adds `BYTES`, the size of the model's verified files, and a last line `total-default<TAB><bytes>`, the default models' verified bytes. `list` never deletes.
- **`verify`:** `verify()` on every model with any file present. Exits 5 if it deleted anything, naming the first file; otherwise 0. Missing files are listed on stderr but aren't an error.

### Tests

- `tests/test_models.py` (no model needed): the real manifest pins every file (40-hex revision, 64-hex SHA-256, positive size, a licence of `MIT` or `CC-BY-4.0`, at least one file per model), and the default models' manifest sizes total ≤ 2.0 × 10⁹ bytes (G1-12, and G1-10's proxy). With a small fake manifest and `hf_hub_download` replaced by a function that writes known bytes: a good file is verified and placed; a bad one raises exit 5 and leaves nothing in the cache (G1-15's bad-checksum test); `lmt models verify` deletes a corrupted cached file and exits 5; `--offline` with a file missing exits 5; no `HF_TOKEN` for a gated model exits 5 with one line; `list --bytes` prints the documented columns and total.
- One test marked `models`: `lmt models list --bytes` shows every default model `verified`, and `total-default` ≤ 2.0 × 10⁹ (G1-10's disk check, on the real files).

### The `test-models` job

After item 2's three steps:

```yaml
- uses: actions/cache@<pinned SHA>
  id: models
  with:
    path: ~/.cache/lmt/models
    key: models-${{ hashFiles('src/lmt/models.toml') }}
- name: Download the default models
  if: steps.models.outputs.cache-hit != 'true'
  env:
    HF_TOKEN: ${{ secrets.HF_TOKEN }}       # this step only
  run: uv run --frozen lmt models download
- run: uv run --frozen lmt models verify
- run: uv run --frozen pytest -m models
```

**Test of the item:** the tests above, and the `test-models` job passing on the PR (a cache miss, so it downloads with `HF_TOKEN`).

## 4. Harness scoring and the results file (#109)

### The vendored normalizer

`src/lmt/eval/normalizer/` holds `__init__.py`, `basic.py`, `english.py` and `english.json`, copied unchanged from `whisper/normalizers/` in `openai/whisper` at the commit of its latest release tag when this item is built (`v20250625` at the time of writing; the Developer resolves the tag to its full commit hash). Also there: `LICENSE`, upstream's MIT notice; and `VENDORED.md`, which gives the repository, the tag, the full commit and the upstream path. Upstream's `__init__.py` uses relative imports, so nothing needs editing. `NOTICE` gains one line for it. `normalize(text)` in `score.py` is `EnglishTextNormalizer()(text)`, with the normalizer built once.

### `src/lmt/eval/score.py`

```python
@dataclass(frozen=True)
class Turn:
    start: float
    end: float
    speaker: str

@dataclass(frozen=True)
class Item:                          # one scored file; item 5a builds these
    dataset: str                     # "LS-ci", "AMI-ci", "LS full", "AMI full", "one-hour"
    id: str
    audio: Path
    duration: float
    ref_text: str | None = None
    ref_turns: tuple[Turn, ...] | None = None

@dataclass(frozen=True)
class Hypothesis:                    # one system's output on one item
    text: str | None                 # the words in order (WER)
    turns: tuple[Turn, ...] | None   # speaker turns (DER)
    wall_seconds: float | None = None
    peak_rss_bytes: int | None = None

SYSTEMS = ("product", "whisper-alone", "pyannote-alone")

def wer(pairs: Sequence[tuple[str, str]]) -> float          # (reference, hypothesis) pairs
def der(files: Sequence[tuple[Sequence[Turn], Sequence[Turn], float]]) -> float   # (reference, hypothesis, duration)
def hypothesis_from_transcript(doc: dict) -> Hypothesis      # transcript JSON, public-api.md v1.0
def turns_from_rttm(text: str) -> tuple[Turn, ...]
def score(items: Sequence[Item], hyps: Mapping[tuple[str, str, str], Hypothesis]) -> list[dict]
    # keys: (system, dataset, item id); returns the results file's "figures"
```

- **`wer`:** both sides through `normalize`. Then one `jiwer.process_words(refs, hyps)` call over the whole set, and WER = (S + D + I) / (S + D + H): pooled, not a mean of per-file rates (spec, "Terms"). An empty normalized reference is a `ValueError`. An empty hypothesis counts every reference word as a deletion. If the locked `jiwer` refuses empty hypotheses, `wer` counts them itself.
- **`der`:** one `DiarizationErrorRate(collar=0.0, skip_overlap=False)`, called on each file with `pyannote.core.Annotation`s built from the turns and `uem=Timeline([Segment(0, duration)])`. Then `abs(metric)`, the pooled rate. The UEM is the whole file, which scores exactly what the spec's "no UEM, whole file" means and stops `pyannote.metrics` warning that it approximates one.
- **`hypothesis_from_transcript`:** `text` is the segments' `text` joined by single spaces, in order; `turns` are the segments' `(start, end, speaker)`. This is DER's hypothesis as the spec defines it (answer 4a).
- **`turns_from_rttm`:** reads `SPEAKER <file> <channel> <start> <duration> <NA> <NA> <speaker> <NA> <NA>` lines. Anything else is a `ValueError` naming the line.
- **`score`:** one figure for each dataset (in the order the items first give them) and system (in `SYSTEMS` order) that has hypotheses. A dataset × system pair with hypotheses for some items but not all is a `ValueError`. Each figure is `{"dataset", "system", "wer", "der", "audio_seconds", "wall_seconds", "rtf", "peak_rss_bytes"}`, in that key order:
  - `wer` when every item has `ref_text` and every hypothesis `text`; `der` when every item has `ref_turns` and every hypothesis `turns`. Otherwise `null`.
  - `audio_seconds` is the sum of `duration`. `wall_seconds` is the sum, and `peak_rss_bytes` the maximum, when every hypothesis has one, otherwise `null`. `rtf` = `wall_seconds / audio_seconds`, or `null`.
  - Rounding, so the file is the same on every run: `wer` and `der` to 6 decimal places, the seconds and `rtf` to 3.

### `src/lmt/eval/report.py`

```python
TIMING_FIELDS = ("date", "wall_seconds", "rtf", "peak_rss_bytes")

def build(set_name, figures, models, determinism=None, *, out_dir,
          commit=None, dirty=None, date=None, machine=None) -> dict
def write(path, results) -> None
def strip_timing(results) -> dict
def same_accuracy(a, b) -> bool
def machine() -> dict
```

- **`build`** returns the results file, version 1.0, in `public-api.md`'s key order. `models` is the caller's dict, shaped as the transcript JSON's `models`. The keyword arguments are for tests; otherwise:
  - `commit` is `git rev-parse HEAD`, or `null` outside a git checkout.
  - `dirty` is whether `git -C <top> status --porcelain` prints anything, where `<top>` is `git rev-parse --show-toplevel`. When `out_dir` resolves inside `<top>` (`Path(out_dir).resolve().is_relative_to(Path(top).resolve())`), the command adds `-- . ':(exclude)<out_dir relative to top>'`, so the first of two runs writing `results/ci.json` doesn't make the second "dirty" (G1-5's comparison would fail otherwise). An `out_dir` outside the work tree, such as `--out /tmp/r`, can't dirty it, and an exclude would make git fail ("outside repository"), so none is added.
  - `date` is `datetime.now().astimezone().isoformat(timespec="seconds")`.
- **`machine()`:** `arch` is `platform.machine()` (`uname -m`). On Linux: `cpu` is `/proc/cpuinfo`'s first `model name`, `memory_bytes` is `/proc/meminfo`'s `MemTotal` × 1024, `os` is `/etc/os-release`'s `PRETTY_NAME`. On macOS: `sysctl -n machdep.cpu.brand_string` and `hw.memsize`, and `os` is `"macOS " + platform.mac_ver()[0]`.
- **`write`:** `json.dumps(results, indent=2, ensure_ascii=False) + "\n"`, to a temporary file in the same directory, then renamed into place.
- **`strip_timing`:** a copy with the timing fields removed, top level and in each figure. `same_accuracy` compares the two stripped files' serialized form byte for byte (G1-5, G1-12).

### Fixtures and tests

`tests/fixtures/eval/` holds fixed references and hypotheses, with the hand-computed figures in comments in the tests:

- **WER, `ls/`:** four utterances, references in LibriSpeech's upper case, hypotheses as transcript JSON:

  | Id | Reference | Hypothesis | Normalized errors | Reference words, normalized |
  | --- | --- | --- | --- | --- |
  | u1 | `THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG` | `The quick brown fox jumped over the lazy dog.` | 1 substitution | 9 |
  | u2 | `IT WAS TWENTY FIVE PAST TEN` | `It was 25 past ten.` | 0 (both normalize to `it was 25 past 10`) | 5 (`it`, `was`, `25`, `past`, `10`; 6 before normalizing) |
  | u3 | `I SAW HER` | *(empty)* | 3 deletions | 3 |
  | u4 | `GOOD MORNING` | `Good good morning.` | 1 insertion | 2 |

  Pooled WER = 5 / (9 + 5 + 3 + 2) = 5 / 19 = 0.263158. The mean of per-file rates, (1/9 + 0 + 1 + 1/2) / 4, would be 0.402778, so the test also proves the pooling. If the pinned normalizer disagrees with a row's normalized form, the Developer replaces that row with one it agrees with, recomputes the totals by hand, and says so on the item. The test must never be adjusted to whatever the code prints.
- **DER, `ami/`:** two files, references as RTTM, hypotheses as transcript JSON (a single stream, so no overlap):
  - f1, 10 s. Reference: A 0–4, B 4–8, A 7–10. Hypothesis: S1 0–4, S2 4–7, S1 7–10. Missed speech 1 s (B in the overlap 7–8), against 11 s of reference speech.
  - f2, 6 s. Reference: A 0–3, B 3–6. Hypothesis: S1 0–4, S2 4–6. Confusion 1 s (3–4), against 6 s.
  - Pooled DER = 2 / 17 = 0.117647. With `skip_overlap=True` f1 would score 0, and the mean of per-file rates would be 0.128788, so the test proves both settings.
- **Results file:** `results_golden.json`, built by `build` from the two sets' figures with a fixed `commit`, `dirty`, `date` and `machine`. The test compares `write`'s output with it byte for byte. Then it builds a second file with other timing values and other `wall_seconds` and checks `same_accuracy` is true, and that changing one `wer` makes it false. Tests of `dirty` make a temporary git repository with one commit and check: writing into an output directory inside it leaves `dirty` false; an `out_dir` outside it (a second temporary directory) gives `false`, with no git error; an untracked file elsewhere in the repository gives `true`, both with an inside and an outside `out_dir`.

**Test of the item:** `tests/test_score.py` and `tests/test_report.py`, in the `test` job.

## 5a. Dataset manifests, cache and the CI subset (#110)

### Manifests

`src/lmt/eval/manifests/sources.toml` lists every file that's downloaded, and the archive members that are used:

```toml
schema_version = 1

[[source]]
id = "librispeech-test-clean"
urls = ["https://www.openslr.org/resources/12/test-clean.tar.gz",
        "https://us.openslr.org/resources/12/test-clean.tar.gz"]     # tried in order
sha256 = "<64 hex>"
size = <bytes>
licence = "CC-BY-4.0"
keep = false                     # deleted once the members it needs are extracted

[[source.member]]
path = "LibriSpeech/test-clean/1089/134686/1089-134686-0000.flac"
sha256 = "<64 hex>"
```

`src/lmt/eval/manifests/sets.toml` says what each set scores:

```toml
schema_version = 1

[[dataset]]
name = "LS-ci"
set = "ci"
kind = "librispeech"
source = "librispeech-test-clean"
utterances = ["1089-134686-0000", "..."]     # 20 ids

[[dataset]]
name = "AMI-ci"
set = "ci"
kind = "ami"
meetings = ["ES2004a"]
audio = "ami-ES2004a"            # source ids
words = "ami-annotations-1.6.2"
rttm = "ami-rttm-ES2004a"
crop = 300.0                     # seconds from the start
```

- **Sources for the CI subset:**
  - LibriSpeech test-clean from openslr, the archive, with the 20 utterances' `.flac` members and their chapters' `.trans.txt` members. Cross-check the archive's SHA-256 against torchaudio's published checksum for `test-clean.tar.gz`, and against openslr's MD5.
  - `ES2004a.Mix-Headset.wav` from `https://groups.inf.ed.ac.uk/ami/AMICorpusMirror/amicorpus/ES2004a/audio/ES2004a.Mix-Headset.wav`.
  - The AMI manual annotations v1.6.2, `https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/ami_public_manual_1.6.2.zip`, with the `words/ES2004a.*.words.xml` members.
  - `only_words/rttms/test/ES2004a.rttm` from `https://raw.githubusercontent.com/BUTSpeechFIT/AMI-diarization-setup/<commit>/…`. The commit is the repository's `main` when this item is built, in full, and every RTTM URL uses it.
- **LS-ci's 20 utterances,** fixed by a rule so that anyone gets the same list: test-clean's 40 speakers in numeric order; take the first 20; for each, the first utterance in sorted id order that lasts 4–12 s. That gives about 2.5 minutes. The manifest records the ids and, in a comment, their total duration.
- **How the Developer gets the hashes:** by downloading each file once and hashing it. A manifest entry never takes a hash from its first CI download.

### `src/lmt/eval/datasets.py`

```python
data_dir() -> Path                                # LMT_DATA_DIR, else ~/.cache/lmt/data
load_manifests() -> Manifests                     # both files; checks the format and that ids resolve
fetch(set_name: str) -> list[Item]                # "ci" now; 5b adds "full" and the fixtures
main(argv) -> int                                 # python -m lmt.eval.datasets fetch ci
```

- **Cache layout:** `<LMT_DATA_DIR>/sources/<source id>/<file or member path>` for what's downloaded, and `<LMT_DATA_DIR>/derived/<dataset name>/…` for what a recipe makes.
- **Fetch:** for each source the set needs, verify what's in the cache by SHA-256, and download only what's missing or wrong. A download goes to a temporary file, is checked by size and SHA-256, and is renamed into place. An archive is verified as a whole, then only the members listed are extracted, each checked against its own hash, and the archive is deleted if `keep = false`. A mismatch deletes the file and raises `InputError("<url>", "SHA-256 doesn't match the manifest")` (exit 3). A failed download tries the next URL, then raises `InputError`. Downloads use `urllib.request`, so no dependency is added.
- **Recipes, which are deterministic and checked:**
  - **LibriSpeech:** `ref_text` is the utterance's line in its chapter's `.trans.txt`, without the id. `duration` comes from the FLAC's header (`soundfile.info`).
  - **AMI words:** every `<w>` element of every speaker's `words.xml` for the meeting, skipping those with `punc="true"`. A word without a `starttime` takes the previous word's in the same file (0 for the first). Sorted by start time, then speaker letter, then position in the file. `ref_text` is the words joined by spaces.
  - **AMI-ci's crop to 300 s:** the audio's first 300 × 16,000 frames, copied with the `wave` module into `derived/AMI-ci/ES2004a.wav`. The words kept are those whose midpoint is before 300 s. Turns are clipped to [0, 300], and those starting at or after 300 are dropped. The cropped WAV's SHA-256 is recorded in `sets.toml` too (`derived_sha256`), so the recipe is checked on every fetch.
- **`main`:** the `fetch` subcommand prints one line per dataset (name, items, total seconds) and returns 0. An `LmtError` prints as `cli.main` prints it and returns its code. This is an internal entry point for CI. Stage 2's `lmt eval --set ci` calls `fetch` itself.

### Tests

- `tests/test_manifests.py`: every source has a 64-hex SHA-256, a positive size and at least one URL, and every member has a SHA-256. Every URL starts with one of `https://www.openslr.org/resources/12/`, `https://us.openslr.org/resources/12/`, `https://groups.inf.ed.ac.uk/ami/`, `https://raw.githubusercontent.com/BUTSpeechFIT/AMI-diarization-setup/<the pinned commit>/`, or, for this repository's copies of the sample meeting and the AMI annotations only, `https://github.com/aray4702/local_meeting_transcriber/releases/download/sample-data-ami/` (#529), so the manifests name only LibriSpeech and AMI sources (G1-7's manifest half). Every dataset's source ids resolve. LS-ci has 20 utterances.
- `tests/test_datasets.py` (no network): `urllib.request.urlopen` replaced, serving small files. A good file is cached and verified; a bad one exits 3 and leaves nothing in the cache; the second URL is used when the first fails; archive members are extracted and checked. The AMI recipes run on a two-speaker words fixture: the order, missing start times, `punc` and the midpoint crop.
- One test marked `data`: after `fetch("ci")`, LS-ci has 20 items with references, and AMI-ci has one 300-second item with words and turns. All are verified.

### The `eval-ci` job

After item 2's three steps:

```yaml
- uses: actions/cache@<pinned SHA>
  with:
    path: ~/.cache/lmt/data
    key: data-${{ hashFiles('src/lmt/eval/manifests/*.toml') }}
- run: uv run --frozen python -m lmt.eval.datasets fetch ci
- run: uv run --frozen pytest -m data
```

Stage 2 adds `lmt eval --set ci` twice, the bounds and the comparison.

**Test of the item:** the tests above, and the `eval-ci` job fetching and verifying the CI subset on the PR.

## 5b. Full sets, the one-hour recording and the fixture clips (new item)

These are needed by stage 2 (the fixture clips) and stage 3 (the full sets), not by stage 1's outcome.

- **LS full:** `[[dataset]] name = "LS full"`, `set = "full"`, every utterance in the archive. Each member's SHA-256 is listed, as for LS-ci.
- **AMI full:** the 16 meetings in the spec's order, EN2002a–d, ES2004a–d, IS1009a–d and TS3003a–d, each with its audio, words members and RTTM. The words come from the same annotation archive, and the RTTMs from the same BUT commit.
- **A concatenation recipe:** `concat = [{source = "...", start = 0.0, end = <s>}, ...]`, with `gap` seconds of digital silence between pieces, an optional `cut` in seconds, and `derived_sha256` for the result. References shift by each piece's offset and are cropped at `cut` as AMI-ci's are. It builds three things:
  - **the one-hour recording:** AMI full's 16 meetings in order, `cut = 3600`;
  - **`tests/fixtures/clip.wav`:** about 60 s of one LibriSpeech test-clean speaker's consecutive utterances, `gap = 0`;
  - **`tests/fixtures/two_speakers.wav`:** four alternating turns by one female and one male test-clean speaker (their sex from LibriSpeech's `SPEAKERS.TXT`), `gap = 0.5`, about 60 s, with its RTTM and word references.

  Inputs that aren't 16 kHz mono are converted with `soundfile` and stored as 16-bit PCM WAV, so the bytes are the same on both platforms.
- **The fixture clips are committed,** with their references, so tests don't need the network. A test rebuilds them from the cache when the CI subset is there (`data`), and compares their SHA-256 with the committed files. Their FLAC, MP3, M4A, MP4 and MOV encodings need ffmpeg, so they belong to stage 2's decode item.

**Test of the item:** the manifest tests cover the new entries (16 AMI meetings, 2,620 LibriSpeech utterances); a unit test of the concatenation recipe on small WAVs (offsets, gaps, cut, references); and the `data` test of the fixture clips.

### 5b's open points, decided (#123)

#307 (#305) built `pin`, `{source, start, end}` slices, `cut`, `concat` and `place_references`. These are the Developer's four questions on #123. None changes a criterion: the sets, the cut at 3,600 s and the clips are as `spec/acceptance.md` gives them.

1. **The two-speaker clip's utterances** are fixed by `g1-stage2.md`, "The two-speaker clip's rule (for #123)" (PR #304), and by nothing here. The one-utterance-per-turn, 12–18 s rule proposed on #123 isn't adopted. Its references are as that rule says: `tests/fixtures/two_speakers.rttm`, one line per piece, and `tests/fixtures/two_speakers.txt`, the texts as `clip.txt` has them. The `[[fixture]]` gains `rttm` and `rttm_sha256` (both or neither; the RTTM is built from the pieces' offsets and checked as the reference is). `LibriSpeech/SPEAKERS.TXT` and the clip's FLAC and `.trans.txt` members join `librispeech-test-clean`, so the `data` test rebuilds the clip after `fetch ci`.
2. **`pin --write-members <source id>`** writes what `pin` hashed into `src/lmt/eval/manifests/sources.toml`, and nowhere else:
   - It needs `--member`, and the URL must be one of that source's `urls`, with the downloaded size and SHA-256 equal to its entry. Otherwise it writes nothing and exits 3.
   - It replaces that source's `[[source.member]]` tables (from its `[[source]]` to the next `[[source]]` or the end) with one `path`, `sha256` pair per member, in the archive's order. Every other line is left byte for byte.
   - It writes to a temporary file beside `sources.toml`, runs `load_manifests` on the result, and renames it into place only if that passes.
   - Its unit test uses a small served archive and a temporary manifest directory: the source's members are replaced; the rest of the file is unchanged; a URL or hash that doesn't match writes nothing.
3. **LS full** has a source of its own, `librispeech-test-clean-full`: the same URLs, SHA-256 and size as `librispeech-test-clean`, `keep = false`, and all 2,707 members (2,620 `.flac`, 87 `.trans.txt`), written by `pin --write-members`. `fetch_source` extracts every listed member, so `fetch ci` stays at its own members. In `sets.toml`, LS full has no `utterances`: for `kind = "librispeech"`, a missing `utterances` means every `.flac` member of the source, in sorted id order, each with its `.trans.txt` member. (An empty list is still an error.) The manifest test checks 2,620.
4. **AMI full** is one `[[dataset]] name = "AMI full"`, `set = "full"`, `kind = "ami"`. `meetings` lists the spec's 16 in order. `audio` and `rttm` are lists parallel to `meetings`, of the source ids `ami-<meeting>` and `ami-rttm-<meeting>` (ES2004a's ids stay). `words = "ami-annotations-1.6.2"`, which gains the other 60 `words/<meeting>.<speaker>.words.xml` members. Every `ami` dataset uses the list form, so AMI-ci becomes `audio = ["ami-ES2004a"]` and `rttm = ["ami-rttm-ES2004a"]` in the same PR. The loader checks that the lists are the same length as `meetings`, and allows `crop` only with one meeting. Each meeting is one item.
5. **The one-hour recording** is `[[dataset]] name = "one-hour"` (§4's name), `set = "full"`, `kind = "concat"`, with these fields:
   - `of = "AMI full"`;
   - `concat`: one slice per meeting of `of`, in its order, `{source = <its audio id>, start = 0, end = <frames / 16000>}`, the exact decimal. The loader checks the sources against `of`;
   - `gap = 0.0`, since the spec says only "concatenated";
   - `cut = 3600.0`;
   - `derived_sha256`.

   It is one item, `derived/one-hour/one-hour.wav`. Only pieces whose offset is before the cut are read, which are EN2002a and EN2002b. Each piece's words and turns are its meeting's, from `of`'s recipes. They are placed with `place_references` and cropped at the cut as AMI-ci's are. `fetch full` builds it after AMI full and checks `derived_sha256`. It isn't committed.

## 6. The README results table (#111)

### `results/full.json`, the placeholder

Until the Owner's full run, `results/full.json` is a version 1.0 results file with no figures and nothing measured:

```json
{
  "schema_version": "1.0",
  "set": "full",
  "commit": null, "dirty": false,
  "date": null,
  "machine": null,
  "lmt_version": "0.1.0",
  "models": null,
  "figures": [],
  "determinism": null
}
```

This holds no invented numbers. Stage 3's PR replaces it with the Owner's file.

### `src/lmt/eval/readme.py`

Standard library only (no eval extra), so the `readme` job needs no extras.

```python
START, END = "<!-- results:start -->", "<!-- results:end -->"
def render(results: dict) -> str
def region(text: str) -> tuple[int, int]        # the span between the markers; InputError if not exactly one pair, in order
def check(readme: Path, results: Path) -> str | None     # None if equal, else a unified diff
def update(readme: Path, results: Path) -> None
```

- **`render`,** for a results file with figures:

  ```
  Measured on <cpu> (<arch>, <memory in GB, 1 decimal> GB, <os>) on <date's day>, at commit `<commit, 12 chars>`, with lmt <lmt_version>.
  Models: ASR `<name>` (`<repository>` at `<revision, 12 chars>`); diarization `<name>` (`<repository>` at `<revision, 12 chars>`).
  Two runs of the CI subset gave identical accuracy figures: <yes|no>.

  | Set | System | WER | DER | RTF |
  | --- | --- | ---: | ---: | ---: |
  | LS full | product | 3.1 % | — | 0.21 |
  ```

  One row per figure, in the file's order. WER and DER as percentages to one decimal place, RTF to two, and `null` as `—`. For the placeholder (no figures), it renders one line: "No full-set results yet. The Owner's run of `lmt eval --set full` fills this table (G1 stage 3)." A results file with `dirty: true` raises `InputError("results/full.json", "made from a dirty working tree; it can't be published")`.
- **`check`:** compares the text between the markers with `render()`, both with leading and trailing newlines stripped.
- **`update`:** replaces that text with `"\n" + render() + "\n"`, writing a temporary file and renaming it.

### `src/lmt/eval/cli.py`

`cli_eval(args)` replaces the stub:
- `--check-readme`: `check(Path("README.md"), Path(args.out) / "full.json")`. A missing or unreadable file, or JSON that doesn't parse, is an `InputError` (3) naming the file. If they differ, it prints the diff to stdout and raises `CheckFailed("README.md", "the results table differs from <path>; run lmt eval --set full --update-readme")` (6).
- `--set`: still `NotBuilt` until stage 2, which also makes `--update-readme` call `update` after the full run.

### `README.md`

A `## Results` section after `## Checks`. It says the table comes from `results/full.json`, regenerated by `lmt eval --set full --update-readme` and checked by `lmt eval --check-readme`, then has the markers with the placeholder's render between them.

### The `readme` job

At tier ≥ 1, after the full `check_readme.py`:

```sh
uv sync --locked
uv run --frozen lmt eval --check-readme
```

### Tests (`tests/test_readme_table.py`)

`render` on a fixed results file with figures against an expected string, and on the placeholder. `lmt eval --check-readme`, run through `cli.main` in a temporary directory: 0 on a freshly updated README; 6 after one figure in the results file changes, with the diff on stdout and one stderr line; 3 when `results/full.json` is missing, when the markers are missing, and for a dirty file. `update` then `check` gives `None`. The repository's own `README.md` and `results/full.json` pass `check`.

**Test of the item:** those tests, and the `readme` job running `lmt eval --check-readme` on the PR.
