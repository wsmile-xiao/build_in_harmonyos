#!/usr/bin/env python3
"""Run cargo-seek version/help checks."""

import subprocess
import sys


def run(binary, *args):
    result = subprocess.run(
        [binary, *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"{binary} {' '.join(args)} failed ({result.returncode})\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def main():
    if len(sys.argv) != 2:
        print("usage: test_cargo_seek.py <cargo-seek>", file=sys.stderr)
        return 2
    binary = sys.argv[1]
    version = run(binary, "--version")
    out = version.stdout.strip() + version.stderr.strip()
    assert "0.1.0" in out, out
    help_res = run(binary, "--help")
    help_out = help_res.stdout + help_res.stderr
    assert "--search" in help_out or "-s" in help_out, help_out
    assert "--help" in help_out, help_out
    # Also check subcommand help via cargo seek alias is not needed; binary help is sufficient
    print("cargo-seek version/help checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
