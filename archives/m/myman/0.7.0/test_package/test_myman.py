#!/usr/bin/env python3
"""Run smoke checks against the installed myman executable."""
import subprocess
import sys


def run(executable, option):
    result = subprocess.run([executable, option], check=False, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0:
        raise SystemExit(f"myman {option} exited {result.returncode}:\n{result.stdout}")
    if not result.stdout.strip():
        raise SystemExit(f"myman {option} produced no output")
    return result.stdout


if len(sys.argv) != 2:
    raise SystemExit("usage: test_myman.py <myman-executable>")
version_output = run(sys.argv[1], "--version")
if "0.7.0" not in version_output:
    raise SystemExit(f"unexpected version output: {version_output}")
run(sys.argv[1], "--help")
print("myman --version and --help passed")
