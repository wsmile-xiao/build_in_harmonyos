#!/usr/bin/env python3
"""Recover libmpeg2's 73 upstream fixtures from its SHA-pinned CVS ZIP.

Each RCS head deltatext is the latest trunk fulltext; later entries in the
archive are reverse deltas. This script never combines the CVS references
with the unrelated MPlayer mirror snapshot.
"""

import argparse
import hashlib
from pathlib import Path
import re
from zipfile import ZipFile


ZIP_SHA256 = "4d42e8eb62bbeb8063ebd0c66a7fb6802b7a9882212c1f7253483f789eb85aa8"
RCS_ROOT = "libmpeg2/mpeg2dec-streams/"
KINDS = ("stream", "c.md5", "dump")


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def quoted(data, position):
    if data[position] != 64:
        raise ValueError("RCS string does not start with @")
    position += 1
    value = bytearray()
    while position < len(data):
        byte = data[position]
        if byte == 64:
            if position + 1 < len(data) and data[position + 1] == 64:
                value.append(64)
                position += 2
                continue
            return bytes(value), position + 1
        value.append(byte)
        position += 1
    raise ValueError("unterminated RCS string")


def latest_fulltext(archive):
    match = re.search(rb"\Ahead\s+([0-9.]+);", archive)
    if not match:
        raise ValueError("RCS head revision missing")
    revision = match.group(1)
    position = archive.index(b"\ndesc\n") + len(b"\ndesc\n")
    _, position = quoted(archive, position)
    marker = b"\n" + revision + b"\nlog\n"
    position = archive.index(marker, position) + len(marker)
    _, position = quoted(archive, position)
    if archive[position:position + 6] != b"\ntext\n":
        raise ValueError("RCS head fulltext marker missing")
    content, _ = quoted(archive, position + 6)
    return revision.decode("ascii"), content


def cases_from_tests(path):
    cases = []
    for line in path.read_text("utf-8").splitlines():
        case = line.split("#", 1)[0].strip()
        if not case:
            continue
        parts = Path(case).parts
        if len(parts) < 2 or any(part in (".", "..") for part in parts):
            raise ValueError("unsafe upstream case: " + case)
        cases.append(case)
    if len(cases) != 73 or len(set(cases)) != 73:
        raise ValueError("upstream test denominator or uniqueness changed")
    return cases


def extract(zip_path, tests_path, output):
    if output.exists() or output.is_symlink():
        raise ValueError("output already exists")
    if digest(zip_path) != ZIP_SHA256:
        raise ValueError("CVS ZIP SHA-256 mismatch")
    cases = cases_from_tests(tests_path)
    rows = []
    with ZipFile(zip_path) as archive:
        if archive.testzip() is not None:
            raise ValueError("CVS ZIP CRC validation failed")
        names = set(archive.namelist())
        expected = {RCS_ROOT + case + "/" + kind + ",v"
                    for case in cases for kind in KINDS}
        if not expected.issubset(names):
            raise ValueError("CVS ZIP lacks a required upstream fixture")
        ignored = {case for case in cases
                   if RCS_ROOT + case + "/IGNORE-MD5,v" in names}
        if len(ignored) != 5:
            raise ValueError("upstream IGNORE-MD5 count changed")
        output.mkdir(parents=True)
        for case in cases:
            directory = output.joinpath(*case.split("/"))
            directory.mkdir(parents=True)
            kinds = KINDS + (("IGNORE-MD5",) if case in ignored else ())
            for kind in kinds:
                revision, data = latest_fulltext(
                    archive.read(RCS_ROOT + case + "/" + kind + ",v"))
                with (directory / kind).open("xb") as target:
                    target.write(data)
                rows.append((case, kind, revision, len(data),
                             hashlib.sha256(data).hexdigest()))
    if len(rows) != 224:
        raise ValueError("restored fixture count changed")
    lines = ["# SourceForge CVS snapshot SHA256=" + ZIP_SHA256,
             "# latest trunk fulltext; not the historical 2003 tarball",
             "case\tfile\trevision\tbytes\tsha256"]
    lines.extend("\t".join(map(str, row)) for row in rows)
    (output / "manifest.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("RECOVERED=73/73 FILES=224 MANIFEST_SHA256=" + digest(output / "manifest.tsv"), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", required=True, type=Path)
    parser.add_argument("--tests", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    extract(args.zip, args.tests, args.output)


if __name__ == "__main__":
    main()
