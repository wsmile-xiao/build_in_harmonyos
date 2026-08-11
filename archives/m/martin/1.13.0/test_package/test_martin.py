#!/usr/bin/env python3
"""Smoke-test the installed martin/mbtiles commands."""

import pathlib
import subprocess
import sys


def run(command):
    return subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
    ).stdout


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: test_martin.py <path-to-bin-dir>")

    bindir = pathlib.Path(sys.argv[1])
    if not bindir.is_dir():
        raise RuntimeError(f"bin directory is missing: {bindir}")

    # martin --version
    martin = bindir / "martin"
    if not martin.is_file():
        raise RuntimeError(f"martin executable is missing: {martin}")
    version_output = run([str(martin), "--version"]).strip()
    if "1.13.0" not in version_output:
        raise RuntimeError(f"Unexpected martin version output: {version_output!r}")

    # martin --help
    help_output = run([str(martin), "--help"])
    for needle in ("Usage:", "martin", "Connection strings"):
        if needle not in help_output:
            raise RuntimeError(f"martin --help missing {needle!r}")

    # mbtiles --help
    mbtiles = bindir / "mbtiles"
    if not mbtiles.is_file():
        raise RuntimeError(f"mbtiles executable is missing: {mbtiles}")
    mbtiles_help = run([str(mbtiles), "--help"])
    for needle in ("Usage:", "mbtiles"):
        if needle not in mbtiles_help:
            raise RuntimeError(f"mbtiles --help missing {needle!r}")

    print("martin test_package OK: martin --version/--help, mbtiles --help all passed")


if __name__ == "__main__":
    main()
