#!/usr/bin/env python3
"""Deterministic integrity validation for the pari-galdata data package.

pari-galdata is a pure data package: it ships no library, no headers and
no executables, so there is no API to call and no binary to run (R34
exemption: for data packages, integrity checking of the packaged data
files replaces the usual "compile a consumer and call the API" test).

What this validator proves instead — on both the unpacked source tree
(--source-root) and the installed package layout (--package-root):

  1. Structural completeness: exactly the 344 known data files are
     present (4 name tables NAM8..NAM11, 197 COS* coset files, 143 RES*
     resolvent files), nothing missing, nothing extra.
  2. Payload identity: every one of the 344 files matches the exact
     SHA-256 of the official 20080411 release payload (hashes pinned
     from the verified upstream tarball).
  3. Content sanity: the name tables parse as GP list literals, NAM8
     starts with the cyclic group "C(8)=8", NAM11 contains the Mathieu
     group M(11), and a binary COS file carries its header ("p n k"
     followed by the coset digits) exactly as polgalois reads it.
"""

import argparse
import hashlib
from pathlib import Path
import sys


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
    20080411 tarball (b7c1650099b24a20bdade47a85a928351c586287f0d4c739
    33313873e63290dd)."""
    try:
        from hashes_galdata import PAYLOAD_SHA256
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from hashes_galdata import PAYLOAD_SHA256
    return PAYLOAD_SHA256


def locate_data_root(root, package_layout):
    """Return the directory holding NAM*/COS*/RES* files."""
    root = Path(root)
    if package_layout:
        return root / "share" / "pari" / "galdata"
    return root / "data" / "galdata"


def validate(root, package_layout):
    assertions = Assertions()

    data_dir = locate_data_root(root, package_layout)
    payload_hashes = read_payload_hashes()
    expected_files = set(payload_hashes)
    assertions.check(
        len(expected_files) == 344,
        "pinned payload hash table covers all 344 data files",
    )

    present = {p.name for p in data_dir.iterdir()} if data_dir.is_dir() else set()
    assertions.check(
        present == expected_files,
        f"data directory holds exactly the 344 known files "
        f"(found {len(present)} entries)",
    )

    by_prefix = {"NAM": 0, "COS": 0, "RES": 0}
    for name in expected_files:
        by_prefix[name[:3]] += 1
    assertions.check(
        by_prefix == {"NAM": 4, "COS": 197, "RES": 143},
        f"file census matches the release: 4 NAM + 197 COS + 143 RES "
        f"(got {by_prefix})",
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
        f"all 344 data files match the official 20080411 payload sha256 "
        f"(first failures: {mismatched[:3]})",
    )

    # Content sanity: name tables parse as GP list literals.
    nam8 = (data_dir / "NAM8").read_text(encoding="utf-8").strip()
    assertions.check(
        nam8.startswith('["C(8)=8"') and nam8.endswith("]"),
        'NAM8 is a GP list literal starting with the cyclic group "C(8)=8"',
    )
    nam11 = (data_dir / "NAM11").read_text(encoding="utf-8")
    assertions.check(
        '"M(11)"' in nam11 and '"S11"' in nam11,
        'NAM11 lists the Mathieu group M(11) and the symmetric group S11',
    )

    # Content sanity: a binary COS file carries its "p n k" header.
    cos = (data_dir / "COS10_10_4").read_bytes()
    header = cos[:6]
    assertions.check(
        header == b"A 5 \x00\x00",
        "COS10_10_4 binary header is 'A 5 ' followed by two zero bytes",
    )
    tail = cos[8:]
    assertions.check(
        all(48 <= b <= 57 or 65 <= b <= 90 for b in tail),
        "COS10_10_4 body is pure alphanumeric coset digits (A-Z0-9)",
    )

    if assertions.count != 9:
        raise ValidationError(
            f"expected 9 assertions, executed {assertions.count}"
        )
    print("pari-galdata: 9/9 data-integrity assertions passed")


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
