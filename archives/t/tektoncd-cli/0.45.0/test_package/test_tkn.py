#!/usr/bin/env python3
"""Smoke-test the installed tkn command."""

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
        raise SystemExit("Usage: test_tkn.py <path-to-tkn>")

    exe = pathlib.Path(sys.argv[1])
    if not exe.is_file():
        raise RuntimeError(f"tkn executable is missing: {exe}")

    help_output = run([str(exe), "--help"])
    if "tekton" not in help_output.lower() and "tkn" not in help_output.lower():
        raise RuntimeError("tkn --help did not identify the command")

    version_output = run([str(exe), "version"])
    if "version" not in version_output.lower():
        raise RuntimeError(f"Unexpected tkn version output: {version_output!r}")

    print("tektoncd-cli package checks passed: 3/3")


if __name__ == "__main__":
    main()
