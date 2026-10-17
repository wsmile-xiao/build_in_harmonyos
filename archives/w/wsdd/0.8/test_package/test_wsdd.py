#!/usr/bin/env python3
"""Offline consumer assertions for the packaged wsdd executable."""

import subprocess
import sys


def main() -> int:
    binary = sys.argv[1]
    version = subprocess.run(
        [binary, "--version"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=20,
    )
    if "0.8" not in version.stdout:
        raise SystemExit(f"unexpected --version output: {version.stdout!r}")

    help_result = subprocess.run(
        [binary, "--help"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=20,
    )
    for expected in ("--version", "--interface", "--hostname"):
        if expected not in help_result.stdout:
            raise SystemExit(f"--help output lacks {expected!r}: {help_result.stdout!r}")

    print("wsdd consumer test: version and help checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
