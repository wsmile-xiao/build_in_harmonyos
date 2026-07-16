#!/usr/bin/env python3
"""Run the packaged c2048 command in upstream non-interactive test mode."""
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: test_c2048.py /path/to/2048", file=sys.stderr)
        return 2

    result = subprocess.run(
        [sys.argv[1], "test"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        return result.returncode
    if "All 13 tests executed successfully" not in result.stdout:
        print("2048 test did not report upstream success message", file=sys.stderr)
        print(result.stdout, end="")
        return 1
    print(result.stdout, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
