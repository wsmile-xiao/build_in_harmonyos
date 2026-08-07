#!/usr/bin/env python3
"""Smoke-test the installed murex command."""

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
        raise SystemExit("Usage: test_murex.py <path-to-murex>")

    exe = pathlib.Path(sys.argv[1])
    if not exe.is_file():
        raise RuntimeError(f"murex executable is missing: {exe}")

    echo_output = run([str(exe), "-c", "echo ohpcd"]).strip()
    if echo_output != "ohpcd":
        raise RuntimeError(f"Unexpected murex command output: {echo_output!r}")

    version_output = run([str(exe), "-version"])
    if "7.2.1001" not in version_output:
        raise RuntimeError(f"murex version output does not contain 7.2.1001: {version_output!r}")

    print("murex package checks passed: 3/3")


if __name__ == "__main__":
    main()

