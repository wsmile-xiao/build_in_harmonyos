#!/usr/bin/env python3
"""Deterministic integrity validation for the pari-seadata-big data package.

pari-seadata-big is a pure data package: it ships no library, no headers
and no executables, so there is no API to call and no binary to run (R34
exemption: for data packages, integrity checking of the packaged data
files replaces the usual "compile a consumer and call the API" test).

What this validator proves instead — on both the unpacked source tree
(--source-root) and the installed package layout (--package-root):

  1. Structural completeness: the 44 data files sea503.gz..sea797.gz
     (one per prime level in (500, 800)) are present, plus README.big in
     the source tree.
  2. Payload identity: every gzip file matches the exact SHA-256 of the
     official 20170418 release payload (pinned from the verified upstream
     archive, so a truncated, recompressed or substituted dataset fails
     loudly).
  3. Stream integrity: every file decompresses completely with a valid
     gzip CRC/trailer.
  4. Content sanity: sea503.gz decompresses to the known Atkin
     polynomial record for p = 503, and README.big documents the dataset
     (ECHIDNA / Kohel, "500 < p < 800", ellcard).
"""

import argparse
import gzip
import hashlib
from pathlib import Path
import sys


# Prime levels carried by upstream: the 44 primes strictly between 500 and
# 800.  sea<p>.gz is the Atkin modular polynomial for level p.
PRIME_LEVELS = [n for n in range(501, 800)
                if all(n % d for d in range(2, int(n ** 0.5) + 1))]

# First decompressed bytes of the official sea503.gz payload: the GP vector
# [503, "A", [1, [-1, 7439, ... marking the p=503 Atkin polynomial.
SEA503_PREFIX = b'[503, "A", [1, [-1, 7439,'


class ValidationError(RuntimeError):
    pass


class Assertions:
    def __init__(self):
        self.count = 0

    def check(self, condition, description):
        if not condition:
            raise ValidationError(description)
        self.count += 1
        print(f"[PASS {self.count:02d}] {description}")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_payload_hashes():
    """SHA-256 of every data file, pinned from the verified upstream
    20170418 archive (7c4db2624808a5bbd2ba00f8b644a439f0508532efd680a24
    7610fdd5822a5f2).  Embedded as a compact mapping so the validator stays
    self-contained."""
    try:
        from hashes_seadata_big import PAYLOAD_SHA256
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from hashes_seadata_big import PAYLOAD_SHA256
    return PAYLOAD_SHA256


def locate_data_root(root, package_layout):
    """Return the directory holding sea<p>.gz (+ README.big in source mode)."""
    root = Path(root)
    if package_layout:
        return root / "share" / "pari" / "seadata"
    return root / "data" / "seadata"


def validate(root, package_layout):
    assertions = Assertions()

    data_dir = locate_data_root(root, package_layout)
    expected_files = {f"sea{p}.gz" for p in PRIME_LEVELS}

    present = {p.name for p in data_dir.iterdir()} if data_dir.is_dir() else set()
    # Source layout: data/seadata/ holds the 44 sea*.gz files plus README.big.
    # Package layout: share/pari/seadata/ holds the 44 data files; the
    # README is packaged under share/doc/pari-seadata-big/ and licenses/.
    if package_layout:
        assertions.check(
            present == expected_files,
            f"share/pari/seadata holds exactly the 44 sea*.gz data files "
            f"(found {len(present)} entries)",
        )
    else:
        assertions.check(
            present == expected_files | {"README.big"},
            f"data directory holds exactly the 44 sea*.gz files plus README.big "
            f"(found {len(present)} entries)",
        )

    payload_hashes = read_payload_hashes()
    assertions.check(
        len(payload_hashes) == 44,
        "pinned payload hash table covers all 44 data files",
    )

    mismatched = []
    empty = []
    for name, digest in payload_hashes.items():
        path = data_dir / name
        if not path.is_file():
            mismatched.append(f"{name}: missing")
            continue
        if path.stat().st_size == 0:
            empty.append(name)
        if sha256(path) != digest:
            mismatched.append(f"{name}: sha256 mismatch")
    assertions.check(not empty, "no packaged data file is empty")
    assertions.check(
        not mismatched,
        f"all 44 data files match the official 20170418 payload sha256 "
        f"(first failures: {mismatched[:3]})",
    )

    # Stream integrity: full decompression of every file validates the gzip
    # CRC and trailer, catching bit rot that a size-only check would miss.
    corrupt = []
    for name in sorted(payload_hashes):
        try:
            with gzip.open(data_dir / name, "rb") as stream:
                while stream.read(4 * 1024 * 1024):
                    pass
        except (OSError, EOFError) as error:
            corrupt.append(f"{name}: {error}")
    assertions.check(
        not corrupt,
        f"all 44 data files decompress completely (first failures: "
        f"{corrupt[:3]})",
    )

    # Content sanity: the smallest level in the dataset, decoded.
    with gzip.open(data_dir / "sea503.gz", "rb") as stream:
        head = stream.read(len(SEA503_PREFIX))
    assertions.check(
        head == SEA503_PREFIX,
        "sea503.gz decompresses to the known p=503 Atkin polynomial record "
        f"({head[:24]!r})",
    )

    # README.big: in the source tree it sits next to the data files; in the
    # package it is installed under share/doc/pari-seadata-big/.
    readme_path = (
        root / "share" / "doc" / "pari-seadata-big" / "README.big"
        if package_layout
        else data_dir / "README.big"
    )
    readme = readme_path.read_text(encoding="latin-1")
    assertions.check(
        "Atkin" in readme and "500 < p < 800" in readme and "ellcard" in readme,
        "README.big documents the Atkin polynomials for 500 < p < 800 used by "
        "ellcard",
    )

    if assertions.count != 7:
        raise ValidationError(
            f"expected 7 assertions, executed {assertions.count}"
        )
    print("pari-seadata-big: 7/7 data-integrity assertions passed")


def main():
    parser = argparse.ArgumentParser()
    roots = parser.add_mutually_exclusive_group(required=True)
    roots.add_argument("--source-root", type=Path)
    roots.add_argument("--package-root", type=Path)
    arguments = parser.parse_args()

    if arguments.source_root:
        validate(arguments.source_root, package_layout=False)
    else:
        validate(arguments.package_root, package_layout=True)


if __name__ == "__main__":
    main()
