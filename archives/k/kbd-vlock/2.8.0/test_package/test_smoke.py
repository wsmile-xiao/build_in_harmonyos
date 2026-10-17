#!/usr/bin/env python3
import subprocess
import sys


def run_vlock(vlock, arg):
    completed = subprocess.run(
        [vlock, arg],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return completed.stdout


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_smoke.py /path/to/vlock")
    vlock = sys.argv[1]
    version = run_vlock(vlock, "--version")
    help_text = run_vlock(vlock, "--help")
    if "2.8.0" not in version:
        raise SystemExit("--version output did not include 2.8.0")
    if "Usage:" not in help_text:
        raise SystemExit("--help output did not include usage text")
    if "vlock" not in help_text:
        raise SystemExit("--help output did not identify vlock")


if __name__ == "__main__":
    main()
