#!/usr/bin/env python3
"""Behavior test for the packaged upse123 command."""

import subprocess
import sys


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    runner = sys.argv[1:-1]
    binary = sys.argv[-1]
    result = subprocess.run(
        runner + [binary, "-v"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    require(result.returncode == 0, f"upse123 -v rc={result.returncode}")
    require(result.stdout.strip().endswith("1.0.0"), result.stdout + result.stderr)
    require("Sound device not available" not in result.stdout, result.stdout)
    print("upse123 version behavior: PASS (3 assertions)")


if __name__ == "__main__":
    main()
