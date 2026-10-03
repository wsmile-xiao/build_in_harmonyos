#!/usr/bin/env python3
"""Exercise the packaged xmppc help command as a real consumer."""
import subprocess
import sys


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_cli.py /path/to/xmppc")

    executable = sys.argv[1]
    result = subprocess.run(
        [executable, "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        raise SystemExit(f"xmppc --help exited with {result.returncode}: {output}")
    if "Usage: xmppc" not in output:
        raise SystemExit("xmppc --help did not print its usage text")
    if "Display this information" not in output:
        raise SystemExit("xmppc help options are missing")

if __name__ == "__main__":
    main()
