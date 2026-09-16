#!/usr/bin/env python3
"""Run the GCC Ada consumer test and validate its output contract."""

import subprocess
import sys


EXPECTED_OUTPUT = "gcc-ada checks passed: 6"


def main():
    if len(sys.argv) != 2:
        print(
            "usage: verify_gcc_ada.py <gcc_ada_test>",
            file=sys.stderr,
        )
        return 2

    try:
        result = subprocess.run(
            [sys.argv[1]],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        print("Ada consumer test timed out after 30 seconds", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print(
            "Ada consumer test executable was not found: {}".format(
                sys.argv[1]
            ),
            file=sys.stderr,
        )
        return 1
    except PermissionError:
        print(
            "Ada consumer test executable is not runnable: {}".format(
                sys.argv[1]
            ),
            file=sys.stderr,
        )
        return 1
    if result.returncode != 0:
        print(
            "Ada consumer test exited with status {}".format(
                result.returncode
            ),
            file=sys.stderr,
        )
        if result.stdout:
            print(result.stdout, end="", file=sys.stderr)
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        return 1

    actual_output = result.stdout.strip()
    if actual_output != EXPECTED_OUTPUT:
        print(
            "unexpected Ada consumer output: {!r}; expected {!r}".format(
                actual_output, EXPECTED_OUTPUT
            ),
            file=sys.stderr,
        )
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        return 1

    print(actual_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
