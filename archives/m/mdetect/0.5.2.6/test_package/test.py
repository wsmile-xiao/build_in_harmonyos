"""Exercise the packaged CLI help path without probing host input devices."""

import subprocess
import sys


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: test.py <mdetect-executable>")

    result = subprocess.run(
        [sys.argv[1], "-h"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        raise SystemExit(f"mdetect -h exited {result.returncode}: {output}")
    if "Usage: mdetect [-hnrvox]" not in output:
        raise SystemExit(f"mdetect -h did not print the expected usage: {output}")
    print("mdetect -h usage smoke test: PASS")


if __name__ == "__main__":
    main()
