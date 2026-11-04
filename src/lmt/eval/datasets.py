"""The evaluation data: the manifests, the cache and its fetch, the fixture recipe (design/internal/g1-slice.md,
S1), and the datasets' recipes (design/internal/g1-stage1.md §5a).

Every file that's downloaded is listed in `manifests/sources.toml`, with its SHA-256, and only the archive members
listed there are extracted. A source without members is a single file, kept as it is. `manifests/sets.toml` says
what's built from them. The cache is `<LMT_DATA_DIR>/sources/<source id>/<file or member path>`, and what a
recipe makes is under `<LMT_DATA_DIR>/derived/<dataset name>/`. Nothing here imports the eval extra. The
fixture's encodings are made by ffmpeg, with the arguments in ENCODINGS (design/internal/g1-formats.md).

    python -m lmt.eval.datasets fetch ci
    python -m lmt.eval.datasets build-fixture clip [--write]
    python -m lmt.eval.datasets encode-fixture clip [--write]
    python -m lmt.eval.datasets pin <url> [--member GLOB ...] [--write-members SOURCE_ID]
"""

import argparse
import fnmatch
import hashlib
import http.client
import io
import itertools
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import urllib.parse
import urllib.request
import wave
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import numpy as np
import soundfile

from lmt.errors import InputError, LmtError, UsageError
from lmt.eval.score import Item, Turn

MANIFEST_DIR = Path(__file__).parent / "manifests"
SCHEMA_VERSION = 1
SAMPLE_RATE = 16000
CHUNK = 1 << 20
TIMEOUT = 60  # seconds without data before a download fails
SAMPLE_MEETING = "AMI-ci"  # lmt demo --sample's meeting (design/internal/g3-stage1.md)
KINDS = ("librispeech", "ami", "concat")

# The manifests name only LibriSpeech and AMI sources (design/internal/g1-stage1.md §5a). AMI's RTTMs come from
# BUT's diarization setup, at the one commit the manifests pin. `pin` refuses any other URL, and
# tests/test_manifests.py checks every manifest URL against the same list.
BUT_COMMIT = "2509d8933721023fab4def2618aabd5c28eb82e9"
URL_PREFIXES = (
    "https://www.openslr.org/resources/12/",
    "https://us.openslr.org/resources/12/",
    "https://groups.inf.ed.ac.uk/ami/",
    "https://github.com/aray4702/local_meeting_transcriber/releases/download/sample-data-ami/",  # own copies (#529, #642)
    f"https://raw.githubusercontent.com/BUTSpeechFIT/AMI-diarization-setup/{BUT_COMMIT}/",
)
ARCHIVE_SUFFIXES = (".zip", ".tar.gz", ".tgz", ".tar")
AUDIO_SUFFIXES = (".flac", ".wav")

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_UTTERANCE = re.compile(r"^\d+-\d+-\d+$")

# The arguments after `ffmpeg` for each encoding, in the order they're made (design/internal/g1-formats.md,
# "The recipe"). <wav> is the fixture's absolute path and <out> a temporary file beside it. They're never read
# from the manifest, so the tool can run only these.
_AUDIO_IN = ("-nostdin", "-v", "error", "-y", "-i", "<wav>", "-map", "0:a:0", "-map_metadata", "-1",
             "-fflags", "+bitexact", "-flags:a", "+bitexact", "-threads", "1")
_VIDEO_IN = ("-nostdin", "-v", "error", "-y", "-i", "<wav>", "-f", "lavfi", "-i", "color=c=black:s=320x240:r=1:d=57",
             "-map", "0:a:0", "-map", "1:v:0", "-map_metadata", "-1", "-fflags", "+bitexact",
             "-flags:a", "+bitexact", "-flags:v", "+bitexact", "-threads", "1")
_AAC = ("-c:a", "aac", "-profile:a", "aac_low", "-b:a", "128k", "-ar", "48000", "-ac", "1")
_STILL = ("-c:v", "mpeg4", "-pix_fmt", "yuv420p")
ENCODINGS: dict[str, tuple[str, ...]] = {
    "flac": (*_AUDIO_IN, "-c:a", "flac", "-compression_level", "8", "-sample_fmt", "s16", "-ar", "16000", "-ac", "1",
             "-f", "flac", "<out>"),
    "mp3": (*_AUDIO_IN, "-c:a", "libmp3lame", "-b:a", "128k", "-ar", "44100", "-ac", "1", "-f", "mp3", "<out>"),
    "m4a": (*_AUDIO_IN, *_AAC, "-f", "ipod", "<out>"),
    "mp4": (*_VIDEO_IN, *_AAC, *_STILL, "-max_interleave_delta", "0", "-f", "mp4", "<out>"),
    "mov": (*_VIDEO_IN, *_AAC, *_STILL, "-max_interleave_delta", "0", "-f", "mov", "<out>"),
}


@dataclass(frozen=True)
class Member:
    path: str  # inside the archive, and under the source's cache directory
    sha256: str


@dataclass(frozen=True)
class Source:
    id: str
    urls: tuple[str, ...]
    sha256: str
    size: int
    licence: str
    keep: bool
    members: tuple[Member, ...]


@dataclass(frozen=True)
class Piece:
    """An archive member, or the slice [start, end) seconds of a single-file WAV source."""

    source: str
    member: str | None = None
    start: float | None = None
    end: float | None = None


@dataclass(frozen=True)
class Encoding:
    format: str  # a key of ENCODINGS; the file is the fixture's path with this as its suffix
    sha256: str


@dataclass(frozen=True)
class Fixture:
    name: str
    path: str  # from the repository root
    reference: str
    gap: float  # seconds of zero samples between pieces
    derived_sha256: str
    reference_sha256: str
    concat: tuple[Piece, ...]
    cut: float | None = None  # seconds kept from the start of the joined audio
    ffmpeg: str | None = None  # the version that made the encodings
    encodings: tuple[Encoding, ...] = ()
    rttm: str | None = None  # one SPEAKER line per piece, from the repository root
    rttm_sha256: str | None = None


@dataclass(frozen=True)
class Dataset:
    name: str
    set: str  # "ci" or "full"
    kind: str  # one of KINDS
    source: str | None = None  # librispeech: the archive's source id
    utterances: tuple[str, ...] = ()
    meetings: tuple[str, ...] = ()  # ami: the meetings, each one item
    audio: tuple[str, ...] = ()  # ami: each meeting's audio and RTTM source ids, parallel to meetings
    words: str | None = None  # ami: the annotations archive
    rttm: tuple[str, ...] = ()
    crop: float | None = None  # ami, with one meeting: seconds kept from the start
    derived_sha256: str | None = None  # of the cropped (ami) or joined (concat) WAV
    of: str | None = None  # concat: the ami dataset whose meetings the slices are
    concat: tuple[Piece, ...] = ()  # concat: one slice per meeting of `of`, in its order
    gap: float = 0.0  # concat: seconds of zero samples between pieces
    cut: float | None = None  # concat: seconds kept from the start of the joined audio


@dataclass(frozen=True)
class Manifests:
    sources: dict[str, Source]
    fixtures: dict[str, Fixture]
    datasets: dict[str, Dataset]


def data_dir() -> Path:
    """LMT_DATA_DIR, else ~/.cache/lmt/data."""
    value = os.environ.get("LMT_DATA_DIR")
    return Path(value).expanduser() if value else Path.home() / ".cache" / "lmt" / "data"


# --- The manifests ---------------------------------------------------------------------------------------------


def load_manifests(dir: Path = MANIFEST_DIR) -> Manifests:
    """Both files, with their format checked and every id resolved. A bad manifest raises ValueError."""
    return _load(Path(dir) / "sources.toml", Path(dir) / "sets.toml")


def _load(sources_file, sets_file):
    sources = {}
    for i, entry in enumerate(_read(sources_file).get("source", [])):
        where = f"{sources_file}: source {i + 1}"
        source = Source(
            id=_get(entry, "id", str, where),
            urls=tuple(_get(entry, "urls", list, where)),
            sha256=_hex64(_get(entry, "sha256", str, where), where),
            size=_get(entry, "size", int, where),
            licence=_get(entry, "licence", str, where),
            keep=_get(entry, "keep", bool, where),
            members=tuple(_member(m, f"{where}, member {j + 1}") for j, m in enumerate(entry.get("member", []))),
        )
        if source.id in sources:
            raise ValueError(f"{where}: id {source.id!r} is repeated")
        if not source.urls or not all(isinstance(u, str) and u.startswith("https://") for u in source.urls):
            raise ValueError(f"{where}: urls must be one or more https:// URLs")
        if source.size <= 0:
            raise ValueError(f"{where}: size must be positive")
        if not source.members and not source.keep:
            raise ValueError(f"{where}: a source without members is a single file, so keep must be true")
        sources[source.id] = source

    sets = _read(sets_file)
    fixtures = {}
    for i, entry in enumerate(sets.get("fixture", [])):
        where = f"{sets_file}: fixture {i + 1}"
        cut = entry.get("cut")
        fixture = Fixture(
            name=_get(entry, "name", str, where),
            path=_get(entry, "path", str, where),
            reference=_get(entry, "reference", str, where),
            gap=float(_get(entry, "gap", (int, float), where)),
            derived_sha256=_hex64(_get(entry, "derived_sha256", str, where), where),
            reference_sha256=_hex64(_get(entry, "reference_sha256", str, where), where),
            concat=tuple(_piece(p, sources, where) for p in _get(entry, "concat", list, where)),
            cut=None if cut is None else float(_get(entry, "cut", (int, float), where)),
            **_encodings(entry, where),
            **_rttm(entry, where),
        )
        if fixture.name in fixtures:
            raise ValueError(f"{where}: name {fixture.name!r} is repeated")
        if fixture.gap < 0 or not fixture.concat:
            raise ValueError(f"{where}: gap must be at least 0, and concat must have a piece")
        if fixture.cut is not None and fixture.cut <= 0:
            raise ValueError(f"{where}: cut must be positive")
        if fixture.rttm is not None and not all(_speaker(p) for p in fixture.concat):
            raise ValueError(f"{where}: an rttm needs every piece to be a LibriSpeech utterance's .flac member")
        fixtures[fixture.name] = fixture

    datasets = {}
    for i, entry in enumerate(sets.get("dataset", [])):
        where = f"{sets_file}: dataset {i + 1}"
        dataset = _dataset(entry, sources, where)
        if dataset.name in datasets:
            raise ValueError(f"{where}: name {dataset.name!r} is repeated")
        _check_dataset(dataset, sources, datasets, where)
        datasets[dataset.name] = dataset
    return Manifests(sources=sources, fixtures=fixtures, datasets=datasets)


def _read(path):
    with open(path, "rb") as f:
        data = tomllib.load(f)
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"{path}: schema_version must be {SCHEMA_VERSION}")
    return data


def _get(entry, key, kind, where):
    value = entry.get(key)
    # bool is an int in Python, so a size or gap can't be `true`.
    if not isinstance(value, kind) or (isinstance(value, bool) and kind is not bool):
        raise ValueError(f"{where}: {key} is missing or has the wrong type")
    return value


def _hex64(value, where):
    if not _HEX64.match(value):
        raise ValueError(f"{where}: {value!r} isn't a SHA-256 in lower-case hex")
    return value


def _encodings(entry, where):
    """The fixture's `ffmpeg` and `encodings`, which come together or not at all."""
    if ("ffmpeg" in entry) != ("encodings" in entry):
        raise ValueError(f"{where}: ffmpeg and encodings must be given together")
    if "ffmpeg" not in entry:
        return {}
    encodings = []
    for j, e in enumerate(_get(entry, "encodings", list, where)):
        at = f"{where}, encoding {j + 1}"
        encoding = Encoding(format=_get(e, "format", str, at), sha256=_hex64(_get(e, "sha256", str, at), at))
        if encoding.format not in ENCODINGS:
            raise ValueError(f"{at}: format {encoding.format!r} isn't one of {', '.join(ENCODINGS)}")
        if encoding.format in {x.format for x in encodings}:
            raise ValueError(f"{at}: format {encoding.format!r} is repeated")
        encodings.append(encoding)
    return {"ffmpeg": _get(entry, "ffmpeg", str, where), "encodings": tuple(encodings)}


def _rttm(entry, where):
    """The fixture's `rttm` and `rttm_sha256`, which come together or not at all."""
    if ("rttm" in entry) != ("rttm_sha256" in entry):
        raise ValueError(f"{where}: rttm and rttm_sha256 must be given together")
    if "rttm" not in entry:
        return {}
    return {"rttm": _get(entry, "rttm", str, where),
            "rttm_sha256": _hex64(_get(entry, "rttm_sha256", str, where), where)}


def _speaker(piece):
    """The LibriSpeech speaker id of a piece that is an utterance's .flac member, else None."""
    if piece.member is None:
        return None
    path = PurePosixPath(piece.member)
    return path.stem.split("-")[0] if path.suffix == ".flac" and _UTTERANCE.match(path.stem) else None


def _member(entry, where):
    path = _get(entry, "path", str, where)
    parts = PurePosixPath(path).parts
    # Members are extracted by these paths, so none may leave the source's cache directory.
    if not parts or path.startswith("/") or "\\" in path or any(p in ("", ".", "..") for p in parts):
        raise ValueError(f"{where}: {path!r} isn't a relative path inside the archive")
    return Member(path=path, sha256=_hex64(_get(entry, "sha256", str, where), where))


def _piece(entry, sources, where):
    """{source, member} for an archive member, or {source, start, end} for a slice of a single-file source."""
    source_id = _get(entry, "source", str, where)
    source = sources.get(source_id)
    if source is None:
        raise ValueError(f"{where}: source {source_id!r} isn't in sources.toml")
    if "member" in entry:
        member = _get(entry, "member", str, where)
        if "start" in entry or "end" in entry:
            raise ValueError(f"{where}: a piece is a member or a slice, not both")
        if member not in {m.path for m in source.members}:
            raise ValueError(f"{where}: {member} isn't a member of {source_id}")
        return Piece(source=source_id, member=member)
    start = float(_get(entry, "start", (int, float), where))
    end = float(_get(entry, "end", (int, float), where))
    if source.members:
        raise ValueError(f"{where}: a slice's source {source_id} must be a single file, without members")
    if not 0 <= start < end:
        raise ValueError(f"{where}: a slice needs 0 <= start < end")
    return Piece(source=source_id, start=start, end=end)


def _dataset(entry, sources, where):
    common = {"name": _get(entry, "name", str, where), "set": _get(entry, "set", str, where),
              "kind": _get(entry, "kind", str, where)}
    if common["kind"] == "librispeech":
        source = _get(entry, "source", str, where)
        if "utterances" in entry:
            utterances = _strings(entry, "utterances", where)
        else:  # every .flac member of the source, in sorted id order (LS full, design/internal/g1-stage1.md §5b)
            if source not in sources:
                raise ValueError(f"{where}: source {source!r} isn't in sources.toml")
            utterances = tuple(sorted(_flac_members(sources[source])))
            if not utterances:
                raise ValueError(f"{where}: without utterances, {source} must have .flac members")
        return Dataset(**common, source=source, utterances=utterances)
    if common["kind"] == "ami":
        crop = entry.get("crop")
        sha = entry.get("derived_sha256")
        return Dataset(**common, meetings=_strings(entry, "meetings", where), audio=_strings(entry, "audio", where),
                       words=_get(entry, "words", str, where), rttm=_strings(entry, "rttm", where),
                       crop=None if crop is None else float(_get(entry, "crop", (int, float), where)),
                       derived_sha256=None if sha is None else _hex64(_get(entry, "derived_sha256", str, where),
                                                                     where))
    if common["kind"] == "concat":
        cut = entry.get("cut")
        return Dataset(**common, of=_get(entry, "of", str, where),
                       concat=tuple(_piece(p, sources, where) for p in _get(entry, "concat", list, where)),
                       gap=float(_get(entry, "gap", (int, float), where)),
                       cut=None if cut is None else float(_get(entry, "cut", (int, float), where)),
                       derived_sha256=_hex64(_get(entry, "derived_sha256", str, where), where))
    raise ValueError(f"{where}: kind must be one of {', '.join(KINDS)}")


def _strings(entry, key, where):
    values = _get(entry, key, list, where)
    if not values or not all(isinstance(v, str) for v in values) or len(set(values)) != len(values):
        raise ValueError(f"{where}: {key} must be one or more different strings")
    return tuple(values)


def _check_dataset(dataset, sources, datasets, where):
    if dataset.kind == "concat":
        _check_concat(dataset, datasets, where)
        return
    for source_id in _source_ids(dataset, datasets):
        if source_id not in sources:
            raise ValueError(f"{where}: source {source_id!r} isn't in sources.toml")
    if dataset.kind == "librispeech":
        source = sources[dataset.source]
        listed = {m.path for m in source.members}
        flacs = _flac_members(source)
        for uid in dataset.utterances:
            if not _UTTERANCE.match(uid):
                raise ValueError(f"{where}: {uid!r} isn't a LibriSpeech utterance id")
            flac = flacs.get(uid)
            if flac is None:
                raise ValueError(f"{where}: {uid}.flac isn't a member of {source.id}")
            if str(_trans_member(flac)) not in listed:
                raise ValueError(f"{where}: {_trans_member(flac)} isn't a member of {source.id}")
        return
    if not len(dataset.audio) == len(dataset.rttm) == len(dataset.meetings):
        raise ValueError(f"{where}: audio and rttm must be lists parallel to meetings")
    for source_id in (*dataset.audio, *dataset.rttm):
        if sources[source_id].members:
            raise ValueError(f"{where}: {source_id} must be a single file, without members")
    for meeting in dataset.meetings:
        if not _words_members(sources[dataset.words], meeting):
            raise ValueError(f"{where}: {dataset.words} has no {meeting}.<speaker>.words.xml member")
    if (dataset.crop is None) != (dataset.derived_sha256 is None):
        raise ValueError(f"{where}: crop and derived_sha256 go together")
    if dataset.crop is not None and dataset.crop <= 0:
        raise ValueError(f"{where}: crop must be positive")
    if dataset.crop is not None and len(dataset.meetings) > 1:
        raise ValueError(f"{where}: crop is allowed only with one meeting")


def _check_concat(dataset, datasets, where):
    """A concat dataset joins slices of an ami dataset above it: one per meeting, in its order, each from 0."""
    of = datasets.get(dataset.of)
    if of is None or of.kind != "ami":
        raise ValueError(f"{where}: of must name an ami dataset above it, not {dataset.of!r}")
    if any(p.member is not None for p in dataset.concat):
        raise ValueError(f"{where}: a concat dataset's pieces are slices, {{source, start, end}}")
    if tuple(p.source for p in dataset.concat) != of.audio:
        raise ValueError(f"{where}: concat must be one slice of each of {of.name}'s meetings' audio, in its order")
    if any(p.start != 0 for p in dataset.concat):
        raise ValueError(f"{where}: each slice starts at 0")
    if dataset.gap < 0:
        raise ValueError(f"{where}: gap must be at least 0")
    if dataset.cut is not None and dataset.cut <= 0:
        raise ValueError(f"{where}: cut must be positive")


def _source_ids(dataset, datasets):
    """The sources the dataset's recipe reads. A concat dataset reads only its pieces before the cut, and their
    meetings' annotations and RTTMs."""
    if dataset.kind == "librispeech":
        return (dataset.source,)
    if dataset.kind == "ami":
        return (*dataset.audio, dataset.words, *dataset.rttm)
    of, read = datasets[dataset.of], _read_pieces(dataset)
    return (*(p.source for p, _ in read), of.words, *of.rttm[:len(read)])


def _read_pieces(dataset):
    """(piece, offset in seconds) of a concat dataset's pieces that start before its cut, as `concat` places
    them: in whole samples, with round(gap × 16000) between pieces."""
    gap, at, read = round(dataset.gap * SAMPLE_RATE), 0, []
    for i, piece in enumerate(dataset.concat):
        if i:
            at += gap
        if dataset.cut is not None and at >= round(dataset.cut * SAMPLE_RATE):
            break
        read.append((piece, at / SAMPLE_RATE))
        at += round(piece.end * SAMPLE_RATE) - round(piece.start * SAMPLE_RATE)
    return read


def _flac_members(source):
    """{utterance id: member path} of the source's utterance FLACs, each <...>/<speaker>/<chapter>/<id>.flac."""
    flacs = {}
    for member in source.members:
        path = PurePosixPath(member.path)
        if path.suffix == ".flac" and _UTTERANCE.match(path.stem):
            speaker, chapter, _ = path.stem.split("-")
            if path.parent.parts[-2:] == (speaker, chapter):
                flacs.setdefault(path.stem, path)
    return flacs


def _trans_member(flac):
    speaker, chapter, _ = flac.stem.split("-")
    return flac.parent / f"{speaker}-{chapter}.trans.txt"


def _words_members(source, meeting):
    """(speaker letter, member path) of each of the meeting's words.xml members, by letter."""
    pattern = re.compile(rf"{re.escape(meeting)}\.([A-Z])\.words\.xml")
    found = ((pattern.fullmatch(PurePosixPath(m.path).name), m.path) for m in source.members)
    return sorted((match[1], path) for match, path in found if match)


# --- The fetch -------------------------------------------------------------------------------------------------


def fetch_source(source: Source) -> Path:
    """The source's cache directory, with every listed member in it and verified.

    Members already in the cache are kept if their SHA-256 matches. Otherwise the archive is downloaded (or
    taken from the cache when `keep` is true), verified as a whole, the listed members are extracted, each
    checked against its own hash, and the archive is deleted unless `keep` is true. A source without members
    is a single file (`source_file`), downloaded unless it's in the cache and verified.
    """
    root = data_dir() / "sources" / source.id
    archive = source_file(source)
    missing = [m for m in source.members if not _verified(root / m.path, m.sha256)]
    if source.members and not missing:
        return root
    root.mkdir(parents=True, exist_ok=True)
    if not _verified(archive, source.sha256):
        _download(source, archive)
    try:
        if missing:
            _extract(archive, root, missing)
    finally:
        if not source.keep:
            archive.unlink(missing_ok=True)
    return root


def source_file(source: Source) -> Path:
    """Where the source's downloaded file is cached: its directory, under the first URL's file name."""
    return data_dir() / "sources" / source.id / PurePosixPath(source.urls[0]).name


def _verified(path, sha256):
    """True if the file is there and matches. A file that doesn't match is deleted."""
    if not path.is_file():
        return False
    if _sha256_file(path) == sha256:
        return True
    path.unlink()
    return False


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(CHUNK):
            digest.update(block)
    return digest.hexdigest()


def _download(source, archive):
    """Download to a temporary file beside the archive, check its size and SHA-256, and rename it into place."""
    failure = None
    for url in source.urls:
        fd, part = tempfile.mkstemp(dir=archive.parent, prefix=f".{archive.name}.", suffix=".part")
        os.close(fd)
        part = Path(part)
        try:
            size, sha256 = _save(url, part)
        except InputError as e:
            failure = e
            continue
        if size != source.size:
            part.unlink()
            raise InputError(url, f"size {size} doesn't match the manifest's {source.size}")
        if sha256 != source.sha256:
            part.unlink()
            raise InputError(url, "SHA-256 doesn't match the manifest")
        part.replace(archive)
        return
    raise failure


def _save(url, path):
    """Download `url` to `path`, and return its size and SHA-256. A failed download deletes `path` and raises
    InputError."""
    try:
        digest, size = hashlib.sha256(), 0
        with open(path, "wb") as out, urllib.request.urlopen(url, timeout=TIMEOUT) as response:
            while block := response.read(CHUNK):
                out.write(block)
                digest.update(block)
                size += len(block)
    except (OSError, http.client.HTTPException) as e:  # URLError, HTTPError and timeouts are OSErrors
        path.unlink(missing_ok=True)
        raise InputError(url, f"download failed: {getattr(e, 'reason', e)}") from e
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return size, digest.hexdigest()


def _extract(archive, root, members):
    """Extract each listed member to its listed path, never to a path the archive gives, and check its hash.
    A .zip is read with zipfile, anything else with tarfile."""
    wanted = {m.path: m for m in members}
    try:
        for name, stream in _entries(archive):
            name = name.removeprefix("./")
            member = wanted.pop(name, None)
            if member is None:
                continue
            if stream is None:
                raise InputError(f"{archive}: {name}", "isn't a regular file in the archive")
            _write_member(stream, root / member.path, member.sha256)
            if not wanted:
                break
    except (tarfile.TarError, zipfile.BadZipFile) as e:
        raise InputError(str(archive), f"can't read the archive: {e}") from e
    if wanted:
        raise InputError(str(archive), f"has no member {min(wanted)}")


def _entries(archive):
    """(name, a stream of its bytes, or None if it isn't a regular file) for each entry, in the archive's order."""
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as z:
            for info in z.infolist():
                if info.is_dir():
                    yield info.filename, None
                    continue
                with z.open(info) as stream:
                    yield info.filename, stream
    else:
        with tarfile.open(archive, "r:*") as tar:
            for info in tar:
                yield info.name, tar.extractfile(info) if info.isfile() else None


def _write_member(stream, dest, sha256):
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, part = tempfile.mkstemp(dir=dest.parent, prefix=f".{dest.name}.", suffix=".part")
    part = Path(part)
    try:
        digest = hashlib.sha256()
        with os.fdopen(fd, "wb") as out:
            while block := stream.read(CHUNK):
                out.write(block)
                digest.update(block)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    if digest.hexdigest() != sha256:
        part.unlink()
        raise InputError(str(dest), "SHA-256 doesn't match the manifest")
    part.replace(dest)


# --- The recipe ------------------------------------------------------------------------------------------------


def build_fixture(fixture: Fixture, manifests: Manifests) -> tuple[bytes, str, str | None]:
    """The fixture's WAV bytes, reference text and RTTM text (None without `rttm`), from the sources in the cache.

    A member piece is read as 16-bit samples, which decodes FLAC exactly, and must be 16 kHz mono. A slice is
    read from its single-file WAV source (`slice_wav`). The pieces are joined by `concat`, with the fixture's
    gap and cut, and written as one-channel, 16-bit, 16 kHz WAV by the `wave` module, so the bytes are the same
    on every platform. The reference is each member utterance's line in its chapter's .trans.txt, without the
    id, joined by single spaces, with one final newline. A slice's references are its dataset's, placed with
    `place_references`. The RTTM has one turn per piece, at its offset, by its utterance's speaker (`rttm_text`),
    cropped at the cut as AMI-ci's turns are.
    """
    samples, texts = [], []
    for piece in fixture.concat:
        source = manifests.sources[piece.source]
        if piece.member is None:
            samples.append(slice_wav(source_file(source), piece.start, piece.end))
            continue
        path = data_dir() / "sources" / source.id / piece.member
        data, rate = soundfile.read(path, dtype="int16")
        if rate != SAMPLE_RATE or data.ndim != 1:
            channels = 1 if data.ndim == 1 else data.shape[1]
            raise ValueError(f"{path}: {rate} Hz, {channels} channels; the recipe takes 16 kHz mono")
        samples.append(data)
        texts.append(_transcript(path))
    joined, offsets = concat(samples, fixture.gap, fixture.cut)
    rttm = None
    if fixture.rttm is not None:
        turns = [Turn(at, at + len(s) / SAMPLE_RATE, _speaker(p))
                 for at, s, p in zip(offsets, samples, fixture.concat, strict=True)]
        if fixture.cut is not None:
            _, turns = crop_references([], turns, fixture.cut)
        rttm = rttm_text(Path(fixture.path).stem, turns)
    return _wav_bytes(joined.astype("<i2").tobytes()), " ".join(texts) + "\n", rttm


def rttm_text(file_id: str, turns: list[Turn]) -> str:
    """One `SPEAKER <file_id> 1 <start> <duration> <NA> <NA> <speaker> <NA> <NA>` line per turn, in order, with
    times in seconds to the millisecond (design/internal/g1-stage2.md, "The two-speaker clip's rule")."""
    return "".join(f"SPEAKER {file_id} 1 {t.start:.3f} {t.end - t.start:.3f} <NA> <NA> {t.speaker} <NA> <NA>\n"
                   for t in turns)


def concat(pieces: list[np.ndarray], gap: float, cut: float | None = None) -> tuple[np.ndarray, list[float]]:
    """The pieces' samples joined in order, with round(gap × 16000) zero samples between them, and cut to the
    first round(cut × 16000) samples when `cut` is set; and each piece's offset in the result, in seconds.
    A piece's offset is where it would start even when the cut drops it."""
    silence = np.zeros(round(gap * SAMPLE_RATE), dtype=np.int16)
    joined, offsets, at = [], [], 0
    for i, piece in enumerate(pieces):
        if i:
            joined.append(silence)
            at += len(silence)
        offsets.append(at / SAMPLE_RATE)
        joined.append(piece)
        at += len(piece)
    samples = np.concatenate(joined)
    if cut is not None:
        samples = samples[:round(cut * SAMPLE_RATE)]
    return samples, offsets


def slice_wav(path: Path, start: float, end: float) -> np.ndarray:
    """Frames round(start × 16000) to round(end × 16000) of a 16 kHz, mono, 16-bit WAV, as int16 samples."""
    first, last = round(start * SAMPLE_RATE), round(end * SAMPLE_RATE)
    with wave.open(str(path), "rb") as r:
        if (r.getframerate(), r.getnchannels(), r.getsampwidth()) != (SAMPLE_RATE, 1, 2):
            raise ValueError(f"{path}: {r.getframerate()} Hz, {r.getnchannels()} channels, "
                             f"{8 * r.getsampwidth()}-bit; the recipe takes 16 kHz mono 16-bit")
        if r.getnframes() < last:
            raise ValueError(f"{path}: {r.getnframes() / SAMPLE_RATE} s, shorter than the slice's end, {end} s")
        r.setpos(first)
        return np.frombuffer(r.readframes(last - first), dtype="<i2").astype(np.int16)


def place_references(words, turns, start: float, end: float, offset: float):
    """A slice's references, for the slice [start, end) of its source placed at `offset` in a concatenation.

    Words are kept when their midpoint is inside the slice, and turns when they overlap it, clipped to it. Both
    are shifted by offset − start. A cut then crops the joined references with `crop_references`.
    """
    shift = offset - start
    kept_words = [(s + shift, e + shift, text) for s, e, text in words if start <= (s + e) / 2 < end]
    kept_turns = [Turn(max(t.start, start) + shift, min(t.end, end) + shift, t.speaker)
                  for t in turns if t.start < end and t.end > start]
    return kept_words, kept_turns


def _transcript(flac):
    """The utterance's text: its line in <speaker>-<chapter>.trans.txt beside it, without the id."""
    utterance = flac.stem
    speaker, chapter, _ = utterance.split("-")
    with open(flac.parent / f"{speaker}-{chapter}.trans.txt", encoding="utf-8") as f:
        for line in f:
            uid, _, text = line.rstrip("\n").partition(" ")
            if uid == utterance:
                return text
    raise ValueError(f"{flac.parent}: no transcript line for {utterance}")


# --- The encodings ---------------------------------------------------------------------------------------------


def ffmpeg_version() -> str:
    """The token after "ffmpeg version " on the first line of `ffmpeg -version`."""
    try:
        r = subprocess.run(["ffmpeg", "-version"], check=False, capture_output=True, text=True)
    except FileNotFoundError:
        raise InputError("ffmpeg", "not found on PATH") from None
    first = r.stdout.splitlines()[0] if r.stdout else ""
    if r.returncode != 0 or not first.startswith("ffmpeg version "):
        raise InputError("ffmpeg", "`ffmpeg -version` didn't give its version")
    return first.removeprefix("ffmpeg version ").split()[0]


def encoding_path(fixture: Fixture, fmt: str) -> Path:
    """tests/fixtures/clip.<fmt>: the fixture's path with the format as its suffix, never from the manifest."""
    return Path(fixture.path).with_suffix(f".{fmt}")


def encode(fixture: Fixture, fmt: str, out: Path) -> None:
    """One encoding of the fixture's WAV to `out`, by ENCODINGS[fmt]. A failed ffmpeg raises InputError."""
    wav = str(Path(fixture.path).resolve())
    argv = ["ffmpeg", *(wav if a == "<wav>" else str(out) if a == "<out>" else a for a in ENCODINGS[fmt])]
    try:
        r = subprocess.run(argv, check=False, capture_output=True, text=True)
    except FileNotFoundError:
        raise InputError("ffmpeg", "not found on PATH") from None
    if r.returncode != 0:
        last = (r.stderr.strip().splitlines() or [f"exit status {r.returncode}"])[-1]
        raise InputError(str(encoding_path(fixture, fmt)), f"ffmpeg failed: {last}")


# --- The datasets ----------------------------------------------------------------------------------------------


def fetch(set_name: str) -> list[Item]:
    """Every item of the set's datasets, in sets.toml's order, with its sources fetched and its recipe checked."""
    manifests = load_manifests(MANIFEST_DIR)
    chosen = [d for d in manifests.datasets.values() if d.set == set_name]
    if not chosen:
        names = sorted({d.set for d in manifests.datasets.values()})
        raise UsageError(set_name, f"not a set in sets.toml ({', '.join(names)})")
    for source_id in dict.fromkeys(s for d in chosen for s in _source_ids(d, manifests.datasets)):
        fetch_source(manifests.sources[source_id])
    recipes = {"librispeech": _librispeech, "ami": _ami, "concat": _joined}
    items = []
    for dataset in chosen:
        items += recipes[dataset.kind](dataset, manifests)
    return items


def sample_meeting(*, offline: bool = False) -> Path:
    """AMI-ci's cropped WAV, verified against its derived_sha256. Only its audio source is downloaded.

    Under `offline`, a missing or unverified file is an InputError instead.
    """
    manifests = load_manifests(MANIFEST_DIR)
    dataset = manifests.datasets[SAMPLE_MEETING]
    path = _derived_wav(dataset)
    if _verified(path, dataset.derived_sha256):
        return path
    if offline:
        raise InputError("LMT_DATA_DIR", "the sample meeting isn't downloaded; run once without --offline")
    source = manifests.sources[dataset.audio[0]]
    fetch_source(source)
    return _crop(source_file(source), dataset)


def _librispeech(dataset, manifests):
    """One item per utterance: its FLAC, its duration from the FLAC's header, and its line in .trans.txt."""
    source = manifests.sources[dataset.source]
    flacs = _flac_members(source)
    items = []
    for uid in dataset.utterances:
        path = data_dir() / "sources" / source.id / flacs[uid]
        info = soundfile.info(str(path))
        items.append(Item(dataset.name, uid, path, info.frames / info.samplerate, ref_text=_transcript(path)))
    return items


def _ami(dataset, manifests):
    """One item per meeting: its audio (cropped when `crop` is set), its words as ref_text and its RTTM turns."""
    return [_item(dataset.name, meeting, *_cropped_meeting(dataset, manifests, i))
            for i, meeting in enumerate(dataset.meetings)]


def live_reference(name: str = SAMPLE_MEETING) -> tuple[Item, list[tuple[float, float, str]]]:
    """An ami dataset's first meeting as `fetch` gives it, with the (start, end, text) words its ref_text is
    made from, in the same order and crop (design/internal/g2-stage1.md §5, item 5d). Only that dataset's own
    sources are fetched, so `lmt eval --set live` downloads no LibriSpeech."""
    manifests = load_manifests(MANIFEST_DIR)
    dataset = manifests.datasets[name]
    for source_id in _source_ids(dataset, manifests.datasets):
        fetch_source(manifests.sources[source_id])
    audio, words, turns = _cropped_meeting(dataset, manifests, 0)
    return _item(dataset.name, dataset.meetings[0], audio, words, turns), [w for w in words if w[2]]


def _cropped_meeting(dataset, manifests, i):
    """An ami dataset's i-th meeting's audio, words and turns, cropped when `crop` is set."""
    words, turns = _meeting_references(dataset, manifests, i)
    audio = source_file(manifests.sources[dataset.audio[i]])
    if dataset.crop is not None:
        audio = _crop(audio, dataset)
        words, turns = crop_references(words, turns, dataset.crop)
    return audio, words, turns


def _meeting_references(dataset, manifests, i):
    """The words and turns of an ami dataset's i-th meeting, from the cache."""
    meeting = dataset.meetings[i]
    words_root = data_dir() / "sources" / dataset.words
    words = ami_words([(letter, words_root / path) for letter, path in
                       _words_members(manifests.sources[dataset.words], meeting)])
    return words, rttm_turns(source_file(manifests.sources[dataset.rttm[i]]), meeting)


def _item(name, id, audio, words, turns):
    with wave.open(str(audio), "rb") as w:
        duration = w.getnframes() / w.getframerate()
    return Item(name, id, audio, duration, ref_text=" ".join(text for _, _, text in words if text),
                ref_turns=tuple(turns))


def _joined(dataset, manifests):
    """A concat dataset's one item, derived/<name>/<name>.wav: the slices before the cut joined by `concat` and
    checked against derived_sha256, with each slice's words and turns from its meeting in `of`, placed with
    `place_references` and cropped at the cut as AMI-ci's are."""
    of, read = manifests.datasets[dataset.of], _read_pieces(dataset)
    path = data_dir() / "derived" / dataset.name / f"{dataset.name}.wav"
    if not _verified(path, dataset.derived_sha256):
        content = joined_wav(dataset, manifests)
        digest = hashlib.sha256(content).hexdigest()
        if digest != dataset.derived_sha256:
            raise InputError(str(path), f"the joined WAV's SHA-256, {digest}, doesn't match sets.toml")
        _write_member(io.BytesIO(content), path, dataset.derived_sha256)
    words, turns = [], []
    for i, (piece, offset) in enumerate(read):
        placed_words, placed_turns = place_references(*_meeting_references(of, manifests, i), piece.start,
                                                      piece.end, offset)
        words += placed_words
        turns += placed_turns
    if dataset.cut is not None:
        words, turns = crop_references(words, turns, dataset.cut)
    return [_item(dataset.name, dataset.name, path, words, turns)]


def joined_wav(dataset: Dataset, manifests: Manifests) -> bytes:
    """A concat dataset's WAV bytes, from the slices that start before its cut, in the cache."""
    samples = [slice_wav(source_file(manifests.sources[piece.source]), piece.start, piece.end)
               for piece, _ in _read_pieces(dataset)]
    joined, _ = concat(samples, dataset.gap, dataset.cut)
    return _wav_bytes(joined.astype("<i2").tobytes())


def ami_words(files: list[tuple[str, Path]]) -> list[tuple[float, float, str]]:
    """(start, end, text) of every <w> in the speakers' words.xml files, given as (speaker letter, path).

    Words with punc="true" are skipped. A word without a starttime takes the previous word's in its file (0 for
    the first), and one without an endtime ends at its start. They're sorted by start time, then speaker letter,
    then position in the file.
    """
    keyed = []
    for letter, path in files:
        start = 0.0
        for position, w in enumerate(e for e in ET.parse(path).iter() if _local(e.tag) == "w"):
            if w.get("punc") == "true":
                continue
            start = float(w.get("starttime", start))
            end = float(w.get("endtime", start))
            keyed.append(((start, letter, position), (start, end, (w.text or "").strip())))
    return [word for _, word in sorted(keyed)]


def _local(tag):
    return tag.rpartition("}")[2]


def rttm_turns(path: Path, meeting: str) -> list[Turn]:
    """The meeting's SPEAKER lines, in the file's order: start, start + duration, and speaker."""
    turns = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            fields = line.split()
            if len(fields) >= 8 and fields[0] == "SPEAKER" and fields[1] == meeting:
                start, duration = float(fields[3]), float(fields[4])
                turns.append(Turn(start, start + duration, fields[7]))
    return turns


def crop_references(words, turns, crop):
    """The words whose midpoint is before `crop`, and the turns clipped to [0, crop], without those starting at
    or after it."""
    kept_words = [w for w in words if (w[0] + w[1]) / 2 < crop]
    kept_turns = [Turn(max(t.start, 0.0), min(t.end, crop), t.speaker) for t in turns if t.start < crop]
    return kept_words, kept_turns


def _derived_wav(dataset):
    return data_dir() / "derived" / dataset.name / f"{dataset.meetings[0]}.wav"


def _crop(audio, dataset):
    """The first crop × 16,000 frames of a 16 kHz, mono, 16-bit WAV, copied with the wave module into
    derived/<dataset>/<meeting>.wav, and checked against derived_sha256. A mismatch writes nothing."""
    path = _derived_wav(dataset)
    if _verified(path, dataset.derived_sha256):
        return path
    frames = round(dataset.crop * SAMPLE_RATE)
    with wave.open(str(audio), "rb") as r:
        if (r.getframerate(), r.getnchannels(), r.getsampwidth()) != (SAMPLE_RATE, 1, 2):
            raise ValueError(f"{audio}: {r.getframerate()} Hz, {r.getnchannels()} channels, "
                             f"{8 * r.getsampwidth()}-bit; the crop takes 16 kHz mono 16-bit")
        if r.getnframes() < frames:
            raise ValueError(f"{audio}: {r.getnframes() / SAMPLE_RATE} s, shorter than the crop's {dataset.crop} s")
        data = r.readframes(frames)
    content = _wav_bytes(data)
    if hashlib.sha256(content).hexdigest() != dataset.derived_sha256:
        raise InputError(str(path), "the cropped WAV's SHA-256 doesn't match sets.toml")
    _write_member(io.BytesIO(content), path, dataset.derived_sha256)
    return path


def _wav_bytes(frames):
    """One-channel, 16-bit, 16 kHz WAV of little-endian frames, as the wave module writes it."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(frames)
    return buffer.getvalue()


# --- Pinning a source ------------------------------------------------------------------------------------------


def pin(url: str, members: tuple[str, ...] = ()) -> list[str]:
    """The facts a manifest entry needs about a file, from one download to a temporary directory.

    The first line is `<url> <size> <sha256>`. For an archive (.zip, .tar.gz, .tgz or .tar), one more line
    follows for each regular member matching a `members` glob (fnmatch, where `*` also matches `/`), in the
    archive's order: `<member> <sha256>`. A .flac or .wav, the file or a member, adds `<frames> <rate>
    <channels>` to its line. Only URLs under URL_PREFIXES are fetched. Nothing is cached.
    """
    _check_pin_url(url, members)
    lines, _ = _pin(url, members)
    return lines


def _check_pin_url(url, members):
    if not url.startswith(URL_PREFIXES):
        raise UsageError(url, "isn't under a pinned LibriSpeech or AMI prefix")
    if members and not PurePosixPath(urllib.parse.urlsplit(url).path).name.endswith(ARCHIVE_SUFFIXES):
        raise UsageError(url, f"--member needs an archive ({', '.join(ARCHIVE_SUFFIXES)})")


def _pin(url, members, check=None):
    """pin's lines, and (member, sha256) of each matching member. `check(size, sha256)` runs on the download
    before its members are read."""
    name = PurePosixPath(urllib.parse.urlsplit(url).path).name
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / (name or "download")
        size, sha256 = _save(url, path)
        if check:
            check(size, sha256)
        lines, hashed = [f"{url} {size} {sha256}{_audio_facts(name, path)}"], []
        if not members:
            return lines, hashed
        try:
            for member, stream in _entries(path):
                member = member.removeprefix("./")
                if stream is None or not any(fnmatch.fnmatchcase(member, glob) for glob in members):
                    continue
                data = stream.read()
                hashed.append((member, hashlib.sha256(data).hexdigest()))
                lines.append(f"{member} {hashed[-1][1]}{_audio_facts(member, io.BytesIO(data))}")
        except (tarfile.TarError, zipfile.BadZipFile) as e:
            raise InputError(url, f"can't read the archive: {e}") from e
    return lines, hashed


def write_members(url: str, members: tuple[str, ...], source_id: str, dir: Path = MANIFEST_DIR) -> list[str]:
    """`pin --write-members`: the source's [[source.member]] tables in sources.toml, replaced by the members
    `pin` hashed, in the archive's order (design/internal/g1-stage1.md §5b, decision 2).

    The URL must be one of the source's urls, and the download's size and SHA-256 must be its entry's; otherwise,
    or without `members`, nothing is written and InputError is raised. The new file is written beside
    sources.toml, loaded with sets.toml, and renamed into place only if that passes. Every line outside the
    source's member tables stays as it was. Returns the download's line and one line of what was written.
    """
    path = Path(dir) / "sources.toml"
    if not members:
        raise InputError("--write-members", "needs --member")
    source = _load(path, Path(dir) / "sets.toml").sources.get(source_id)
    if source is None:
        raise InputError(source_id, f"isn't a source in {path}")
    if url not in source.urls:
        raise InputError(url, f"isn't one of {source_id}'s urls")
    _check_pin_url(url, members)

    def check(size, sha256):
        if (size, sha256) != (source.size, source.sha256):
            raise InputError(url, f"size {size} and SHA-256 {sha256} don't match {source_id}'s entry")

    lines, hashed = _pin(url, members, check)
    if not hashed:
        raise InputError(url, f"has no member matching {', '.join(members)}")
    text = _replace_members(path.read_text(encoding="utf-8"), source_id, hashed)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".sources.toml.", suffix=".tmp")
    temp = Path(temp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as out:
            out.write(text)
        _load(temp, Path(dir) / "sets.toml")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)
    return [lines[0], f"{source_id}: {len(hashed)} members written to {path}"]


def _replace_members(text, source_id, members):
    """sources.toml's text with the source's member tables replaced. They run from its first [[source.member]]
    to its last line that isn't blank or a comment, before the next [[source]] or the end; a source without
    members gets them after its last such line."""
    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.strip() == "[[source]]"] + [len(lines)]
    for begin, end in itertools.pairwise(starts):
        if any(line.split("#")[0].strip() == f'id = "{source_id}"' for line in lines[begin:end]):
            break
    else:
        raise InputError(source_id, "has no [[source]] table in sources.toml")
    content = [i for i in range(begin, end) if lines[i].strip() and not lines[i].lstrip().startswith("#")]
    tables = [i for i in content if lines[i].strip() == "[[source.member]]"]
    first, last = (tables[0], content[-1] + 1) if tables else (content[-1] + 1, content[-1] + 1)
    new = "".join(f'\n[[source.member]]\npath = "{p}"\nsha256 = "{h}"\n' for p, h in members)
    if tables:
        new = new.removeprefix("\n")
    elif not lines[first - 1].endswith("\n"):
        new = "\n" + new
    return "".join(lines[:first]) + new + "".join(lines[last:])


def _audio_facts(name, file):
    """' <frames> <rate> <channels>' for a .flac or .wav, from its header; '' for anything else."""
    if not name.lower().endswith(AUDIO_SUFFIXES):
        return ""
    try:
        info = soundfile.info(file)
    except RuntimeError as e:  # soundfile's errors are RuntimeErrors
        raise InputError(name, f"can't read the audio's header: {e}") from e
    return f" {info.frames} {info.samplerate} {info.channels}"


# --- The entry point -------------------------------------------------------------------------------------------


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m lmt.eval.datasets",
                                     description="Fetch the evaluation data and build the fixtures.")
    commands = parser.add_subparsers(dest="command", metavar="COMMAND", required=True)
    f = commands.add_parser("fetch", help="Fetch and verify a set's datasets, and build their recipes.")
    f.add_argument("set", help='The set\'s name in sets.toml ("ci").')
    b = commands.add_parser("build-fixture", help="Fetch a fixture's sources, build it and check its hashes.")
    b.add_argument("name", help="The fixture's name in sets.toml.")
    b.add_argument("--write", action="store_true", help="Write the fixture and its references to their paths first.")
    e = commands.add_parser("encode-fixture", help="Encode a fixture with ffmpeg and check the files' hashes.")
    e.add_argument("name", help="The fixture's name in sets.toml.")
    e.add_argument("--write", action="store_true", help="Write the encodings beside the fixture first.")
    p = commands.add_parser("pin", help="Download a file once and print its size and SHA-256, and its listed "
                                        "members' hashes, for writing the manifests. Nothing is cached.")
    p.add_argument("url", help="Under one of the pinned LibriSpeech or AMI prefixes.")
    p.add_argument("--member", action="append", default=[], metavar="GLOB",
                   help="Archive members to hash, by glob; may be repeated.")
    p.add_argument("--write-members", metavar="SOURCE_ID",
                   help="Replace the source's members in sources.toml with the hashed ones, instead of printing them.")
    args = parser.parse_args(argv)
    try:
        if args.command == "fetch":
            return _fetch_command(args.set)
        if args.command == "pin":
            members = tuple(args.member)
            if args.write_members is not None:
                print("\n".join(write_members(args.url, members, args.write_members, MANIFEST_DIR)))
            else:
                print("\n".join(pin(args.url, members)))
            return 0
        command = _build_fixture_command if args.command == "build-fixture" else _encode_fixture_command
        return command(args.name, args.write)
    except LmtError as e:
        print(f"lmt: error: {e}", file=sys.stderr)
        return e.exit_code


def _fetch_command(set_name):
    """One line per dataset: its name, its items and their total seconds."""
    items = fetch(set_name)
    for name in dict.fromkeys(i.dataset for i in items):
        mine = [i for i in items if i.dataset == name]
        print(f"{name}: {len(mine)} items, {sum(i.duration for i in mine):.3f} s")
    return 0


def _fixture(name):
    manifests = load_manifests(MANIFEST_DIR)
    fixture = manifests.fixtures.get(name)
    if fixture is None:
        raise UsageError(name, f"not a fixture in sets.toml ({', '.join(sorted(manifests.fixtures))})")
    return manifests, fixture


def _encode_fixture_command(name, write):
    _, fixture = _fixture(name)
    if not fixture.encodings:
        raise UsageError(name, "has no encodings in sets.toml")
    version = ffmpeg_version()
    temps, hashes = {}, {}
    try:
        for fmt in ENCODINGS:
            fd, temp = tempfile.mkstemp(dir=Path(fixture.path).parent, suffix=f".{fmt}.tmp")
            os.close(fd)
            temps[fmt] = Path(temp)
            encode(fixture, fmt, temps[fmt])
            hashes[fmt] = _sha256_file(temps[fmt])
        if write:
            for fmt, temp in temps.items():
                temp.replace(encoding_path(fixture, fmt))
    finally:
        for temp in temps.values():
            temp.unlink(missing_ok=True)
    for fmt, digest in hashes.items():
        print(f"{encoding_path(fixture, fmt)} {digest}")
    print(f"ffmpeg {version}")
    if version != fixture.ffmpeg:
        raise InputError("ffmpeg", f"version {version} here, sets.toml records {fixture.ffmpeg}; "
                                   "the hashes can't be compared")
    expected = {e.format: e.sha256 for e in fixture.encodings}
    for fmt, digest in hashes.items():
        if digest != expected.get(fmt):
            raise InputError(str(encoding_path(fixture, fmt)), "the encoded file's SHA-256 doesn't match sets.toml")
    return 0


def _build_fixture_command(name, write):
    manifests, fixture = _fixture(name)
    for source_id in dict.fromkeys(p.source for p in fixture.concat):
        fetch_source(manifests.sources[source_id])
    audio, text, rttm = build_fixture(fixture, manifests)
    files = [(fixture.path, audio, fixture.derived_sha256),
             (fixture.reference, text.encode("utf-8"), fixture.reference_sha256)]
    if rttm is not None:
        files.append((fixture.rttm, rttm.encode("utf-8"), fixture.rttm_sha256))
    if write:
        for path, content, _ in files:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_bytes(content)
    for path, content, _ in files:
        print(f"{path} {hashlib.sha256(content).hexdigest()}")
    for path, content, expected in files:
        if hashlib.sha256(content).hexdigest() != expected:
            raise InputError(path, "the rebuilt file's SHA-256 doesn't match sets.toml")
    print(f"{fixture.name}: {', '.join(path for path, _, _ in files)} match sets.toml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
