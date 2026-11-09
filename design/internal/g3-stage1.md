# Internal design: G3 stage 1 (rename, demo, browser test, packaging)

| Date (PT) | By | Change |
| --- | --- | --- |
| 2026-10-30 | architect, #169 | The builder's report: the Owner's Mac has Chrome 156 but no chromedriver, and Homebrew disabled the `chromedriver` cask on 2026-09-01 (it fails the macOS Gatekeeper check). No browser or driver may be downloaded (#83, answer 8a), and Gatekeeper isn't to be bypassed; cloud sessions have no Chrome either. So the `browser` job moves from 3d into 3a, at tier 2 as before, without its record. The test of each of 3a, 3b and 3c is now a `workflow_dispatch` gate run on the PR's branch with the `browser` job passing, linked on the PR; a local Mac run is welcome but not required. The step asking the Owner for `brew install --cask google-chrome chromedriver` is removed; `conftest.py`'s Mac fallbacks and its fail-not-skip message stay. The headless `currentTime` check with no sound device is now 3b's first dispatched run. 3d keeps the screenshot script, its test and the `criteria-browser` record, so `product.yml`'s `browser` block is built in a chain, 3a → 3d. G3's criteria are unchanged |
| 2026-10-30 | architect, #409 | The Owner's answer 1 on #409 (spec G3 "Terms"). 0d's test compares only the fields that don't depend on the machine, through `machine_independent`: the top-level `schema_version`, `lmt_version`, `source`, `models` and `speakers`, `len(segments)`, and each segment's `speaker` in order. Across machines, word times differed by up to 0.58 s and one segment's text differed, so the masked byte comparison (#452) failed on `main` and was reverted (#494); on one machine, three runs were byte-identical. On a mismatch the test still writes the run's file as the `transcript-fixture` artifact. The committed fixture stays the Mac's file from 0c unless a compared field differs. G3's criteria are unchanged |
| 2026-10-30 | architect, #415 | The builder's report on #485: CI's first real install (gate run 41082832975) failed step 7, 293 of 482 checks, because `uv tool install` chose the runner's Python 3.12.3. That installs the lock's ≥ 3.12 tree (`av` 19.0.2 is the lock's own 3.12 entry, not a fresh resolve), which G1-15 has never vetted: `check_licences.py` knows only 3.11's extension modules, and `av` 19.0.2's new libraries (`libvmaf`) have no entry. `requires-python` becomes `">=3.11,<3.12"`, so the README's command installs the Python CI measures, on any machine, and the `av` and `numpy` pins lose their Python markers (4a1). `check_install.py` step 4 also fails unless the install's Python has `.python-version`'s minor (4a3). The command, `check_readme.py` and step 7 are unchanged: step 7 still checks what actually installed, and the unpinned rest of the tree may move, as the architecture says (4a4). G3's criteria are unchanged |
| 2026-10-30 | architect, #415 | The Owner's answer 1 on #415: G3-7 checks only for `jiwer`, since `pyannote.audio` 3.4.0 brings `pyannote.metrics` into every plain install (`uv.lock`). `check_install.py` step 5 (4a3) checks `jiwer` alone, with `EVAL_EXTRA = ("jiwer",)`. 0b's import hook still blocks both, since `lmt`'s plain modules mustn't import either |
| 2026-10-30 | architect, #409 | The Developer's question on 0d (PR #452). Two `workflow_dispatch` runs of `test-models` on one commit (40998719001, 41003160960) gave transcripts that differ only in each word's `probability` (the first word, "also", has 0.943 in one and 0.959 in the other): CPU inference isn't bit-reproducible across GitHub's runners. 0d's comparison is now byte for byte with every word's `probability` value masked, and a separate check that each such value is a number in [0, 1]. Every time, text, speaker, the `source` and `models` fields, the key order and the formatting still must match Linux's run exactly. No tolerance is set, since two runs can't bound one. The bytes committed from run 40998719001 stay. G3's criteria are unchanged |
| 2026-10-29 | architect, #168 | The Developer's question on 4a1. torch 2.8.0 has no cp314 wheels, so with `torch==2.8.0` `uv lock` fails on the lock's Python 3.14 split. `requires-python` becomes `">=3.11,<3.14"`, which changes none of the lock's versions. `av` and `numpy`, whose lock versions differ by Python, are pinned with the lock's `python_full_version` markers, and `test_packaging.py` checks each platform with each Python the range allows. Reviewer's finding on #454: so `check_install.py` step 4 (4a3) looks up the lock entry for the platform and the installed Python's version, and its unit test covers that. G3's criteria are unchanged |
| 2026-10-29 | architect, #406 | The Developer's question on 0c. In the product's run, the segment at index `n // 2` stays current for 1.42 s, which is too short. Two changes follow. 0c now measures what 3b needs: how long a segment stays current under the page's rule (the next segment's start minus its own start), not its own length, since segments can overlap or have gaps. "The middle" is also now a rule: the first segment from index `n // 2` on that stays current for ≥ 1.6 s and isn't the last. One helper in `tests/fixtures/segments.py`, which 0c adds, works it out at test time, and 0c and 3b both use it. G3's criteria are unchanged |
| 2026-10-29 | architect, #164 review | Reviewer's findings on #404. G1's stage 2 hasn't all merged: P7c (#391) and P13 (#402) are open. A diarizing run writes outside its outputs until P13, so 5a needs P13 for G3-6 and G3-8, and 5a alone waits on stage 2. "What stage 1 takes" is restated at d6d0707. Each item now names its criterion tags (`criteria.md` §1), and each new check writes its record (§3): the `browser` job its own (3d); `check_install.py` `criteria-test-3.json` in the `test` job, whose upload becomes a glob (4a3, 4a4); `check_install.py` and `check_full_install.py` one record per runner in `install-full` (4a3, 4b1, 4b2, 5a). 5a now needs 4a4, which changes the upload test first. A new item, **6**, sets `complete = true` for G3-1 to G3-8 once their checks pass on `main`, as G1's P10 does. 26 S items. G3's criteria are unchanged |
| 2026-10-29 | architect, #164 | The Owner's "Break down L and XL items into S items": the eight items become 25 S items (0a–0d, 1a–1c, 2a1–2a4, 2b1–2b2, 3a–3d, 4a1–4a4, 4b1–4b2, 5a–5b), each with its own files, test, Needs and tier. Needs are now what is really unmerged: G1's stage 2 is on `main`, so "What stage 1 takes from G1's stage 2" states what `main` has. Since `PULL_REQUEST_MAX_TIER = 1`, a PR runs tier 1 only: model and browser tests are the Developer's local run, first confirmed on `main`, and the two items that add a job's first Linux check (0d, 3d) get a `workflow_dispatch` gate run on their branch before merging. The Linux-only fixture comparison skips on macOS. G3-2's `ffmpeg` checks run in `test-models`, the job with `ffmpeg`. 4b's offline phase reads the models snapshot from a file. G3's criteria are unchanged |
| 2026-10-29 | architect, #349 | G1's P6 split into P6a and P6b, and P7 into P7a to P7c (`g1-stage2.md`). The guard and its test are P7a's, and `tests/isolation.py` is P7b's: item 2a, which takes its snapshot, needs P7a and P7b, and item 4b, which keeps its own, needs P7a. `tests/subtitle_checks.py` is P6a's, so items 1 and 4b, which call it, need P6a |
| 2026-10-29 | architect, #289 | G1's stage 2 (`g1-stage2.md`): the network guard and its test are built by G1's P7, with `LMT_NETGUARD_ALLOW`, so item 0 no longer lists them, items 2a and 4b need P7, and every G3 use sets `LMT_NETGUARD_ALLOW=127.0.0.1` |
| 2026-10-29 | architect, #286 | The label pattern ends with `(?![\s\S])`, not `$`, so Python's and ECMA-262's validators agree on a trailing newline |
| 2026-10-28 | architect, #155 | Reviewer's findings on #156: item 3's `lmt rename` writes only the JSON; the network guard allows only `127.0.0.1`; item 4b runs its offline phase as one process inside one namespace, imports `subtitle_checks` lazily, and lists the directories G3-6 compares; the CI cost is corrected to about 960 minutes; `--tag-checkout` takes the README's tag; U+FEFF joins the name tests |
| 2026-10-28 | architect, #155 | First version: phase 3.1's five items, with the CLI wiring and fixtures split out as item 0, the demo split into 2a and 2b, and the full-install script split out as 4b |

This is the detail a Developer or the builder needs to build each of G3 stage 1's items in one run. It works inside `spec/acceptance.md` G3, `design/architecture.md` ("Speaker names (G3, F7)", "Demo (G3, F8)", "Packaging and release (G3, Q5)", "CI"), `design/public-api.md`, the Owner's answers 1a–11a on #83, and `design/internal/g1-stage1.md`. Where this file and those disagree, they win, and this file is the one to fix. The Reviewer reviews this file. The Architect changes it.

## Items, files and order

The design's eight items (0, 1, 2a, 2b, 3, 4a, 4b, 5) were each about 1.5 hours. Each is now split into S items: one Developer (or builder) run and one PR, up to about 45 minutes. A 26th, **6**, marks the registry. The sections below keep their numbers, and each says which S item builds which part.
- **Every test that checks part of a criterion's "How it's checked" column carries its `criterion` marker, in the same PR** (`design/internal/criteria.md` §1). The table's last column names the tags. A test it doesn't name stays untagged: helpers' and fixtures' own tests, the stubs', and checks of what the spec puts in another job (G3-6 is checked in `install-full`, not by 2b's fakes). A check that isn't pytest writes its own record (§3).
- **`cli.py` puts a change in tier 3,** and both `rename` and `demo` need subcommands in it. So 0a wires both commands to stub modules at once, as G1's item 1a did. The rename and demo items then never touch `cli.py`: they run at tier 2, and in parallel.
- **A file that several items build is built in a chain,** never by two open items at once: `rename.py` (0a → 1a → 1b), `demo/server.py` (0a → 2a2 → 2a3 → 2a4), `test_fixture_transcript.py` (0c → 0d), `test_demo_server.py` (2a3 → 3c), `check_full_install.py` (4b1 → 4b2), `pyproject.toml` with `uv.lock` (4a1 → 3a), `product.yml`'s `browser` block (3a → 3d), `tests/test_criteria.py` (4a4 → 5a), and `tests/criteria.toml` with `.github/scripts/test_criteria.py` (3d and 5a → 6).

| Item | What | Needs (unmerged) | Files it creates or changes | Tier | Its test |
| --- | --- | --- | --- | --- | --- |
| **0a** | `lmt rename` and `lmt demo` wired to stubs, with `validate`'s new rules (§0, "`cli.py`") | — | `src/lmt/cli.py`, `src/lmt/errors.py` (`NotBuilt`'s stage), `src/lmt/rename.py` (stub), `src/lmt/demo/__init__.py`, `src/lmt/demo/server.py` (stub), `src/lmt/demo/sample.py` (stub), `tests/test_cli.py`, `.github/scripts/test_tiers.py` | 3 | `test_cli.py`: G1-6's table test with `rename` and `demo`; `--help` for both; each new `validate` rule exits 2 with one line; each stub exits 1 with one line. `test_tiers.py`'s two new cases. `test` job. **Tags:** the table and help tests keep `G1-6` and gain `G3-3`; `rename`'s `validate` test `G1-6`, `G3-3`; `demo`'s `G1-6`, and the `TRANSCRIPT`-with-`--sample` one `G3-4` too. The stub tests are untagged |
| **0b** | The import-graph test (§0, "`tests/test_import_graph.py`") | 0a | `tests/test_import_graph.py` | 2 | Its three checks. `test` job. Untagged |
| **0c** | The transcript and markup fixtures, with the checks that need no model (§0, "The transcript fixture", "The markup fixture") | — | `tests/fixtures/two_speakers.transcript.json`, `tests/fixtures/markup.py`, `tests/fixtures/segments.py`, `tests/test_fixture_transcript.py` | 2 | The fixture loads, names `two_speakers.wav`, and has two speakers. Its first segment, its middle segment (`segments.py`'s rule) and its last segment each stay current for ≥ 1.6 s; `markup_transcript` passes the schema with the two strings. `test` job. Untagged (fixtures' own tests) |
| **0d** | The fixture checked against Linux's product run in the fields that don't depend on the machine (spec G3 "Terms") | 0c | `tests/test_fixture_transcript.py` (the `models` test and `machine_independent`'s test), `tests/fixtures/two_speakers.transcript.json` (a Linux run's file, only if a compared field differs), `.github/workflows/product.yml` (`test-models` block) | 3 | The comparison passing in `test-models` in a `workflow_dispatch` gate run on the PR's branch, after the fixture is taken from that job's artifact if a compared field first differed. Untagged (spec G3 "Terms", not a criterion) |
| **1a** | `rename.py`'s parts: `parse_pair`, `check_name`, `resolve`, `relabel`, `speaker_table` (§1) | 0a | `src/lmt/rename.py` (`cli_rename` still raises `NotBuilt`), `tests/test_rename_core.py` | 2 | `check_name` and the schema's pattern agree both ways; each `resolve` case; the echo of control characters; the table. `test` job. Untagged (helpers' tests; 1b checks them through the command) |
| **1b** | `cli_rename`: G3-1, G3-3 and G1-6 for `rename` (§1) | 1a, 0c | `src/lmt/rename.py`, `tests/test_rename.py` | 2 | §1's G3-1, G3-3 and G1-6 tests, on the fixture. `test` job. **Tags:** the G3-1 tests `G3-1`; the G3-3 cases `G3-3`; the option tests `G1-6`, `G3-3` |
| **1c** | G3-2 with the rename names, and G3-1's model test (§1) | 1b | `tests/test_rename_subtitles.py`, `tests/test_rename_models.py` | 2 | G3-2's parse checks in the `test` job; its `ffmpeg` checks (U+2028 and U+2029 included) and G3-1's model test marked `models`. The PR shows the local `pytest -m models` result; first confirmed on `main`'s `test-models`. **Tags:** G3-2's checks, both jobs', `G3-2`; the model test `G3-1`; the U+2028/U+2029 test untagged (no criterion names it) |
| **2a1** | The page: `src/lmt/demo/static/` (§2a, "The page") | 0a | `src/lmt/demo/static/index.html`, `app.js`, `app.css`, `favicon.svg`, `tests/test_demo_page.py` | 2 | The page's source checks and its DOM contract. `test` job. Untagged (internal; G3-5 is the browser's) |
| **2a2** | Loading a demo: `Demo`, `wav_bytes`, `load` (§2a) | 0a, 0c | `src/lmt/demo/server.py` (`cli_demo` still raises `NotBuilt`), `tests/test_demo_load.py` | 2 | The WAV against `decode`; the audio's default and `--audio`; the errors' subjects; the duration warning. `test` job. Untagged (2a4 checks the errors through the command) |
| **2a3** | The handler: `make_server` and `Handler` (§2a, "The handler") | 2a1, 2a2 | `src/lmt/demo/server.py`, `tests/test_demo_server.py` | 2 | In process: routes, ranges, HEAD, refusals, headers, the live re-read, the port in use, the address. `test` job. **Tags:** `G3-4` |
| **2a4** | The command: `cli_demo` and `DemoProcess` (§2a) | 2a3 | `src/lmt/demo/server.py`, `tests/demo_process.py`, `tests/test_demo_process.py` | 2 | In a subprocess: start and stop, the browser opener, loopback only, the errors' exit codes, and G1-13's checks with the guard and the snapshot. `test` job. **Tags:** `G3-4`; the tests of `--audio`, `--port` and `--no-browser` `G1-6` too |
| **2b1** | `--sample`'s cache: `prepare`, `cache_key` (§2b) | 0a, 0c | `src/lmt/demo/sample.py`, `tests/test_demo_sample.py` | 2 | §2b's first six tests, on fakes. `test` job. **Tags:** the two `offline=True` tests, through `cli.main`, `G1-6` (`--offline`); the rest untagged (G3-6 is `install-full`'s) |
| **2b2** | `lmt demo --sample` end to end, on fakes (§2b) | 2a4, 2b1 | `tests/test_demo_sample_process.py`, `tests/fixtures/sample_fakes/sitecustomize.py` | 2 | §2b's last test. `test` job. **Tags:** `G1-6` (`--sample`); its `TRANSCRIPT`-with-`--sample` check `G3-4` too |
| **3a** | Selenium in the lock, the driver, the page's list, and the `browser` job without its record (§3) | 2a4; after 4a1 (the lock) | `pyproject.toml` (Selenium, the `browser` marker), `uv.lock`, `toolchain.toml` (`[licences]` entries, if any), `tests/browser/conftest.py`, `tests/browser/test_page.py`, `.github/workflows/product.yml` (`browser` block) | 3 | The inventory posted for both platforms; the `browser` job passing in a `workflow_dispatch` gate run on the PR's branch, linked on the PR. **Tags:** `G3-5` |
| **3b** | Playing from a clicked or keyed segment (G3-5) (§3) | 3a | `tests/browser/test_play.py` | 2 | The `browser` job passing in a `workflow_dispatch` gate run on the PR's branch, linked on the PR: the first run of the headless `currentTime` check with no sound device. **Tags:** `G3-5` |
| **3c** | The track after a rename (G3-2's Chrome parse), the markup fixture, and the relabel helper (§3) | 3a, 1b | `tests/browser/test_track.py`, `tests/test_demo_server.py` (the helper) | 2 | The `browser` job passing in a `workflow_dispatch` gate run on the PR's branch, linked on the PR; the `test` job with the helper in the PR. **Tags:** the track test `G3-2`, `G3-5`; the markup test `G3-5` |
| **3d** | The screenshot script, and the `browser` job's screenshot and record steps (§3) | 3b, 3c | `tests/browser/screenshot.py`, `tests/browser/test_screenshot.py`, `.github/workflows/product.yml` (`browser` block: its record and screenshot steps), `tests/criteria.toml` (`jobs`), `.github/scripts/test_criteria.py` (the real registry's `jobs`) | 3 | The `browser` job passing in a `workflow_dispatch` gate run on the PR's branch, with every G3-5 check, G3-2's Chrome comparison, the screenshot artifact and the `criteria-browser` record. `test_screenshot.py` untagged (G3-9 is stage 2's) |
| **4a1** | The pins (§4a) | — | `pyproject.toml` (pins), `uv.lock`, `tests/test_packaging.py` | 3 | `test_packaging.py`; the lock's eight versions unchanged. `test` job. Untagged (G3-7's check is the install, 4a4) |
| **4a2** | `## Install` and its README check (§4a) | — | `README.md`, `.github/scripts/check_readme.py`, `.github/scripts/test_check_readme.py` | 1 | `check_install`'s unit tests and `--print-install`; `check_readme.py --root .` passing. `readme` job. **Tags:** `check_install`'s row in `CHECKS` carries `G3-7`, so the `readme` record has it |
| **4a3** | `check_install.py`, with `--criteria-out` (§4a) | 4a2 | `.github/scripts/check_install.py`, `.github/scripts/test_check_install.py` | 1 | Its unit tests, the record's included. `readme` job |
| **4a4** | The `test` job's install (G3-7 on Linux), and its record (§4a) | 0a, 2a1, 4a1, 4a3 | `.github/workflows/product.yml` (`test` block), `tests/test_criteria.py` (`UploadTest`) | 3 | The install step passing in the PR's `test` job, with its time; `UploadTest` accepting the job's two records, `criteria-test-1.json` and `criteria-test-3.json` |
| **4b1** | `check_full_install.py`: its frame, the online phase and `--criteria-out` (§4b) | — | `.github/scripts/check_full_install.py`, `.github/scripts/test_check_full_install.py` | 1 | Its unit tests on a fake `lmt`, the record's included. `readme` job |
| **4b2** | `check_full_install.py`: the offline phase (§4b) | 4b1 | `.github/scripts/check_full_install.py`, `.github/scripts/test_check_full_install.py` | 1 | Its unit tests on a fake `lmt`, the offline steps' records included. `readme` job |
| **5a** | Builder: `install-full`, with its records (§5) | 1b, 2a4, 2b1, 4a1, 4a3, 4a4, 4b2; **G1's P13 (#402)** | `.github/workflows/install-full.yml`, `.github/workflows/product.yml` (`install-full` block), `tests/criteria.toml` (`jobs`), `.github/scripts/test_criteria.py` (the real registry's `jobs`), `tests/test_criteria.py` (`UploadTest`) | 3 | `install-full` passing on both runners in a `workflow_dispatch` gate run on the PR's branch, with both runners' `criteria-install-full-*` artifacts; `UploadTest` |
| **5b** | Builder: `release.yml` and `release_notes.py` (§5) | 5a | `.github/workflows/release.yml`, `.github/scripts/release_notes.py`, `.github/scripts/test_release_notes.py` | 3 | `test_release_notes.py`; after merging, a `dry_run` on `main` recorded on the item |
| **6** | The registry: `complete = true` for G3-1 to G3-8, once their checks have passed on `main` (§6) | 1c, 2b2, 3d, 5a, each passed on `main` | `tests/criteria.toml`, `.github/scripts/test_criteria.py` | 2 | `tests/test_criteria.py` and `.github/scripts/test_criteria.py`; `criteria.py` on `main`'s latest records gives `pass` for each criterion marked, shown in the PR |

**Order.** An item can start once everything it needs has merged:
1. **Now:** 0a, 0c, 4a1, 4a2 and 4b1.
2. **Then,** as each need merges: 0b, 1a, 2a1 (after 0a); 0d (after 0c); 2a2, 2b1 (after 0a and 0c); 4a3 (after 4a2); 4b2 (after 4b1).
3. 1b (1a); 2a3 (2a1, 2a2); 4a4 (0a, 2a1, 4a1, 4a3).
4. 1c (1b); 2a4 (2a3).
5. 2b2 (2a4, 2b1); 3a (2a4, and after 4a1).
6. 3b (3a); 3c (3a, 1b).
7. 3d (3b, 3c); 5a (1b, 2a4, 2b1, 4a1, 4a3, 4a4, 4b2, and G1's P13, #402).
8. 5b (5a).
9. 6 (1c, 2b2, 3d, 5a), once each one's checks have passed on `main`.

**G1's stage 2 blocks 5a alone.** Two of its items are still open: P7c (#391, PR #400), G1-13's test, which no G3 item uses, and P13 (#402, PR #403). Until P13 merges, a run that diarizes writes matplotlib's font cache and onnxruntime's telemetry files under `HOME` and `XDG_CACHE_HOME` (`g1-stage2.md`, "P13"). 4b's two `--sample` runs then fail their "four fresh directories are still empty" checks, which are G3-6's "neither run writes anything outside `LMT_DATA_DIR`", and G3-8's offline `transcribe` writes there too. 4b1 and 4b2 run on a fake `lmt`, so only 5a's real run needs P13. No other G3 item checks a diarizing run's writes: 2a4's snapshot is of `lmt demo` on a transcript, which loads no model.

The path to G3-5 is the longest: 0a, 2a1, 2a3, 2a4, 3a, 3b, 3d, seven merges in a row.

**Parallel-safe,** by the files in the table:
- **No two items that can be open at once share a file,** except `product.yml`: 0d, 4a4, 3a and 5a each change their own job's block (`test-models`, `test`, `browser`, `install-full`), and so does G2's 3c4 (`test-models`' `timeout-minutes`, if at all; `g2-stage1.md`). Git merges different blocks, so they may run in parallel. 3d changes the `browser` block after 3a has merged, since it needs 3b and 3c, which need 3a. If two of them conflict, the second updates its branch from `main`. 3d and 5a also each add their job to the registry's `jobs` line, in `tests/criteria.toml` and in `.github/scripts/test_criteria.py`'s real-registry test. That is one line in each, so the second to merge updates its branch from `main` and keeps both jobs.
- **3a and 4a1** both change `pyproject.toml` and `uv.lock`, and a lock can't be merged by hand. So 3a starts only after 4a1 has merged, since 4a1 is on G3-7's path. If they ever overlap, the second updates its branch from `main` and runs `uv lock` again; it never merges `uv.lock`'s text.

**Every item's local checks:** `uv run --frozen ruff check`, `uv run --frozen pytest`, and `python3 -I system/gate/generic.py --base origin/main`. An item with a `models` test adds `uv run --frozen pytest -m models`. An item with a `browser` test adds `uv run --frozen pytest -m browser` where its machine has Chrome and a matching chromedriver; that run is welcome but not required (§3).

### How an item's test runs, now that a PR runs tier 1

`.github/scripts/tiers.py` has `PULL_REQUEST_MAX_TIER = 1`: a PR runs only tier 1 (the `readme` and `test` jobs). `test-models` and `browser` run on `main` after the merge, and in a `workflow_dispatch` run, which runs every tier. So, as G1's P6b and P7c do (`g1-stage2.md`):
- **A `models` test** is shown in the PR by the Developer's local run (`uv run --frozen pytest -m models`). It is first confirmed in CI on `main`. A failure there is `sev:1`: revert first, as the next Developer item, then fix the cause.
- **A `browser` test** is shown by a `workflow_dispatch` gate run on the PR's branch in which the `browser` job passes, linked on the PR: 3a, 3b, 3c and 3d each get one before merging. Neither the Owner's Mac nor a cloud session has a driver (§3, "Why not the Mac"), so the runner's headless Chrome is where these tests are shown. After 3a merges, `main`'s `browser` job runs them too; a failure there is `sev:1`, as above.
- **0d** added a job's first Linux check, where the Mac can't stand in for Linux (the fixture is checked against Linux's product run), and got a `workflow_dispatch` gate run on its branch. So does 5a, whose `install-full` runs only that way. No Developer run can start one or read its artifacts today: `post.py` has no such command, `post.py gate` shows only the overall result (#218), and `gh run` is denied (#312). So the Developer asks on the item for the builder, who starts the run and posts its result and any artifact the item needs, or passes that to the Owner.
- **A `test` or `readme` job check** runs in the PR, as before.

**CI cost.** The table this replaced assumed tier-2 and tier-3 runs on each PR. Now a PR's runs are tier 1, about 10 minutes each (architecture, "CI"), and 12 once G3-7's install lands in 4a4. Each merge runs its own tier once on `main`. With the architecture's 4 runs per PR, an upper estimate for stage 1:

| What | Count | Minutes |
| --- | --- | --- |
| PR runs, tier 1 | 26 PRs × 4 × ≈ 11 | ≈ 1,140 |
| `main` runs, tier 3 (0a, 0d, 3a, 3d, 4a1, 4a4, 5a, 5b) | 8 × ≈ 38 | ≈ 300 |
| `main` runs, tier 2 (0b, 0c, 1a–1c, 2a1–2a4, 2b1, 2b2, 3b, 3c, 6) | 14 × ≈ 26 | ≈ 360 |
| `main` runs, tier 1 (4a2, 4a3, 4b1, 4b2) | 4 × ≈ 12 | ≈ 50 |
| `workflow_dispatch` runs (0d, 3a, 3b, 3c, 3d, 5a) | 6 × ≈ 38, plus `install-full`'s ≈ 30 | ≈ 260 |

That is about 2,100 minutes, against about 1,100 for the eight items: 26 PRs carry more fixed time than eight, and most of the total is the architecture's 4 runs per PR. The Coordinator plans against the 3,000-minute signal with these figures.

## What stage 1 takes from G1's stage 2

Most of G1's stage 2 has merged: decode, diarization, alignment, the exporters, `transcript.load`, the subtitle checks, the network guard and the file snapshot. None of these blocks a G3 item any more. Two of its items are still open, P7c (#391) and P13 (#402), and only 5a waits on stage 2, for P13 ("Order", above). This table gives what `main` has (at d6d0707), which the items call. Where `main` differs from what this design first assumed, the difference is written here, and the items follow `main`.

| Interface | Used by | On `main` |
| --- | --- | --- |
| **The transcript types** (`lmt.transcript`) | 0c, 1a, 1b, 2a2, 2a3, 2b1 | Frozen dataclasses `Transcript`, `Speaker(id, label)`, `Segment`, `Word` (and `Turn`, which G3 doesn't use). `Transcript.speakers` and `.segments` are tuples. `load(path) -> Transcript` reads, parses and validates the file, and checks that `schema_version`'s major part is 1. Any failure is `InputError(str(path), problem)`. `SCHEMA_VERSION` is `"1.1"`. |
| **The round trip** | 1b, 1c | `load`, then `lmt.export.render`, gives the file's bytes back for a file the JSON exporter wrote: `export/json.py` is `json.dumps(to_dict(t), indent=2, ensure_ascii=False) + "\n"`, and it writes the transcript's own `lmt_version`. |
| **The schema** (`lmt.schema`) | 1a | `validate(doc)` raises `InputError`. `transcript.schema.json` holds the label rule exactly: `"maxLength": 32` and the pattern ending `(?![\s\S])` (#286). So 1a adds nothing to the schema, and no rename item is tier 3. |
| **The exporters** (`lmt.export`) | 1b, 2a3 | `FORMATS`, `render(transcript, fmt)`, and `write(transcript, out_dir, stem, formats, *, overwrite) -> list[Path]`, as assumed. `write` first calls `check`: a missing or unwritable directory is `InputError`, and an existing output without `overwrite` is `UsageError`. It never creates the directory. |
| **The WebVTT visible prefix** | 1b, 1c, 3c | `export/vtt.py` writes `<v José &amp; Ana>José &amp; Ana: text`. |
| **Decode** (`lmt.audio`) | 2a2 | `decode(path) -> numpy.ndarray`, float32, 16 kHz (`SAMPLE_RATE`), mono. Every failure is `InputError`. |
| **The pipeline** (`lmt.pipeline`) | 2b1 | `transcribe(path, *, model=None, offline=False, diarize=True, …) -> Transcript`. 2b1 calls it with `offline=` alone, so the rest are the defaults `lmt transcribe` uses. |
| **The models** (`lmt.models`) | 2b1 | `load_manifest()`, `default_models(manifest)`, and `Model.repository` and `.revision`. |
| **The sample meeting** (`lmt.eval.datasets`) | 2b1 | `sample_meeting(*, offline=False) -> Path` is on `main` (`datasets.py:770`), with the offline error the design gave. Its SHA-256 is `load_manifests(MANIFEST_DIR).datasets[SAMPLE_MEETING].derived_sha256`. So 2b1 doesn't change `datasets.py`, and stays tier 2. `score.py` imports `jiwer` and `pyannote` inside its functions, so `datasets.py`'s `from lmt.eval.score import Item, Turn` brings in no `eval` extra. 0b's test keeps it so. |
| **The subtitle checks** (G1's P6a) | 1c, 4b1, 4b2 | `tests/subtitle_checks.py`: `check_srt(path)` and `check_vtt(path)` parse strictly and then run the `ffmpeg` re-encode, which fails (never skips) when `ffmpeg` isn't on `PATH`. **Only `test-models` installs `ffmpeg`;** the `test` job doesn't. So 1c's tests that call `check_srt` and `check_vtt` are marked `models`, and the `test` job keeps no `ffmpeg` (§1). The Developer's Mac has `ffmpeg`, as P6b's local run needed. |
| **The shared product run** (`tests/conftest.py`) | 0d, 1c | The session fixture `two_speakers_run` runs `lmt transcribe tests/fixtures/two_speakers.wav` with no option, so all four formats, in a fresh directory. It returns a `ProductRun(returncode, stdout, stderr, out_dir)`, not a path: the JSON is `run.out_dir / "two_speakers.json"`. |
| **The file snapshot** (G1's P7b) | 2a4 | `tests/isolation.py`: `snapshot(*dirs)` maps each path to `("file", size, sha256)`, `("dir",)` or `("link", target)`. 2a4 makes the fresh `HOME`, `TMPDIR`, `XDG_CACHE_HOME` and working directory itself, in `DemoProcess`. |
| **The network guard** (G1's P7a) | 2a4, 4b2 | `tests/netguard/sitecustomize.py`, active only when `LMT_NETGUARD_LOG` is set, allowing the hosts in `LMT_NETGUARD_ALLOW` (comma-separated, none by default). G3 sets `LMT_NETGUARD_ALLOW=127.0.0.1`. Its test is P7a's `tests/test_netguard.py`. |
| **The CLI table test** (G1-6) | 0a | `tests/test_cli.py`'s `documented_options()` skips every `public-api.md` heading that `LATER_GOAL` matches (`(G2)` or `(G3, …)`): "skipped until the item that adds the command removes its goal here". `test_parser_matches_public_api` asserts the exact set of commands. So 0a wires the two commands itself, as below. |
| **`NotBuilt`** (`lmt.errors`) | 0a | `NotBuilt(command)`'s message is `"not built yet (G1 stage 2)"`, and its docstring says it goes when G1's stage 2 closes. `export.render` still raises it for an unknown format. |
| **The tier exceptions** (#107) | 0a | `tiers.py`'s `TIER3_EXCEPT` already has `"src/lmt/rename.py"` and `"src/lmt/demo/"`, and `test_tiers.py` has `rename.py` → 2, `demo/page.html` → 2 and `cli.py` → 3. |
| **The per-criterion record** (`criteria.md`) | every item; 3d, 4a3, 4a4, 4b1, 4b2, 5a, 6 | The `criterion` marker and `--criteria-out` (`tests/conftest.py`). `criteria.py`'s `write_record(path, checks, complete)` takes the job from the file's name, `criteria-<job>[-<n>].json`; `check_readme.py` loads `criteria.py` by path to call it. The registry's `jobs` is `["readme", "test", "test-models", "eval-ci"]`, and the `test` job uploads the single file `criteria-test.json`. `tests/test_criteria.py`'s `UploadTest` requires, for each job in `jobs`, a last step uploading `criteria-<job>` from `criteria-<job>.json`, and `LMT_TIER` on each step that writes it. `.github/scripts/test_criteria.py`'s `test_real_registry_loads` lists `jobs` and the complete criteria. The merge joins one run's files for a job by `(job, run_id, run_attempt)`. |
| **P13** (#402, open) | 5a | Not on `main`: no `ORT_DISABLE_TELEMETRY`, no `MPLCONFIGDIR` handling. A diarizing run writes under `HOME` and `XDG_CACHE_HOME` until it merges. |

## 0. CLI wiring, fixtures and the tier exceptions

**Its S items:** 0a (`cli.py`, the stubs, `NotBuilt`, the tier cases), 0b (the import-graph test), 0c (the fixtures and their checks that need no model), 0d (the Linux comparison). The tier exceptions are already on `main` (#107), and the network guard is G1's P7a, so neither is built here.

### `cli.py` (0a)

Two subcommands, with exactly the options in `public-api.md`:
- **`rename`:** `TRANSCRIPT`; `KEY=NAME`, `nargs="*"`; `-o/--output-dir` (default `None`, meaning the transcript's directory); `-f/--formats`. Handler `lmt.rename:cli_rename`.
- **`demo`:** `TRANSCRIPT`, `nargs="?"`; `--audio FILE`; `--sample`; `--port N` (default 0); `--no-browser`; `--offline`. Handler `lmt.demo.server:cli_demo`.
- **`validate(args)`** gains: `--formats` as for `transcribe`; for `demo`, exactly one of `TRANSCRIPT` and `--sample` (a `UsageError` naming `--sample` when both are given, and naming `TRANSCRIPT` when neither is); `--audio` not with `--sample`; `--port` from 0 to 65535.

**`NotBuilt`** gains an optional stage: `NotBuilt(command, stage="G1 stage 2")`, with the message `f"not built yet ({stage})"`, so `export.render`'s use is unchanged. Its docstring says it goes when the stage it names closes. The stubs raise `NotBuilt("rename", "G3 stage 1")`, `NotBuilt("demo", "G3 stage 1")` and `NotBuilt("demo --sample", "G3 stage 1")`. `lmt.demo.sample`'s stub defines `prepare(*, offline) -> tuple[Path, Path]`, the interface 2a4 calls and 2b1 fills in. `lmt/demo/__init__.py` is empty, apart from its docstring.

**`tests/test_cli.py`:**
- `LATER_GOAL` drops `G3`, so it matches `(G2)` alone, and `test_later_goals_sections_are_skipped` moves the two G3 headings to the list that must not match. `test_parser_matches_public_api`'s set of commands gains `("rename",)` and `("demo",)`. That is G1-6 for both commands, and G3-3's last sentence for `rename`.
- `test_help_exits_0_for_lmt_and_every_subcommand` gains `["rename"]` and `["demo"]`.
- One test per new `validate` rule, each exiting 2 with one `lmt: error:` line naming its option: a bad `--formats` for `rename`; `demo` with both `TRANSCRIPT` and `--sample` (`--sample`), with neither (`TRANSCRIPT`), with `--audio` and `--sample` (`--audio`), and with `--port 65536` and `--port -1` (`--port`).
- Each stub, reached through `cli.main` with valid arguments, exits 1 with one line, `lmt: error: rename: not built yet (G3 stage 1)` and the like.
- `test_help_imports_no_handler_module` also checks that `lmt.rename`, `lmt.demo.server` and `lmt.demo.sample` aren't imported by `--help`.

**`.github/scripts/test_tiers.py`** gains `src/lmt/demo/server.py` → 2 and `src/lmt/demo/static/app.js` → 2. `tiers.py` doesn't change.

**Test of 0a:** the tests above, in the `test` job.

### The transcript fixture (0c, 0d)

`tests/fixtures/two_speakers.transcript.json` is `lmt transcribe tests/fixtures/two_speakers.wav -f json` with the default models, renamed from `two_speakers.json`. Its `source.file` is `two_speakers.wav`, which sits beside it, so `lmt demo` finds the audio by default. It is always a run's output, unchanged: never retyped or edited.

**0c: the fixture, from the Developer's run, and its checks that need no model.**
- The Developer makes the file locally with `uv run --frozen lmt transcribe tests/fixtures/two_speakers.wav -f json -o <a directory>`, on the Mac's verified models. Nothing in G3 that needs no model depends on the platform it came from: every test derives what it expects from the fixture at test time. 0d checks it against Linux's run in the fields that don't depend on the machine, and replaces it only if one of those differs.
- **`tests/fixtures/segments.py`:** the segments that G3-5's "first, middle and last" picks, worked out from the fixture at test time. That way a fixture taken again (by 0d, if a compared field differs, or at `1.0.0`) needs no change to the design.
  - `MIN_CURRENT = 1.6`. G3-5 checks the marked segment 1 s after the click, from as early as 0.05 s before its start. With 1.6 s, the check still has about 0.5 s of margin.
  - `current_span(segments, i) -> float`: how long segment `i` stays current under the page's rule ("The current segment": the last one whose `start` ≤ `currentTime`). It is the earliest `start` among the segments after `i`, minus `segments[i].start`. For the last segment, it is `end − start`, because the audio runs at least to that end. This is the gap to the next start, not the segment's own length: in the product's run, segment 0 lasts 2.78 s, segment 1 starts 2.55 s after it, and segment 11 lasts 1.25 s but stays current for 2.85 s.
  - `play_targets(segments) -> tuple[int, int, int]`: the first segment (0), the middle segment and the last segment (`n − 1`). The middle segment is the first index `i` with `n // 2 ≤ i < n − 1` and `current_span(segments, i) ≥ MIN_CURRENT`. If none exists, it raises `LookupError` with a message naming `n // 2`. In the product's run (21 segments), index 10 stays current for only 1.42 s, so the middle segment is index 11 (35.823 s), near the clip's middle.
- **`tests/test_fixture_transcript.py`,** in the `test` job: the file loads with `lmt.transcript.load`; `source.file` is `two_speakers.wav`; and it has two speakers, `S1` and `S2`. `play_targets` returns three distinct indices without raising, and each of the three segments has `current_span ≥ MIN_CURRENT`, rounded to milliseconds. There is also one test of the helper on a hand-built list of segments: one segment overlaps the next, there is a gap, and the segment at `n // 2` is too short, so the rule skips it. If the fixture fails, the Developer reports it on the item, for the Architect, rather than changing the test.
- **The markup fixture** (below) is 0c's too, with a test that its document passes `lmt.schema.validate` and holds the two strings.

**0d: the fixture checked against Linux's product run in what doesn't depend on the machine** (spec G3 "Terms": "A test in `test-models` checks that it still matches what the product run gives on Linux in everything that doesn't depend on the machine").
- **`tests/test_fixture_transcript.py`** gains a test marked `models`, which compares `two_speakers_run.out_dir / "two_speakers.json"` with the committed file in these fields only, through one helper, `machine_independent(doc: dict) -> dict`, applied to both parsed files:
  - the top-level `schema_version`, `lmt_version`, `source`, `models` and `speakers`, each whole;
  - `len(segments)`;
  - each segment's `speaker`, in order, as a list.

  The two dicts must be equal. Nothing else is compared: no segment's or word's `start`, `end` or `text`, no word's `probability`, and not the key order or the formatting.
  - **Why only these:** CPU inference doesn't give the same output on every machine. On one machine, three runs gave byte-identical JSON. Across machines, word times differed by up to 0.58 s, segment boundaries moved, and one segment read "Hay fever." on one and "Hey, fever." on another. The earlier check, everything but word probabilities (#452), passed on one GitHub runner and failed on `main`'s next run, and was reverted (#494). The fields above were equal in every run measured (21 segments). They still catch a stale fixture: a schema or version change, a model change, or a different speaker split. No G3 test needs Linux's exact times or texts: the rename, demo and browser tests derive what they expect from the fixture as committed, at test time.
  - It is skipped where `sys.platform != "linux"`, with the reason "the fixture is checked against the product run on Linux (spec G3, Terms)". On a mismatch, it still copies the run's whole file into `$LMT_FIXTURE_OUT/two_speakers.transcript.json`, when that is set, and fails with a message naming each field that differs.
- **The `test-models` block** sets `LMT_FIXTURE_OUT: ${{ runner.temp }}/fixture` on its pytest step, and adds a step, `actions/upload-artifact` (the pinned SHA the block already uses), `if: failure()`, with name `transcript-fixture`, that path, and `if-no-files-found: ignore`. It sits just before the `criteria-test-models` upload, which stays last (`criteria.md` §3).
- **The committed fixture stays as it is:** the Mac's run from 0c, which #494 restored. It already equals Linux's runs in every compared field, and the tests that need no model were written and checked against it. Taking a Linux run's file instead would only move times and texts that nothing compares. Before merging, the Developer asks on the item for a `workflow_dispatch` gate run on the PR's branch ("How an item's test runs"). If its `test-models` passes, the fixture stays. Only if a compared field differs does the builder put the artifact's file on the branch unchanged, in a commit that names the run, and make the dispatched run again. It must then pass, 0c's checks included. The PR says which of the two happened.
- **It changes with the version.** The file holds `lmt_version`, so stage 2's version change to `1.0.0` makes this test fail on `main` until the fixture is taken again. That PR takes it the same way, from a dispatched run on its branch.

**Test of 0c:** `test_fixture_transcript.py`'s checks, in the `test` job. **Test of 0d:** the dispatched run's `test-models` passing the comparison, and a test in the `test` job of `machine_independent` on short hand-built documents: two that differ only in a word's `text`, `start` or `probability` and a segment's `start`, `end` or `text` give equal results, and two that differ in a segment's `speaker`, in the number of segments or in `lmt_version` don't. On the Mac, the PR shows the `models` test skipped.

### The markup fixture (0c)

`tests/fixtures/markup.py`: `markup_transcript(doc: dict) -> dict` returns a deep copy whose segment 0 text is `<img src=x onerror="window.__lmtXss=1">` and segment 1 text is `<script>window.__lmtXss=1</script>`. Built from the transcript fixture at test time, so it can't fall out of step with it. It still passes the schema, which limits labels, not text.

### The network guard (G1's P7a, on `main`)

As G3 uses it: `tests/netguard/sitecustomize.py` on `PYTHONPATH` for a subprocess, with `LMT_NETGUARD_LOG` set and `LMT_NETGUARD_ALLOW=127.0.0.1`. A connection to any other address is appended, one line, to the log file, and raises `OSError(errno.ENETUNREACH)`. That is G3-4's "allowing only `127.0.0.1`", and it is stricter than G3-8's "loopback", so one guard serves both. `lmt` itself connects to nothing, and the tests' own clients run outside the guard. A caller that swallows the error is still caught, because the test reads the log. 2a4's G3-4 check and 4b2's G3-8 check use it. Its test is P7a's `tests/test_netguard.py`, and G3 adds no second one.

### `tests/test_import_graph.py` (0b)

The test that makes `rename.py`'s and `demo/`'s tier exceptions safe (architecture, "CI"). It runs in the `test` job.
- **`lmt.eval` reaches neither `rename` nor `demo`.** It parses every `.py` under `src/lmt/` with `ast`, builds the graph of `import` and `from … import` edges between `lmt` modules (relative imports resolved, a package import counting as its `__init__`), and asserts that no module under `lmt.eval` reaches `lmt.rename` or anything under `lmt.demo`. Imports inside functions count, so a lazy import can't hide an edge.
- **The plain install's modules load without the `eval` extra.** In a subprocess, a `sys.meta_path` finder raises `ImportError` for `jiwer`, `pyannote.metrics` and their submodules; then `lmt.cli`, `lmt.rename`, `lmt.demo.server` and `lmt.demo.sample` are imported, and must all load.
- **It checks itself:** a fake package in a temporary directory, with an edge from `eval` to `demo` through a third module, fails the first check.

**Test of 0b:** the three checks above, in the `test` job. The self-check shows the first one can fail. The second runs on the stubs 0a left, and keeps running as 1a, 2a2 and 2b1 replace them.

## 1. `lmt rename`

**Its S items:**
- **1a:** `parse_pair`, `check_name`, `resolve`, `relabel` and `speaker_table`, with `tests/test_rename_core.py`. `cli_rename` still raises 0a's `NotBuilt`.
- **1b:** `cli_rename`, with `tests/test_rename.py`: G3-1, G3-3 and G1-6.
- **1c:** `tests/test_rename_subtitles.py` (G3-2, and the names the spec doesn't test) and `tests/test_rename_models.py`. It adds no product code. If a U+2028 or U+2029 name breaks the subtitles, the item stops for the Architect, as below.

### `src/lmt/rename.py` (1a, 1b)

```python
def parse_pair(arg: str) -> tuple[str, str]        # split at the first "="; UsageError(arg, "expected KEY=NAME")
def check_name(key: str, name: str) -> str          # the trimmed name, or UsageError(key, problem)
def resolve(transcript, pairs) -> dict[str, str]    # speaker id -> new label; UsageError for bad keys
def relabel(transcript, labels: dict[str, str]) -> Transcript   # dataclasses.replace on speakers only
def speaker_table(transcript) -> str
def cli_rename(args) -> int
```

- **`check_name`:** `name.strip()`, then, in this order: empty ("the name is empty"); longer than 32 code points ("the name is N characters; at most 32"); a character in U+0000–U+001F or U+007F–U+009F ("the name has a control character"); one of `<`, `>`, `{`, `}`, `=` ("the name has '<'"). These are exactly the schema's rule: `str.strip()` and the schema's `\s` agree on every character the control ranges don't already exclude. A unit test runs a list of names through both `check_name` and the schema's pattern and asserts they agree, both ways. The list includes U+FEFF at each end of a name: Python's `\s` and `str.strip()` both leave it, so the two agree.
- **The error's subject** is the key, never the name, so a name holding a newline can't split the error line. Text echoed from the user (a key, or an argument without `=`) has its control characters written as `\uXXXX`.
- **`resolve`,** against the transcript as read, before any of this command's renames:
  - a key equal to a speaker's id is that speaker;
  - else a key equal to exactly one speaker's label is that speaker;
  - a key that is the label of several speakers (7a lets names repeat) is `UsageError(key, "is the label of S1 and S3; use an id")`. `public-api.md` doesn't cover this case. This is the Architect's reading of "matched exactly";
  - no match is `UsageError(key, "no speaker has this id or label")`;
  - two pairs that reach the same speaker are `UsageError(key, "names S1 a second time")`.
- **`cli_rename`:**
  1. `transcript = lmt.transcript.load(args.transcript)`. That gives exit 3 for a missing, unreadable, non-JSON or invalid file, or a major version other than 1.
  2. With no pairs: print `speaker_table` to stdout and return 0, writing nothing.
  3. Parse, check and resolve every pair before anything is written, so a bad pair changes nothing.
  4. `paths = lmt.export.write(relabel(...), out_dir, Path(args.transcript).stem, formats, overwrite=True)`, where `out_dir` is `--output-dir` or the transcript's directory. Print each path, one per line, in `--formats` order.
- **`--formats`** is "as for `transcribe`" (`public-api.md`): `rename` writes exactly the formats listed. With `-f srt`, the JSON isn't rewritten, so the names aren't kept in it. This reading follows the option table. The Reviewer may ask for the JSON to be always written instead, which would be a public-API change, for the Owner.
- **`speaker_table`:** tab-separated, a header `ID LABEL SEGMENTS SECONDS FIRST WORDS`, then one line per speaker in `speakers` order. `SECONDS` is the sum of its segments' `end − start`, to one decimal place. `FIRST WORDS` is the first six words of its first segment, with `…` if there are more. A label or word holding a tab is shown with the tab as a space.

### 1a's tests (`tests/test_rename_core.py`, the `test` job, no model)

On small `Transcript` objects the test builds itself, so 1a needs no fixture:
- **`check_name` and the schema agree,** on a list that covers each rule's edge, both ways: every name `check_name` accepts, once trimmed, matches the schema's label pattern and length (read from `lmt/schema/transcript.schema.json`), and every name it refuses fails them. The list includes U+FEFF at each end, U+2028 and U+2029 inside, a 32- and a 33-code-point name, each control range's ends, and each of `<`, `>`, `{`, `}`, `=`. Each refusal's message is the one above, in the order above.
- **`parse_pair`:** split at the first `=`, so `S1=a=b` gives the name `a=b`, which `check_name` then refuses; an argument without `=` is `UsageError` with the argument as subject, its control characters written as `\uXXXX`.
- **`resolve`:** a key by id; by a unique label; a label held by two speakers (`is the label of S1 and S2; use an id`); no match; two pairs reaching one speaker; and a key that is one speaker's id and another's label resolves by id.
- **`relabel`:** only `speakers` changes; `segments` is the same object.
- **`speaker_table`:** the header, one line per speaker, `SECONDS` to one decimal, `FIRST WORDS` cut at six words with `…`, and a tab in a label shown as a space.

**Test of 1a:** those tests, in the `test` job.

### 1b's tests (`tests/test_rename.py`, the `test` job, no model)

Each test copies the transcript fixture into a temporary directory as `two_speakers.json`, so the outputs are `two_speakers.{txt,srt,vtt,json}`. The rename names (spec, G3 "Terms") are the constants `NAME1 = "José & Ana"` and `NAME2 = "Bartholomew J. Fernández-Rodrigo"`, written with precomposed letters, which a test asserts is 32 code points with a space. 1c imports them from this file.

- **G3-1:**
  - `S1=NAME1 S2=NAME2` exits 0, and stdout is the four paths. Each file equals `lmt.export.render(t', fmt)`, where `t'` is the loaded fixture with those labels set directly.
  - Each format shows each name where it shows a label: `[HH:MM:SS] <name>: ` in the text, the `<name>: ` cue prefix in the SRT, `<v José &amp; Ana>José &amp; Ana: ` in the WebVTT, and `speakers[].label` in the JSON.
  - The JSON with `speakers` removed equals the fixture with `speakers` removed, and the ids are unchanged.
  - Renaming back with `"José & Ana=Speaker 1" S2="Speaker 2"`, one key by label and one by id, gives the four files the fixture itself renders to (`lmt.export.render(fixture, fmt)`). 0d's test checks the fixture against `lmt transcribe`'s JSON in the fields that don't depend on the machine, and 1c's model test compares with a real run's files.
  - `S1=" José & Ana "` gives the same bytes as `S1="José & Ana"`.
  - `S1=Alex S2=Alex` exits 0. Both speakers show `Alex`, and the JSON keeps `S1` and `S2`.
  - No pairs: stdout is the table, with the fixture's two speakers, and no file in the directory changes (SHA-256 before and after).
- **G3-3:** one test per case, each checking the exit code, one stderr line starting `lmt: error:` that names the key or file, and every file in the directory unchanged by SHA-256. The cases: `S9=Bob` (2); `Bob` (2); `S1=` and `S1="   "` (2); a 33-code-point name after trimming (2); `S1="a<b"` (2); `S1="a\nb"` (2); a missing transcript (3); a file holding `{` (3); the fixture with a segment's `start` removed (3); the fixture with `schema_version` `"2.0"` (3); `-o` to a read-only directory (3). Plus the ambiguous label (2) and the same speaker twice (2).
- **G1-6:** one test per option: `-o` writes to another directory and leaves the original's files unchanged; `-f txt,json` writes only those two.

**Test of 1b:** those tests, in the `test` job.

### 1c's tests

**`tests/test_rename_subtitles.py`,** on the fixture renamed with the rename names through `lmt rename`, in a temporary directory:
- **G3-2, in the `test` job:** `srt.parse` in strict mode and `webvtt.read` each parse the outputs. In the WebVTT, both the voice tag's annotation and the cue text have `&amp;` and no bare `&`, and after `html.unescape`, `webvtt-py`'s `voice` for each cue equals its speaker's label. Every cue's lines in both formats are at most two, of at most 42 characters, unless a line is a single word.
- **G3-2's `ffmpeg` re-encodes, marked `models`:** `check_srt` and `check_vtt` pass on the same outputs. They need the `ffmpeg` CLI, which only `test-models` installs ("What stage 1 takes from G1's stage 2"), so they run there. They need no model. The marker puts them in the job that has `ffmpeg`, rather than adding `ffmpeg` to the `test` job, which would be a tier-3 workflow change for one check.
- **Names the spec doesn't test, marked `models` for the same reason:** U+2028 and U+2029 pass the rule, which excludes only control characters, but some parsers treat them as line breaks. A test renames to `"A B"` and runs `check_srt` and `check_vtt`. If they fail, the Developer stops and reports it on the item for the Architect, since tightening the rule is a public-API change. The test is never weakened to pass.
- **U+FEFF in the published schema:** ECMA-262's `\s` includes U+FEFF, but Python's doesn't. So a JavaScript validator of the published schema (F3) rejects a label starting or ending with U+FEFF that `rename` accepts. 1c doesn't change the rule. The Architect takes this to the Owner together with the U+2028 result, since either fix changes the schema's pattern.

**`tests/test_rename_models.py`,** marked `models`: from a copy of `two_speakers_run.out_dir`, `lmt rename` with the rename names, then the rename back. Every file then equals the product run's, byte for byte (G3-1's last sentence). Both runs are on one platform, so this holds on the Mac and on Linux alike.

**Test of 1c:** the `test` job's G3-2 checks in the PR; the `models` tests in the Developer's local `uv run --frozen pytest -m models`, shown in the PR; first confirmed on `main`'s `test-models`.

## 2a. `lmt demo`: server and page

**Its S items,** in a chain, since three of them build `server.py`:
- **2a1:** the page, `src/lmt/demo/static/`, with `tests/test_demo_page.py`. No server is needed to check its source.
- **2a2:** `Demo`, `wav_bytes` and `load`, with `tests/test_demo_load.py`. `cli_demo` still raises 0a's `NotBuilt`.
- **2a3:** `make_server` and `Handler`, with `tests/test_demo_server.py`, run in process.
- **2a4:** `cli_demo`, with `tests/demo_process.py` and `tests/test_demo_process.py`, run in a subprocess.

### `src/lmt/demo/server.py` (2a2, 2a3, 2a4)

```python
@dataclass
class Demo:
    transcript: Path
    audio: bytes                 # the whole WAV file
    token: str
    port: int = 0                # set once bound
    last_warning: str | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)

def wav_bytes(samples: numpy.ndarray) -> bytes        # 16-bit PCM, 16 kHz, mono, via the wave module into BytesIO
def load(transcript: Path, audio: Path | None, audio_option: bool) -> Demo
def make_server(demo: Demo, port: int) -> ThreadingHTTPServer
class Handler(BaseHTTPRequestHandler)
def cli_demo(args) -> int
```

- **`load`:** `lmt.transcript.load(transcript)` (exit 3 if invalid). The audio is `--audio`, or `source.file` in the transcript's directory. `lmt.audio.decode` turns it into samples, and `wav_bytes` into a WAV: the samples are clipped to [−1, 1], times 32767, rounded, and written as little-endian `int16`. A decode failure is `InputError`, with subject `--audio <path>` when the option gave the file, and `<path>` with the problem ending "; give the recording with --audio" otherwise. A duration that differs from `source.duration` by more than 1 s prints one `lmt: warning: <audio>: lasts <a> s, but the transcript says <b> s`.
- **The token:** `secrets.token_urlsafe(16)`, 128 bits. It is compared with `hmac.compare_digest`.
- **`make_server`:** `ThreadingHTTPServer(("127.0.0.1", port), Handler)`, with `daemon_threads = True` and the `Demo` on the server object. `EADDRINUSE` is `InputError(f"--port {port}", "already in use")` (exit 3). The bound port goes into `demo.port`.
- **`cli_demo`:**
  1. With `--sample`, `transcript, audio = lmt.demo.sample.prepare(offline=args.offline)`, and the audio counts as given by option.
  2. `load`, then `make_server`.
  3. Print `http://127.0.0.1:<port>/<token>/` to stdout and flush.
  4. Unless `--no-browser`, `webbrowser.open(url)` once.
  5. A SIGTERM handler raises a private `_Stop` exception. `serve_forever()` runs until `KeyboardInterrupt` or `_Stop`, then `server_close()` and return 0. So Ctrl-C exits 0, not 130 (`public-api.md`).
  6. `log_message` is a no-op, so stderr carries only warnings and errors.

### The handler (2a3)

Every response carries `Content-Security-Policy: default-src 'self'`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` and `Cache-Control: no-store`. The checks run in this order, so that a page from another site learns nothing:
1. **`Host`** must equal `127.0.0.1:<port>` or `localhost:<port>`, with `localhost` in any case. Otherwise 403, also when the header is missing.
2. **The method** must be GET or HEAD. `BaseHTTPRequestHandler` answers an unknown method with 501, so `Handler.__getattr__` returns a 405 handler, with `Allow: GET, HEAD`, for any `do_<METHOD>` that isn't defined.
3. **The path's first segment** must be the token. Otherwise 404. The query string is ignored.

Routes, under `/<token>/`:

| Path | Content-Type | Body |
| --- | --- | --- |
| `` (the page) | `text/html; charset=utf-8` | `static/index.html` |
| `app.js`, `app.css`, `favicon.svg` | `text/javascript`, `text/css`, `image/svg+xml` (each with `; charset=utf-8`) | the static file |
| `transcript.json` | `application/json` | the file's bytes, once `lmt.transcript.load` accepts them |
| `transcript.vtt` | `text/vtt; charset=utf-8` | `lmt.export.vtt.render(load(...))`, UTF-8 |
| `audio.wav` | `audio/wav` | `demo.audio`, with byte ranges |

Anything else under the token is 404. Static files are read with `importlib.resources.files("lmt.demo") / "static"`, so they come from the wheel.

- **Re-reading the transcript** (G3-4): `transcript.json` and `transcript.vtt` each call `lmt.transcript.load` on every request. On `InputError`, the answer is 500 with a `text/plain` body, the error's text. Under `demo.lock`, the warning `lmt: warning: <file>: <problem>` goes to stderr only if it differs from `demo.last_warning`. A good read clears it. So a file that turns invalid gives one line, not one per request, and the line comes again if the file breaks again after a fix.
- **Byte ranges** (audio only): `Accept-Ranges: bytes` on every audio answer. One range of the form `bytes=a-b`, `bytes=a-` or `bytes=-n` gets 206, with `Content-Range: bytes a-b/<total>` and those bytes. `b` beyond the end is cut to the end. A range starting at or beyond the end gets 416, with `Content-Range: bytes */<total>`. A header that doesn't parse, or several ranges, is ignored, and the whole file comes back with 200, which RFC 9110 allows.
- **HEAD** sends the same status and headers as GET, with no body.

### The page (`src/lmt/demo/static/`, 2a1)

Plain HTML, JavaScript and CSS, with no build step, no third-party code, and no inline script or style, which the CSP would block. The browser tests (3a to 3c) rely on these ids and attributes. They are internal, so a later item may change them, with the browser tests, in one PR.

```html
<link rel="icon" href="favicon.svg">           <!-- else Chrome asks for /favicon.ico, gets 404 and logs an error -->
<link rel="stylesheet" href="app.css">
<main>
  <h1>Transcript</h1>
  <p id="error" role="alert" hidden></p>
  <audio id="audio" controls preload="auto" src="audio.wav">
    <track id="track" kind="subtitles" srclang="en" label="Transcript" src="transcript.vtt" default>
  </audio>
  <h2>Speakers</h2>  <ul id="speakers"></ul>
  <h2>Segments</h2>  <ol id="segments"></ol>
</main>
<script src="app.js"></script>
```

`app.js`:
- **Loading:** `fetch("transcript.json", {cache: "no-store"})`. If the answer isn't OK, `#error` shows "The transcript can't be read: " plus the body's text, and is unhidden.
- **Speakers:** one `<li data-speaker="S1">` per speaker, in `speakers` order, reading `<label> · <M:SS>` of speaking time.
- **Segments:** one `<li>` per segment, holding a `<button class="segment" data-index="i" data-start="<start>" data-speaker="<id>">`. The button holds three spans: `.time` (the start as `HH:MM:SS`, rounded down, as the text export writes it), `.speaker` (the label) and `.text`. Every string goes in through `textContent`. `innerHTML`, `insertAdjacentHTML` and `document.write` are never used.
- **Playing:** a button's `click` (which Enter also fires) sets `audio.currentTime = start` and calls `audio.play()`.
- **The current segment:** on `timeupdate` and `seeked`, the current segment is the last one whose `start` ≤ `currentTime`, or none before the first. It gets `aria-current="true"`, every other button loses the attribute, and it is scrolled into view with `{block: "nearest"}`. Using the last start, not `[start, end)`, keeps a segment current through the pause after it.
- **The CSS:** a visible focus outline on buttons, and a distinct background for `[aria-current="true"]`.

### 2a1's tests (`tests/test_demo_page.py`, the `test` job)

- **The page's source:** `index.html` has no `<script>` without `src`, no `style=` attribute, and no URL with a scheme or starting `//`. `app.js` contains none of `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write` and `eval(`.
- **The DOM contract,** read with `html.parser`: `index.html` has the elements above with their ids and attributes (`#error` hidden with `role="alert"`; `#audio` with `src="audio.wav"`; `#track` with `kind="subtitles"`, `src="transcript.vtt"` and `default`; `#speakers`; `#segments`), the icon and stylesheet links, and one `<script src="app.js">`. `favicon.svg` parses as XML. The files are found through `importlib.resources.files("lmt.demo") / "static"`, as the handler reads them.

What `app.js` does in a browser is for 3a to 3c to test. **Test of 2a1:** those tests, in the `test` job.

### 2a2's tests (`tests/test_demo_load.py`, the `test` job)

On the fixture and its clip, copied into a temporary directory:
- **The WAV:** `wave` reads `load(...).audio` as 16 kHz, mono, 16-bit, with as many frames as `decode` gives. `wav_bytes` on samples beyond ±1 gives ±32767.
- **The audio:** with no `--audio`, it is `source.file` beside the transcript; with it, the file named.
- **The errors:** `--audio` naming a missing file is `InputError` with subject `--audio <path>`; the default audio missing is `InputError` with the path, its problem ending "; give the recording with --audio"; an invalid transcript is `InputError`.
- **The duration:** a 1-second WAV, written by the test, with the fixture: one `lmt: warning:` line on stderr, and `load` still returns.
- **The token:** 22 URL-safe characters, different for two loads.

**Test of 2a2:** those tests, in the `test` job.

### 2a3's tests (`tests/test_demo_server.py`, the `test` job)

In process: `make_server(load(...), 0)`, with `serve_forever` on a daemon thread and `shutdown` at the end. Requests use `http.client.HTTPConnection`, so the test sets `Host` and the method itself. The fixture and its clip are copied into a temporary directory.
- **Loopback only:** `server_address[0] == "127.0.0.1"`.
- **Routes:** the page, `app.js`, `app.css` and `favicon.svg` get 200 with their types. `transcript.json` equals the fixture's bytes. `transcript.vtt` equals `export.vtt.render` of the fixture. `audio.wav` equals `demo.audio`. The four security headers are on every answer, the error answers included.
- **Ranges:** `bytes=0-99`, `bytes=1000-`, `bytes=-100` and `bytes=0-<past the end>` give 206 and the bytes that slice gives. `bytes=<total>-` gives 416. `bytes=0-1,5-6` gives 200 and the whole file. A HEAD gives the same headers, with no body.
- **Refusals:** a path without the token, a wrong token, and `/<token>/nothing` give 404. `Host: evil.example:<port>`, `Host: 127.0.0.1:1` and no `Host` give 403. POST, PUT, DELETE, OPTIONS and an invented method, `BREW`, give 405, with `Allow`.
- **Live re-read:** change both labels with `relabel(path, mapping)`, a test helper that writes the JSON alone, through `lmt.export.write(…, ["json"], overwrite=True)`. 3c swaps it for `lmt rename -f json`, which writes the same file; plain `lmt rename` would also write a `.vtt` beside it. Then `transcript.json` and `transcript.vtt` show the new labels, with no `.vtt` file anywhere in the directory. Replace the file with `{`: both routes give 500, and the page still gives 200. stderr (`capfd`) has exactly one `lmt: warning:` line, naming the file. Write the fixture back, and both routes give 200 again.
- **The port in use:** `make_server` on a port the test holds is `InputError` with subject `--port <n>`.

**Test of 2a3:** those tests, in the `test` job.

### 2a4's tests (`tests/test_demo_process.py`, the `test` job)

`tests/demo_process.py` holds `DemoProcess`, a context manager that copies the fixture and the clip into a temporary directory, starts `sys.executable -m lmt demo <args> --no-browser` with fresh `HOME`, `TMPDIR`, `XDG_CACHE_HOME`, working directory and `PYTHONDONTWRITEBYTECODE=1`, and reads the first stdout line within 10 s. It parses the URL as `^http://127\.0\.0\.1:(\d+)/([A-Za-z0-9_-]{22})/$`. On exit it sends SIGINT (or SIGTERM, if asked), waits 10 s, and asserts exit code 0. It takes extra environment variables, which 2b2 uses. 2b2 and 3a import it too.

- **Start and stop:** one URL line within 10 s, and exit 0 on SIGINT and on SIGTERM. Two runs give different tokens.
- **The browser opener:** without `--no-browser`, with `BROWSER` set to `"<python> <recorder.py> %s"`, a script that appends its argument to a file, the file ends with exactly one line, the URL. Python's `webbrowser` reads `BROWSER` on Linux and macOS alike.
- **Loopback only:** a connection to the port on `::1`, and on the machine's first non-loopback IPv4 address if it has one, is refused.
- **Errors, through the command:** `--audio` naming a missing file (3; stderr names the file and `--audio`); the default audio missing (3); an invalid transcript (3); a port already bound by the test (3); `TRANSCRIPT` with `--sample` (2). Each is one `lmt: error:` line. A 1-second WAV with the fixture: one `lmt: warning:` line, and it still serves.
- **No file written, no connection out** (G1-13's checks, once more): with the network guard on `PYTHONPATH`, `LMT_NETGUARD_ALLOW=127.0.0.1` and `LMT_NETGUARD_LOG` set, one run serves every route once and is stopped. Then `tests/isolation.py`'s snapshot of `HOME`, `TMPDIR`, `XDG_CACHE_HOME`, the working directory and the fixture's directory is unchanged, and the guard's log is empty.

**Test of 2a4:** those tests, in the `test` job.

## 2b. `lmt demo --sample`

**Its S items:**
- **2b1:** `prepare` and `cache_key`, with `tests/test_demo_sample.py`, in process. `sample_meeting` is on `main`, so `datasets.py` doesn't change and the item is tier 2.
- **2b2:** the command end to end on fakes, `tests/test_demo_sample_process.py`, through 2a4's `DemoProcess`.

### `src/lmt/demo/sample.py` (2b1)

```python
def prepare(*, offline: bool) -> tuple[Path, Path]     # (transcript, audio), both in LMT_DATA_DIR
def cache_key(audio_sha256: str, models: list[Model]) -> str
```

- **The audio:** `lmt.eval.datasets.sample_meeting`, which is AMI-ci's cropped WAV, verified against `derived_sha256` (G1 design, 5a). `prepare` first calls it with `offline=True`. On `InputError`, under `--offline` it raises it as it is; otherwise it prints the download line below and calls it again with `offline=False`. So the line comes only before a real download. Its SHA-256 is the manifest's (`load_manifests(MANIFEST_DIR).datasets[SAMPLE_MEETING].derived_sha256`), so it isn't hashed again.
- **The key:** the SHA-256 of `"<audio sha256>\n" + "\n".join(f"{m.repository}@{m.revision}" for m in default_models(load_manifest()))`, first 16 hex characters. It is computed from the manifest, so a cache hit loads no model.
- **The cache:** `<LMT_DATA_DIR>/sample/<key>/ES2004a.json`.
  - **A hit** is a file that `lmt.transcript.load` accepts. It is used as is.
  - **A miss,** or a file that fails `load`: `lmt.pipeline.transcribe(audio, offline=offline)`. Its `source.file` is the WAV's name. Then the directory is made (`mkdir(parents=True, exist_ok=True)`, since `write` never creates it) and `lmt.export.write(t, dir, "ES2004a", ["json"], overwrite=True)`, whose temporary-file rename means a stopped run leaves no half-written transcript.
  - **Under `--offline`,** a missing model is `ModelError` (5), as for `transcribe`.
- **On stderr,** one line before the download ("downloading the sample meeting (AMI ES2004a, CC BY 4.0)") and one before transcribing ("transcribing the sample meeting once; later runs use the cache").
- **Imports:** `lmt.pipeline` is imported inside `prepare`, on a miss only, so a hit never loads torch. Nothing from the `eval` extra is imported (0b's test).

### 2b1's tests (`tests/test_demo_sample.py`, the `test` job, no network or model)

`LMT_DATA_DIR` is a temporary directory. `datasets.sample_meeting` is replaced by a function returning a copy of the two-speaker clip (and raising the offline `InputError` when the test says the sample is missing), and `pipeline.transcribe` by one returning the loaded fixture and counting its calls. `load_manifest` is pointed at a small manifest.
- The first `prepare` transcribes once and writes `sample/<key>/ES2004a.json`. The second doesn't call `transcribe`.
- A different model revision in the manifest gives another key, and transcribes again.
- A cached file holding `{` is replaced by a new transcription.
- With `offline=True` and the sample missing, `InputError` with subject `LMT_DATA_DIR` (exit 3 through `cli.main`), and no download line.
- With `offline=True` and a missing model (`transcribe` raises `ModelError`), exit 5.
- Nothing is written outside `LMT_DATA_DIR`: a snapshot of the other temporary directories is unchanged.

**Test of 2b1:** those tests, in the `test` job.

### 2b2's test (`tests/test_demo_sample_process.py`, the `test` job)

`lmt demo --sample --no-browser`, run as `DemoProcess` with `PYTHONPATH` pointing at `tests/fixtures/sample_fakes/`, whose `sitecustomize.py` installs the two replacements above in the child (the clip as the sample, the fixture as the transcription). It serves the page, `transcript.json` equal to the cached transcript's bytes, and `audio.wav`, and exits 0 on SIGINT. A second run finds the cache: the fake `transcribe` counts its calls in a file the test names, and the count stays 1. `TRANSCRIPT` with `--sample` still exits 2.

G3-6 itself, with the real download and models, is 4b1's script in 5a's `install-full`.

**Test of 2b2:** that test, in the `test` job.

## 3. The browser test

**Its S items:**
- **3a:** Selenium in the lock and the licence inventory, the `browser` marker, the driver (`tests/browser/conftest.py`), `tests/browser/test_page.py` (the list, the origin and the console), and the `browser` job without its record.
- **3b:** `tests/browser/test_play.py`: clicking and the keyboard (G3-5).
- **3c:** `tests/browser/test_track.py`: the track after a rename (G3-2's Chrome parse) and the markup fixture (G3-5), and the relabel helper in `tests/test_demo_server.py`.
- **3d:** the screenshot script and its test, and the `browser` job's screenshot and record steps.

The `browser` tests run on the runner's headless Chrome, in the `browser` job, from 3a on. The test of each of 3a to 3d is a `workflow_dispatch` gate run on the PR's branch with that job passing, linked on the PR ("How an item's test runs"). A dispatched run runs every tier, so it runs the job though the PR runs tier 1. A local `uv run --frozen pytest -m browser`, on a machine that has Chrome and a matching chromedriver, is welcome in the PR but not required.

**Why not the Mac.** This design first had the Developer's Mac run these tests until 3d, and the Owner install the driver with `brew install --cask google-chrome chromedriver`. Homebrew disabled the `chromedriver` cask on 2026-09-01, since it fails the macOS Gatekeeper check. The Owner's Mac has Chrome but no driver; no browser or driver may be downloaded (#83, answer 8a), and Gatekeeper isn't to be bypassed. Cloud sessions have no Chrome. The runner image provides both ("The driver").

### First step (3a)

Before the PR, as G1's item 1b did, add `selenium>=4.25` to the `dev` group, `uv lock`, and run `check_licences.py --inventory` on both platforms' installs. Post both tables on the item. Selenium's own tree is expected to bring `urllib3`, `trio`, `trio-websocket`, `outcome`, `sniffio`, `sortedcontainers`, `attrs`, `wsproto`, `h11`, `websocket-client`, `certifi`, `PySocks` and `typing_extensions`, all in the classes the Owner accepted (§7). The wheel also carries the Selenium Manager executable (Apache-2.0), which isn't a shared library, so the bundled-library check doesn't see it. The inventory names it all the same. Anything outside the allow list goes to the Owner in one batch, and the item stops before its PR.

The check that headless Chrome on the runner advances `currentTime` while playing with no sound device was to run through a draft PR's `browser` job, and then through 3d's dispatched run. The runner has no sound device, so it is now 3b's first dispatched run, the first to play audio. If it fails there, the Developer reports the flags tried on 3b's item before changing anything in G3-5.

### The driver (`tests/browser/conftest.py`, 3a)

```python
options = webdriver.ChromeOptions()
for a in ("--headless=new", "--window-size=1280,900", "--autoplay-policy=no-user-gesture-required",
          "--mute-audio", "--no-first-run", "--no-default-browser-check"):
    options.add_argument(a)
options.binary_location = chrome_binary()
options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
service = Service(executable_path=chromedriver_path())
```

- **No browser is downloaded** (#83, answer 8a). The runner image provides `google-chrome` and `chromedriver`, at matching versions, with the driver's directory in `CHROMEWEBDRIVER`. With an explicit driver path, Selenium doesn't call Selenium Manager. `conftest.py` also sets `SE_OFFLINE=true` and `SE_AVOID_STATS=true` in `os.environ` (with `setdefault`) before it imports Selenium, so a local run can't download or send usage statistics either. The job sets both as well.
- **Finding them.** `chrome_binary()` is `shutil.which("google-chrome")`, else, on macOS, `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` if it exists. `chromedriver_path()` is `$CHROMEWEBDRIVER/chromedriver` when the variable is set, else `shutil.which("chromedriver")`. The fallbacks are for a Mac that already has Chrome and a driver, whose run can't set an environment variable for one command.
- **Where Chrome or the driver is missing,** the fixture fails with a message naming what it looked for. It doesn't skip, so a job without them fails rather than passing empty. No one is asked to install the driver on a Mac ("Why not the Mac"); the fallbacks stay for a machine that already has one.
- **The marker:** `pyproject.toml`'s `markers` gains `browser: drives headless Chrome (the browser job)`, and `addopts` becomes `-m 'not models and not data and not browser'`.
- **A served page:** a fixture `page(driver, demo_dir, *args)` starts 2a4's `DemoProcess` and opens its URL. 3a to 3d use it.

### The page's tests (marked `browser`)

On the transcript fixture with its clip, through 2a4's `DemoProcess`.

**`tests/browser/test_page.py` (3a):**
- **The list (G3-5):** `#segments .segment` has one button per JSON segment, in order. Each one's `.time`, `.speaker` and `.text` equal the segment's `start` as `HH:MM:SS`, its speaker's label, and its text. `#speakers li` lists each label.
- **Its own origin, and no errors (G3-5):** `performance.getEntriesByType("navigation")` and `("resource")` each have a `name` starting with the page's origin. `driver.get_log("browser")` has no entry at level `SEVERE`.

**Test of 3a:** the inventory posted on the item for both platforms; a `workflow_dispatch` gate run on the PR's branch in which the `browser` job passes `test_page.py`, linked on the PR; and the `test` job passes in the PR.

**`tests/browser/test_play.py` (3b):**
- **Clicking (G3-5):** for the first, the middle and the last segment, the three indices from `tests/fixtures/segments.py`'s `play_targets` (0c):
  1. Click its button, and poll every 100 ms for up to 2 s until `audio.paused` is false and `currentTime` is between `start − 0.05` and `start + 1.0`.
  2. Read `t₀ = currentTime`, wait 1 s, and assert `currentTime ≥ t₀ + 0.5`.
  3. Assert that exactly that button has `aria-current="true"`.
  4. Pause the audio before the next segment.
- **The keyboard (G3-5):** from the page's start, send Tab until the middle segment's button (`play_targets`' second index) has focus (`document.activeElement`), then Enter. The same checks as for a click.

**Test of 3b:** a `workflow_dispatch` gate run on the PR's branch in which the `browser` job passes `test_play.py`, linked on the PR. It is the runner's case, headless with no sound device ("First step").

**`tests/browser/test_track.py` (3c):**
- **The track, after a rename (G3-2, G3-5):**
  1. Run `lmt rename -f json` on the served copy with the rename names, and reload the page. The list and `#speakers` show the new names.
  2. Wait until `track.readyState === 2`. Read every cue's `startTime`, `endTime` and `getCueAsHTML().textContent` through `execute_script`.
  3. Compare with `webvtt-py`'s parse of `lmt.export.vtt.render(load(copy))`: the same number of cues; the same start and end times, to the millisecond (`round(x * 1000)`); and the same text, `webvtt-py`'s caption text with its tags removed and `html.unescape`d on that side, with lines joined by `\n` on both.
- **The markup fixture (G3-5):** `markup_transcript` of the fixture, written beside the clip and served:
  - segment 0's and 1's `.text` equal their strings exactly, as text;
  - `#segments` holds no `img` or `script` element;
  - `window.__lmtXss` is `undefined` after 1 s.

In `tests/test_demo_server.py`, the `relabel` helper becomes a call to `lmt rename -f json`, now that 1b and 2a3 have landed. The `-f json` keeps the directory free of a `.vtt`, which 2a3's live re-read test asserts (G3-4: "with no `.vtt` beside it").

**Test of 3c:** a `workflow_dispatch` gate run on the PR's branch in which the `browser` job passes `test_track.py`, linked on the PR; and the `test` job passes in the PR with the new helper.

### The screenshot script (`tests/browser/screenshot.py`, 3d)

```
uv run --frozen python tests/browser/screenshot.py (--transcript PATH [--audio PATH] | --sample) --out PATH
```

1. Starts `lmt demo … --no-browser` through `DemoProcess`, and opens Chrome as above, with a window of 1600 × 1000 at a device scale factor of 1.
2. Clicks the segment nearest 40 % of the way through, waits 1.5 s, and pauses, so a segment is marked.
3. Saves `driver.get_screenshot_as_png()`, then reads the PNG's `IHDR` width.
4. Fails, naming the figure, unless the width is from 1,000 to 2,000 pixels and the file is at most 1,000,000 bytes (G3-9). It never shrinks the image to pass.

Stage 2 runs it with `--sample` to make `docs/demo.png`. Here `tests/browser/test_screenshot.py` (marked `browser`) runs `main()` on the fixture, into a temporary file, and checks both figures.

### The `browser` job (`product.yml`, 3a and 3d)

```yaml
browser:
  needs: changes
  if: fromJSON(needs.changes.outputs.tier) >= 2
  runs-on: ubuntu-24.04
  timeout-minutes: 15
  env:
    SE_OFFLINE: "true"
    SE_AVOID_STATS: "true"
  steps:
    - actions/checkout (pinned SHA), persist-credentials: false
    - astral-sh/setup-uv (pinned SHA), version: <toolchain.toml [uv] version>, enable-cache: true
    - run: uv sync --locked --all-extras
    - run: google-chrome --version && "$CHROMEWEBDRIVER/chromedriver" --version
    # 3a: `run: uv run --frozen pytest -m browser`. 3d adds the record's option and LMT_TIER:
    - env:
        LMT_TIER: ${{ needs.changes.outputs.tier }}
      run: uv run --frozen pytest -m browser --criteria-out=criteria-browser.json
    # 3d: the screenshot and the two uploads.
    - run: uv run --frozen python tests/browser/screenshot.py --transcript tests/fixtures/two_speakers.transcript.json --out "$RUNNER_TEMP/demo.png"
    - actions/upload-artifact (pinned SHA), name: demo-screenshot, path: ${{ runner.temp }}/demo.png
    # The job's per-criterion record (design/internal/criteria.md §3); a cancelled run uploads none.
    - if: ${{ !cancelled() }}
      actions/upload-artifact (pinned SHA), name: criteria-browser, path: criteria-browser.json,
        retention-days: 90, if-no-files-found: error
```

**3a** adds the job with its steps up to `pytest -m browser`, without `--criteria-out`, `LMT_TIER` or any upload: the job isn't in the registry's `jobs` yet, so `UploadTest` doesn't check it, and a job without its record mustn't be added there. This is an exception to `design/internal/criteria.md` §3 ("each product job that runs tagged checks uploads one record per run"): from 3a until 3d the job runs `G3-5` and `G3-2` checks without a record, so §3's "`browser` … when they land" means 3d, and until then the merge doesn't count the job's checks: G3-5 shows `no-check`, and G3-2 shows only its `test` and `test-models` checks, so its Chrome comparison counts from 3d. `tiers.py` needs no change: `tests/` is already tier 2 by its paths, `.github/workflows/` tier 3, and a `workflow_dispatch` run runs every tier. **3d** adds the rest. The artifact lets the Reviewer look at the page without running it. **The record:** the pytest step writes `criteria-browser.json` with 3a to 3c's `G3-5` and `G3-2` tags, and its upload is the job's last step, as `UploadTest` requires. 3d adds `"browser"` to `tests/criteria.toml`'s `jobs` and to `.github/scripts/test_criteria.py`'s `test_real_registry_loads`. #300 says `against_base.py` refuses a change to that file; if it isn't fixed by then, the PR says so for the Reviewer, as G1's P10 does. No model is needed, so the job runs at tier 2 (architecture, "CI"): on `main` after each tier-2 or tier-3 merge from 3a on, and in every `workflow_dispatch` run. A PR, at tier 1, doesn't run it.

**Test of 3d:** before merging, a `workflow_dispatch` gate run on the PR's branch ("How an item's test runs"), linked on the PR, in which the `browser` job passes `test_screenshot.py`, every G3-5 check and G3-2's Chrome comparison, on the runner's headless Chrome with no sound device, and uploads the `criteria-browser` record. The builder posts that run's result and its `demo-screenshot` artifact on the item, for the Reviewer.

## 4a. Packaging

**Its S items:**
- **4a1:** the pins and `tests/test_packaging.py`.
- **4a2:** `README.md`'s `## Install`, with `check_readme.py`'s new check and `--print-install`.
- **4a3:** `check_install.py` and its unit tests.
- **4a4:** the `test` job's install step, the first real install.

**Whether the install takes torch's `+cpu` build** on Linux, from the CPU index named in `[tool.uv]`, was a first step before the PR. No Developer run may run `uv tool install`, so it is now read from 4a4's step: `check_install.py` step 4 writes each installed version, with its local label, to the step summary. Either way G3-7 passes, since versions are compared without local labels (architecture, "Packaging and release").

### The pins (`pyproject.toml`, 4a1)

Each of `faster-whisper`, `ctranslate2`, `pyannote.audio`, `torch`, `torchaudio`, `av`, `numpy` and `huggingface-hub` becomes `==<the lock's version>`, without a local label. Under PEP 440, `torch==2.8.0` matches `2.8.0+cpu`. Where the lock gives different public versions on the two platforms, there are two lines, with `; sys_platform == 'linux'` and `; sys_platform == 'darwin'`. Since `requires-python` admits Python 3.11 alone (below), no pin needs a Python marker. The existing bounds on these packages go, since the pin replaces them. Then `uv lock`, which must leave the eight versions where they were.

**`requires-python` is `">=3.11,<3.12"`** (#415). The install is the product a user runs, so it uses the Python everything is measured and vetted on: `.python-version`'s 3.11, which CI's jobs, G1's results and G1-15's licence inventory all use. `uv tool install` picks an interpreter that `requires-python` admits, and downloads one if the machine has none; with the earlier `<3.14` it took the machine's newest Python, which on `ubuntu-24.04` is 3.12 and on a Mac may be Homebrew's 3.13. Python 3.12's tree differs (`av` 19.0.2, `numpy` 2.5.4, `scipy` 1.18.1, and `av`'s new bundled libraries, such as `libvmaf`) and G1-15 has never checked it. Narrowing the range removes only the lock's ≥ 3.12 entries (and `setuptools`, which torch needs only on ≥ 3.12): the 3.11 tree keeps every version (measured with uv 0.13.6, #415). It reads §7's "Python 3.11 or later" as the floor, which `.python-version` and the README's `## Build` meet. The range widens once a newer Python's tree passes G1-15 on both platforms: its libraries listed in `toolchain.toml` (an Owner's question if any licence is off the list), `check_licences.py`'s `EXTENSION_MODULE` taking that Python's `cpython-3NN` tag, and every pinned version having wheels for it.

`tests/test_packaging.py` (the `test` job) reads `pyproject.toml` and `uv.lock` with `tomllib`. For each of the eight, every `[[package]]` entry of that name in the lock must match a pin whose marker covers that entry's environment (each platform with each Python that `requires-python` allows), with the local label dropped. Each must be pinned with `==`. `requires-python` must admit `.python-version`'s minor and no other (3.10, 3.12 and 3.13 checked against it), so the install's Python can't drift from CI's. It also checks that `lmt.__version__` equals `pyproject.toml`'s version.

**Test of 4a1:** `test_packaging.py`, in the `test` job; and the PR says that `uv lock` left the eight versions as they were (`git diff` of `uv.lock` shows no version line of theirs changed).

### `README.md`: `## Install` (4a2)

A new section after `## What it is`, before `## Build`, which is for developers. Stage 2 moves it after `## Results` and `## Demo` (G3-9).

````markdown
## Install

You need [uv](https://docs.astral.sh/uv/getting-started/installation/), installed by its own installer. Nothing else: uv fetches a suitable Python if you don't have one.

```sh
uv tool install git+https://github.com/aray4702/local_meeting_transcriber@v1.0.0
```

The speaker models are gated on Hugging Face. Once, before the first download: make a free account, accept the conditions on the pages of [pyannote/speaker-diarization-3.1](…), [pyannote/segmentation-3.0](…) and [pyannote/wespeaker-voxceleb-resnet34-LM](…), create a read token, and set it as `HF_TOKEN` for `lmt models download`. After that, nothing needs the network.
````

The tag doesn't exist until the release, but CI checks the command against its own checkout's tag (below), and stage 2's release creates it. `lmt models download` stays inline, so the section has exactly one `sh` block. S1-3 runs only `## Build`'s block, so this block isn't run as part of it.

### `check_readme.py` (4a2)

A new check, `check_install`:
- `## Install` appears once, with exactly one `sh` block.
- The block has exactly one line that isn't blank or a comment, and it matches `^uv tool install git\+https://github\.com/aray4702/local_meeting_transcriber@v\d+\.\d+\.\d+$`.
- The section links `https://docs.astral.sh/uv/getting-started/installation/` and names `HF_TOKEN`.

`--print-install` prints that line and exits, for `check_install.py`. Unit tests in `test_check_readme.py` cover each rule, passing and failing.

**Test of 4a2:** those unit tests, in the `readme` job's `unittest discover`, and `check_readme.py --root .` passing on the new README (the `readme` job; locally, `python3 -I .github/scripts/check_readme.py --root .`).

### `.github/scripts/check_install.py` (4a3)

Standard library only. The `test` job runs it (4a4), and so do 5a's `install-full` and 5b's `release.yml`.

```
python3 -I .github/scripts/check_install.py --platform {linux-x86_64,macos-arm64} --scratch DIR
                                            (--readme ROOT [--tag-checkout] | --wheel PATH) [--criteria-out PATH]
```

1. **The command:**
   - With `--readme`, it takes the command from `check_readme.py --print-install`, and replaces `git+https://github.com/aray4702/local_meeting_transcriber@` with `git+file://<ROOT resolved>@`. It rewrites the string rather than using git's `insteadOf`, because uv can resolve a GitHub URL's tag through GitHub's API and skip git. With `--tag-checkout`, it first runs `git -C ROOT tag -f <tag> HEAD`, in that checkout only (spec, G3-7). `<tag>` is the one after `@` in the README's line (`v1.0.0`), not `pyproject.toml`'s version, so the redirected URL resolves. Step 3 still compares `lmt --version` with `pyproject.toml`'s version.
   - With `--wheel`, the command is `uv tool install <wheel>`, for `release.yml`.
2. **A clean environment:** the command runs with `UV_TOOL_DIR=<scratch>/tools`, `UV_TOOL_BIN_DIR=<scratch>/bin`, `UV_CACHE_DIR=<scratch>/cache` (so no cache is reused) and `UV_PYTHON_INSTALL_DIR=<scratch>/python`, and with the working directory `<scratch>`. It must exit 0.
3. **The version:** `<scratch>/bin/lmt --version` prints `lmt <pyproject.toml's version>`.
4. **The pins:** in the tool's environment (`<scratch>/tools/local-meeting-transcriber/`), its Python prints `importlib.metadata.version` of the eight packages and `platform.python_version()`. Each version, without its local label, equals the one in the `uv.lock` entry that applies to the platform *and* that Python version. Since 4a1, `av` and `numpy` have two entries on each platform, chosen by Python version, so the platform alone doesn't decide. An entry applies if it has no `resolution-markers`, or if one of its markers holds for `sys_platform` and `platform_machine` from `--platform` (`linux`/`x86_64`, `darwin`/`arm64`) and `python_full_version` from that Python. The lock's markers are `and`-joined comparisons of those three fields only, so the script evaluates them itself, comparing versions as integer tuples, and stays standard library only. A clause of any other form is `FAIL`, so a new lock shape can't pass unread, and so is a package with no applicable entry or more than one. The step writes the Python version to the step summary with the versions, and fails unless that Python's `major.minor` equals the checkout's `.python-version` (`3.11`), so the install ran on the Python CI measures (#415). G3-7's "the ones `uv.lock` gives for that platform" reads as that platform with the Python the install used.
5. **No `eval` extra:** `jiwer` isn't installed (`EVAL_EXTRA = ("jiwer",)`). `pyannote.metrics` isn't checked: `pyannote.audio` 3.4.0 depends on it with no extra marker (`uv.lock`), so the plain install has it (spec, G3-7; #415).
6. **The modules load:** `import lmt.cli, lmt.rename, lmt.demo.server, lmt.demo.sample` succeeds, and `lmt/demo/static/index.html` is in the installed package.
7. **The licences:** `check_licences.py --site <the tool's site-packages> --platform <platform>` passes (G1-15, on what actually installed).

Each step prints `PASS` or `FAIL` and a line to `GITHUB_STEP_SUMMARY`. It exits 1 if any step fails.

**Its record** (`criteria.md` §3, "A check that isn't pytest"). With `--criteria-out PATH`, after its last step it writes one check per step through `criteria.py`'s `write_record`, loaded by path as `check_readme.py` loads it, with `complete=True`. Each check is named `check_install.py::<platform> <step>` (`check_install.py::linux-x86_64 pins`), so the two runners' checks stay apart when the merge joins them, and carries `["G3-7"]`. A step that passed is `passed` and one that failed is `failed`. A step not reached because an earlier one failed (no install, so no version) is `failed` too, since G3-7 needs every step. The job comes from the file's name: `criteria-test-3.json` in the `test` job (4a4), and `criteria-install-full-<n>.json` in `install-full` (5a). `release.yml` doesn't pass the option, since its run isn't a gate job.

`test_check_install.py` (`unittest`, standard library only) tests the string rewrite, the tag step on a temporary git repository, the label stripping (`2.8.0+cpu` → `2.8.0`), the lock lookup per platform and Python version (on a small lock of its own: `av`-like entries split at `'3.12'`, a `torch`-like one split by platform, one without markers, and `FAIL` for an unknown clause and for no applicable entry), and the steps' `PASS`/`FAIL` report and exit code with the install and the tool's Python replaced by fakes. It also reads the record that run writes: seven checks, each with `G3-7` and the platform in its name, `complete: true`, the job `test` for `criteria-test-3.json`, and `failed` for the steps after a failed install. The install itself is tested by 4a4's job step.

**Test of 4a3:** `test_check_install.py`, in the `readme` job's `unittest discover`.

### The `test` job (4a4)

After its pytest step, and before its upload:

```yaml
- name: The one-command install (G3-7, Linux)
  if: ${{ !cancelled() }}
  env:
    LMT_TIER: ${{ needs.changes.outputs.tier }}
  run: python3 -I .github/scripts/check_install.py --platform linux-x86_64 --scratch "$RUNNER_TEMP/install" --readme . --tag-checkout --criteria-out criteria-test-3.json
```

Step 6 needs `lmt.rename`, `lmt.demo.server`, `lmt.demo.sample` (0a's stubs are enough) and `static/index.html` (2a1), so 4a4 needs 0a and 2a1.

**The job's record becomes two files** (`criteria.md` §3: "A job whose checks span several programs writes one record per program"). The pytest step's `--criteria-out=criteria-test.json` becomes `criteria-test-1.json`, the install step writes `criteria-test-3.json`, and the upload, still named `criteria-test` and still last, takes `path: criteria-test-*.json`. The `-2` is left for `check_results.py`, which §3 already numbers so (G1's stage 3). The install step runs `if: ${{ !cancelled() }}`, so a pytest failure doesn't drop G3-7's checks from the record. If the step ran only after a passing pytest, a pytest failure would leave the install's checks out of that run's record, and the merge would drop them as a deleted test (§4).

**`UploadTest`** (`tests/test_criteria.py`) learns this form. A job's writers are the steps with `--criteria-out[= ]criteria-<job>(-\d+)?\.json`. With one writer, the upload's path is `criteria-<job>.json`, as today. With several, each writes `criteria-<job>-<n>.json` with a distinct `n`, and the upload's path is `criteria-<job>-*.json`. Every writer still sets `LMT_TIER`. A case on a small `product.yml` text with two writers and a glob passes, and one whose upload names a single file fails.

**What step 7 checks** (#415): the licences of what actually installed, as G3-7 and G1-15 say, not of the lock. Only the eight pins are held to the lock (step 4); the rest of the tree resolves fresh within their constraints, as the architecture accepts ("Packaging and release"). On 2026-10-30, with Python 3.11, 1 of 106 installed distributions differed from the lock (`hf-xet` 1.8.0 against 1.7.1), and all seven steps passed. If a later release in that rest bundles a library with no `toolchain.toml` entry, step 7 fails as it should: a user would get that library too. The fix is then an entry for it (the Owner's, if its licence is off the list), or a pin.

**Test of 4a4:** the `test` job's install step passing in the PR, which runs tier 1 and so runs it; `UploadTest` and 4a3's record test, in the PR's jobs. The artifact's two files are #240's to read: no agent run can read an artifact yet (#218). Its time (about 2 minutes, as the architecture estimates) and torch's installed version are in the step summary. No agent run can read a summary yet (#218), so they inform the builder's CI figures and don't decide the test.

## 4b. The full-install sequence (`.github/scripts/check_full_install.py`)

The steps of G3-6 and G3-8 against an installed `lmt`, so that 5a's workflow only calls it. It runs from a checkout with `uv run --frozen`, after the install.

```
uv run --frozen python .github/scripts/check_full_install.py --lmt <scratch>/bin/lmt --platform {linux-x86_64,macos-arm64} --work DIR [--criteria-out PATH]
```

**Its S items,** both tier 1 and both on a fake `lmt`, so neither waits for 2b or 4a; only 5a's real run does:
- **4b1:** the frame (arguments, directories, each command's fresh environment, the module's own snapshot, `run_demo`, the step report and summary), the online phase, and `offline_command()`'s argv. Its `main` runs the online phase alone.
- **4b2:** the `offline` subcommand and its five steps, the outer process's call of it through `offline_command()`, and the check of `offline.json`. `main` then runs both phases.

**Imports.** The module imports only the standard library at the top, so `test_check_full_install.py` can import it in the `readme` job, which runs `python3 -I -m unittest discover -s .github/scripts` with no venv. `tests/subtitle_checks.py` (G1's P6a), which needs `srt` and `webvtt-py`, is imported only inside `subtitle_checkers()`, the one function that uses it. That function first puts the checkout's `tests/` (`Path(__file__).resolve().parents[2] / "tests"`) on `sys.path`. The file snapshot is the module's own, a few lines of `os.walk` and `hashlib`, rather than `tests/isolation.py`'s.

**The directories.** Under `<work>`: `LMT_CACHE_DIR=<work>/models` and `LMT_DATA_DIR=<work>/data` for every command, and `<work>/out` for the transcripts. Every `lmt` command gets its own fresh, empty `HOME`, `TMPDIR`, `XDG_CACHE_HOME` and working directory, under `<work>/runs/<step>/`, as G1-13's do, with `HF_TOKEN` passed to `models download` alone. The tool's own directory isn't compared: Python's bytecode cache goes there, as for any installed program, and G1-13 compares the same set.

**Steps that run `lmt demo`** (`run_demo`), the same online and offline: start it with `subprocess.Popen`, read the first stdout line within the step's limit, and parse the URL as 2a4's `DemoProcess` does. GET the page and `audio.wav` with `http.client` from this same process, each within 10 s, expecting 200 and, for the audio, a body starting `RIFF`. Then `send_signal(SIGTERM)` to the `lmt` process, which is this process's own child, and `wait(10)`. The step passes only if the exit code is 0. A missed limit kills the process with SIGKILL and fails the step, naming the limit.

1. **Online,** in the job's own environment:
   1. `lmt models download` exits 0.
   2. Snapshot `<work>/models`, now that the download has finished, so its own writes don't count. The snapshot is written to `<work>/snapshots/models.json`, the reference for every later `<work>/models` check, the offline phase's included, since that phase is another process (the Reviewer's note on #170).
   3. **G3-6's first run:** `run_demo` on `lmt demo --sample --no-browser`, with a limit of 30 minutes for the URL, since it downloads and transcribes. Afterwards `<work>/data` holds the sample's WAV and one `sample/*/ES2004a.json`. The run's four fresh directories are still empty, and `<work>/models` is unchanged.
2. **Offline.** The script runs this phase as a second process of itself, `python -I check_full_install.py offline …`, with `sys.executable`, so that every command in it, and every fetch, runs in one network namespace:
   - **On Linux,** `offline_command()` gives this argv, so no path passes through a shell string:
     ```
     sudo -n unshare --net -- sh -c 'ip link set lo up && u=$1 g=$2 && shift 2 && exec setpriv --reuid="$u" --regid="$g" --init-groups -- "$@"' \
       sh <uid> <gid> env -i HOME=<work>/runs/offline/home PATH=<the job's PATH> PYTHONDONTWRITEBYTECODE=1 \
       <sys.executable> -I <this script> offline --lmt … --platform … --work …
     ```
     `unshare` without `--fork`, `sh`'s `exec`, `setpriv` and `env` each replace themselves, so the phase's Python runs as the runner's user and is `sudo`'s only child. `sudo` exits with its child's code. The phase's own process starts every `lmt` command as its child, with the environment it builds (the directories above, and the guard's three variables), so neither `sudo`'s reset nor its signal relay is in the way.
   - **On macOS,** the same argv from `env -i` on, with no namespace.
   - **The outer process** waits for the phase with no limit of its own. Every step inside has one, and the job's `timeout-minutes` is the last resort. The phase writes its results to `<work>/offline.json` and exits 0 only if every step passed. The outer process fails the phase if the file is missing, naming the exit code (such as `sudo` failing), or if the exit code and the file disagree.

   Inside the phase, with the network guard (G1's P7a) on `PYTHONPATH`, `LMT_NETGUARD_ALLOW=127.0.0.1` and `LMT_NETGUARD_LOG=<work>/netguard.log` for every `lmt` command:
   1. **On Linux, the cut is real:** `socket.create_connection(("192.0.2.1", 80), timeout=2)` from the phase itself fails with `ENETUNREACH`. Otherwise the phase fails, "the namespace has a route out".
   2. `lmt transcribe <checkout>/tests/fixtures/two_speakers.wav -f txt,srt,vtt,json -o <work>/out` exits 0 within 15 minutes, and `check_srt` and `check_vtt` pass on its files.
   3. `lmt rename <work>/out/two_speakers.json "S1=José & Ana"` exits 0 within 2 minutes.
   4. **G3-6's second run:** snapshot `<work>/data`, then `run_demo` on `lmt demo --sample --no-browser`, with a limit of 10 s for the URL. It has no `--offline`, as in G3-8: the network is simply gone, as when a user turns Wi-Fi off. Afterwards its four fresh directories are still empty, `<work>/data` is unchanged against the snapshot this step took, and `<work>/models` is unchanged against `<work>/snapshots/models.json`. With the 10 s, that shows it served the cache without transcribing again.
   5. The guard's log is empty or absent.

Each step prints `PASS` or `FAIL`, and the outer process writes every step to the step summary, the offline phase's from its file. Exit 1 on any failure.

**Its record** (`criteria.md` §3). With `--criteria-out PATH`, the outer process, after its last check, writes one check per step through `criteria.py`'s `write_record`, loaded by path, with `complete=True`. The offline phase's steps come from `offline.json`. When the file is missing or contradicts the exit code, each offline step is `failed`. Each check is named `check_full_install.py::<platform> <step>` and carries:

| Step | Criteria |
| --- | --- |
| 1.1 `models download` | `G3-8` |
| 1.3 the first `--sample` run | `G3-6` |
| 2.1 the cut is real (Linux) | `G3-8` |
| 2.2 offline `transcribe`, with `check_srt` and `check_vtt` | `G3-8` |
| 2.3 offline `rename` | `G3-8` |
| 2.4 the second `--sample` run | `G3-6`, `G3-8` |
| 2.5 the guard's log | `G3-6`, `G3-8` |

1.2, the snapshot, checks nothing and isn't listed. On macOS, 2.1 doesn't run and isn't listed either: the spec cuts the network with a namespace on Linux only, and the guard is macOS's check. A `skipped` check would leave G3-8 `waiting` for good (§4). Steps not reached because an earlier one failed are `failed`. 4b1 writes the online steps (`main` runs that phase alone); 4b2 adds the offline ones.

`test_check_full_install.py` (`unittest`, standard library only) uses a fake `lmt`, a small Python script that records its arguments, writes placeholder outputs, and for `demo` prints a URL and serves a fixed page and a short `RIFF` body until SIGTERM. It calls the steps in process, with `subtitle_checkers` replaced by a stub. The real run is 5a's first `workflow_dispatch`.
- **4b1's cases:** the online order; `run_demo`'s limits (a fake that never prints its URL, one that ignores SIGTERM) and an exit code other than 0; a file written outside `LMT_DATA_DIR`, or into `<work>/models` after its snapshot; `<work>/snapshots/models.json` written after step 1.2; each command's fresh directories and `HF_TOKEN` passed to `models download` alone; and `offline_command()`'s argv for both platforms, built without running `sudo`; the record from a passing and a failing online run (names, criteria, outcomes, `complete: true`, the job from the file's name).
- **4b2's cases:** the offline steps' order and limits; the Linux probe of step 1, stubbed both ways (refused with `ENETUNREACH`, which passes, and connected, which fails with "the namespace has a route out"; the Reviewer's note on #170); `<work>/models` changed against `snapshots/models.json`; `<work>/data` changed by the second run; a line in the guard's log; and the outer process's check, with `offline.json` missing, contradicting the exit code, and agreeing with it; the record's offline checks in each of those three cases, and no 2.1 check on macOS.

**Test of 4b1 and of 4b2:** each one's cases, in the `readme` job's `unittest discover` (tier 1). Locally, `python3 -I -m unittest discover -s .github/scripts -t .github/scripts`, if the run is allowed it, else the PR's `readme` job.

## 5. Builder: `install-full` and `release.yml`

`.github/workflows/` is the builder's. This is what the product side gives it, and what it needs to do.

**Its S items:**
- **5a:** `install-full.yml` and `product.yml`'s `install-full` job, with their records. It needs 4a3 and 4b2 to run, 4a4 for `UploadTest`'s numbered records, and 0a, 1b, 2a4, 2b1 and 4a1 to pass (the imports, `rename`, `demo`, `--sample` and the pins). It also needs G1's P13 (#402) to pass: until then, `--sample`'s transcription writes under the run's fresh `HOME` and `XDG_CACHE_HOME`, and G3-6's checks fail ("Order").
- **5b:** `release.yml`, with `release_notes.py` and `test_release_notes.py`. It calls 5a's reusable workflow, so it needs 5a.

### From the product side

- **`check_install.py`** (4a3): the install and G3-7's checks, from the README's command (`--readme ROOT --tag-checkout`) or from a wheel (`--wheel PATH`).
- **`check_full_install.py`** (4b1, 4b2): G3-6 and G3-8 after the install. It needs `HF_TOKEN` in its environment, a checkout with `uv sync --locked --all-extras` for `tests/subtitle_checks.py` and `ffmpeg`, and, on Linux, passwordless `sudo`, `unshare`, `setpriv` and `ip`, which GitHub's `ubuntu-24.04` image has.
- **The uv version:** `toolchain.toml`'s `[uv] version`.
- **The results table:** between `README.md`'s `<!-- results:start -->` and `<!-- results:end -->` markers (G1's design, item 6). The install command is `check_readme.py --print-install`'s line.

### `install-full` (`.github/workflows/install-full.yml`, 5a)

A reusable workflow (`workflow_call`, secret `HF_TOKEN`), with one job on a matrix of `ubuntu-24.04` and `macos-15`, `timeout-minutes: 45`, and `permissions: contents: read`. Its steps, in a clean environment (spec, G3 "Terms"): no `actions/cache`, and no `enable-cache` on setup-uv.
1. Install uv at the pinned version, with `astral-sh/setup-uv` (pinned SHA), its version passed in as an input. A first job reads it from `toolchain.toml` in a sparse checkout and outputs it.
2. Check out into `$RUNNER_TEMP/src`, with `persist-credentials: false`. Nothing there is synced before the install, so the checkout is only the git source the README's URL is redirected to. This is the Architect's reading of "no checkout before the install".
3. `check_install.py --platform <platform> --scratch "$RUNNER_TEMP/install" --readme "$RUNNER_TEMP/src" --tag-checkout --criteria-out "$GITHUB_WORKSPACE/criteria-install-full-<i>.json"`.
4. In `$RUNNER_TEMP/src`: `uv sync --locked --all-extras`, then install `ffmpeg` as `test-models`'s "The ffmpeg CLI (G1-4)" step does on Linux, and with Homebrew on macOS if the image lacks it.
5. `check_full_install.py --lmt "$RUNNER_TEMP/install/bin/lmt" --platform <platform> --work "$RUNNER_TEMP/work" --criteria-out "$GITHUB_WORKSPACE/criteria-install-full-<j>.json"`, with `HF_TOKEN` in this step's environment only, and `if: ${{ !cancelled() }}`, so a failed install still records G3-6's and G3-8's checks as failed rather than dropping them.
6. **The record,** last, `if: ${{ !cancelled() }}`: `actions/upload-artifact` (pinned SHA) with `name: criteria-install-full-<platform>`, `path: criteria-install-full-*.json`, `retention-days: 90` and `if-no-files-found: error`.

**The records** (`criteria.md` §3). Each runner writes two files: `<i>`, `<j>` are 1 and 2 on `ubuntu-24.04`, and 3 and 4 on `macos-15`, set in the matrix, so no two files of a run share a name. Each runner uploads its own artifact, since one run's artifact names must differ. The merge joins all four files of the run into one `install-full` record by `(job, run_id, run_attempt)`, as it joins one job's files, and the platform in each check's name keeps the runners' checks apart. Each step that writes a record sets `LMT_TIER` from a `tier` input of the reusable workflow. `product.yml`'s job passes `needs.changes.outputs.tier`, and `release.yml` passes nothing, so its records give `tier: null`.

`product.yml` gains an `install-full` job, `needs: changes`, that `uses: ./.github/workflows/install-full.yml` when `github.event_name == 'workflow_dispatch'`, passing `HF_TOKEN` and the tier. A run of the gate by `schedule` doesn't run it (#83, answer 10a: by hand and at release). A job skipped by its `if` passes, as for the tiers. 5a adds `"install-full"` to `tests/criteria.toml`'s `jobs` and to `.github/scripts/test_criteria.py`'s `test_real_registry_loads` (#300, as in 3d). A run on `main` without `workflow_dispatch` uploads no `install-full` record, so the merge keeps the latest dispatched run's (§4), and gives `null` until there is one.

**`UploadTest`** learns a job that `uses:` a reusable workflow: it reads that file's job steps instead, with the upload's name `criteria-install-full-${{ matrix.platform }}` (or the matrix key 5a names) and its `path` glob, and `LMT_TIER: ${{ inputs.tier }}` on each writer.

**Test of 5a:** before merging, a `workflow_dispatch` gate run on the PR's branch in which `install-full` passes on both runners, with each step's summary posted on the item, and both `criteria-install-full-*` artifacts uploaded. `UploadTest`, in the PR's `test` job.

### `release.yml` (5b)

`workflow_dispatch` with two inputs: `version` (`1.0.0`), and `dry_run` (boolean, default `false`). Without `dry_run` it refuses any ref but `refs/heads/main`. A dry run skips the `draft` job, and its `check` job skips the tag and version tests, so it can run on today's `0.1.0`.
1. **`check`** (`contents: read`, `actions: read`):
   - `pyproject.toml`'s version equals the input.
   - The tag `v<version>` doesn't exist yet.
   - The commit has a successful run of the gate workflow started by `workflow_dispatch`: `gh run list --workflow gate.yml --commit <sha> --event workflow_dispatch --json conclusion`. G3-10 asks for that run, so a run started by a push isn't enough.
2. **`install-full`:** the reusable workflow, on both runners.
3. **`build`** (`contents: read`):
   - `uv build` (sdist and wheel) and `sha256sum * > SHA256SUMS` in `dist/`.
   - `check_install.py --wheel dist/<wheel> --platform linux-x86_64 --scratch …`.
   - `release_notes.py` writes the notes: the install command, then the README's results region exactly as it stands.
   - The three files and the notes are uploaded as an artifact.
4. **`draft`** (`needs: [check, install-full, build]`, `contents: write`, this job only): `gh release create v<version> --draft --target <sha> --title "v<major>.<minor>" --notes-file notes.md dist/*`. The Owner publishes the draft, which creates the tag (G3-10). A draft that already exists for the tag is an error, never overwritten.

`.github/scripts/release_notes.py` (standard library) reads `README.md`, and fails if either the markers or the install line is missing. `.github/scripts/test_release_notes.py` (`unittest`) covers the notes from a sample README, and each of the two failures.

`check_release.py` (G3-10's check of the published release) is stage 2's, not this item's.

**Test of 5b:**
- **Before merging:** `test_release_notes.py`, in the `readme` job.
- **After merging:** GitHub dispatches only workflows that are on the default branch. So the builder records a `dry_run` of `release.yml` on `main` on the item, with its artifact's three files and notes. No draft is created before the release.

## 6. The registry

As G1's P10 does (`g1-stage2.md`, "P10"): `tests/criteria.toml` gains a block with `complete = true` for each of G3-1 to G3-8 whose tagged checks have all passed on `main`, each with a comment naming its tests, as `[G1-1]` and `[G1-2]` have. Until then, G3's criteria show `partial` with every check passing (`criteria.md` §2).

| Criterion | Complete when | Its checks |
| --- | --- | --- |
| G3-1 | 1b and 1c, with `main`'s `test-models` passing `tests/test_rename_models.py` | `tests/test_rename.py`, `tests/test_rename_models.py` |
| G3-2 | 1c and 3c, with `main`'s `test-models` passing 1c's `ffmpeg` checks and its `browser` job passing `tests/browser/test_track.py` (3d) | `tests/test_rename_subtitles.py`, `tests/browser/test_track.py` |
| G3-3 | 0a and 1b | `tests/test_cli.py`, `tests/test_rename.py` |
| G3-4 | 2a3, 2a4 and 2b2 | `tests/test_demo_server.py`, `tests/test_demo_process.py`, `tests/test_demo_sample_process.py`, `tests/test_cli.py` |
| G3-5 | 3a to 3d, with `main`'s `browser` job passing | `tests/browser/test_page.py`, `test_play.py`, `test_track.py` |
| G3-6 | 4b1, 4b2 and 5a, with a `workflow_dispatch` run on `main` whose `install-full` passes on both runners | `check_full_install.py`'s record |
| G3-7 | 4a2, 4a4 and 5a, with `main`'s `test` job and that dispatched run's `install-full` passing | `check_readme.py`'s `check_install` row, `check_install.py`'s records |
| G3-8 | 4b1, 4b2 and 5a, with that dispatched run | `check_full_install.py`'s record |

- **G3-9 and G3-10** are stage 2's: their checks (`check_readme.py`'s lead, `check_release.py`) don't exist yet. G3-5m and G3-8m are already in the registry, with `ci = false`.
- **G1-6** is G1's P10's to mark. Its CI part now includes `rename`'s and `demo`'s options (0a removes G3 from `LATER_GOAL`). If P10 has marked G1-6 by then, item 6 adds 1b's, 2a4's, 2b1's and 2b2's option tests to its comment.
- `.github/scripts/test_criteria.py`'s `test_real_registry_loads` gains the same IDs. #300 applies as for P10.
- If the deadline (2026-10-31) nears first, item 6 marks what has passed, and a second run marks the rest.

**Test of 6:** `tests/test_criteria.py` and `.github/scripts/test_criteria.py`. `criteria.py` on `main`'s latest records then gives `pass` for each criterion marked, and the PR shows that output, as P10's does.
