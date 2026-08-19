#!/usr/bin/env python3
"""Installed pixz round-trip consumer test."""

import os
from pathlib import Path
import subprocess
import sys


def run(command):
    environment = os.environ.copy()
    environment["LD_LIBRARY_PATH"] = ""
    subprocess.run(command, check=True, env=environment)


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: test_pixz.py <pixz-bin> <work-dir>")

    pixz_bin = Path(sys.argv[1])
    work_dir = Path(sys.argv[2])
    sample = work_dir / "sample.txt"
    compressed = work_dir / "sample.txt.xz"
    output = work_dir / "sample.out"

    sample.write_text("pixz harmonyos round trip\n" * 8, encoding="utf-8")
    run([str(pixz_bin), "-k", "-t", str(sample), str(compressed)])
    run([str(pixz_bin), "-d", str(compressed), str(output)])

    if output.read_bytes() != sample.read_bytes():
        raise RuntimeError("pixz round-trip output mismatch")

    print("pixz round-trip test passed")


if __name__ == "__main__":
    main()
