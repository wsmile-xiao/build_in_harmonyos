#!/usr/bin/env python3
"""Deterministic integrity validation for the pari-elldata data package.

pari-elldata is a pure data package: it ships no library, no headers and
no executables, so there is no API to call and no binary to run (R34
exemption: for data packages, integrity checking of the packaged data
files replaces the usual "compile a consumer and call the API" test).

What this validator proves instead — on both the unpacked source tree
(--source-root) and the installed package layout (--package-root):

  1. Structural completeness: all 500 data files ell0..ell499 plus the
     README are present and non-empty.
  2. Payload identity: each of the 500 data files matches the exact
     SHA-256 of the official 20210301 release payload (the hashes are
     pinned from the verified upstream tarball, so a truncated, patched
     or corrupted file fails loudly).
  3. Content sanity: the ell0 file contains the record for the first
     curve "11a1" (conductor 11, the smallest conductor in the
     database) with its correct Weierstrass coefficients, and the file
     set covers conductors 0..499999 (README: "all conductor less than
     500000", one file per 1000-conductor range).
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
    20210301 tarball (dd551e64932d4ab27b3f2b2d1da871c2353672fc1a74705c5
    2e3c0de84bd0cf6).  They are embedded as a compact mapping so the
    validator stays self-contained."""
    try:
        from hashes_elldata import PAYLOAD_SHA256
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from hashes_elldata import PAYLOAD_SHA256
    return PAYLOAD_SHA256


def locate_data_root(root, package_layout):
    """Return the directory holding ell0..ell499 + README."""
    root = Path(root)
    if package_layout:
        return root / "share" / "pari" / "elldata"
    return root / "data" / "elldata"


def validate(root, package_layout):
    assertions = Assertions()

    data_dir = locate_data_root(root, package_layout)
    expected_files = {f"ell{i}" for i in range(500)}

    present = {p.name for p in data_dir.iterdir()} if data_dir.is_dir() else set()
    # Source layout: data/elldata/ holds the 500 ell* files plus README.
    # Package layout: share/pari/elldata/ holds the 500 ell* data files;
    # the README is packaged under share/doc/pari-elldata/ and licenses/.
    if package_layout:
        assertions.check(
            present == expected_files,
            f"share/pari/elldata holds exactly the 500 ell* data files "
            f"(found {len(present)} entries)",
        )
    else:
        assertions.check(
            present == expected_files | {"README"},
            f"data directory holds exactly the 500 ell* files plus README "
            f"(found {len(present)} entries)",
        )

    payload_hashes = read_payload_hashes()
    assertions.check(
        len(payload_hashes) == 500,
        "pinned payload hash table covers all 500 data files",
    )

    mismatched = []
    empty = []
    for name, digest in payload_hashes.items():
        path = data_dir / name
        if not path.is_file():
            mismatched.append(f"{name}: missing")
            continue
        size = path.stat().st_size
        if size == 0:
            empty.append(name)
        if sha256(path) != digest:
            mismatched.append(f"{name}: sha256 mismatch")
    assertions.check(not empty, "no packaged data file is empty")
    assertions.check(
        not mismatched,
        f"all 500 data files match the official 20210301 payload sha256 "
        f"(first failures: {mismatched[:3]})",
    )

    # Content sanity: smallest conductor record in the database.
    ell0 = (data_dir / "ell0").read_text(encoding="utf-8")
    assertions.check(
        '"11a1",[0,-1,1,-10,-20]' in ell0,
        "ell0 contains curve 11a1 with Weierstrass coefficients [0,-1,1,-10,-20]",
    )
    # README: in the source tree it sits next to the data files; in the
    # package it is installed under share/doc/pari-elldata/.
    readme_path = (
        root / "share" / "doc" / "pari-elldata" / "README"
        if package_layout
        else data_dir / "README"
    )
    readme = readme_path.read_text(encoding="utf-8")
    assertions.check(
        "Cremona" in readme and "500000" in readme,
        "README documents the Cremona database and the 500000 conductor range",
    )

    if assertions.count != 6:
        raise ValidationError(
            f"expected 6 assertions, executed {assertions.count}"
        )
    print("pari-elldata: 6/6 data-integrity assertions passed")


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
