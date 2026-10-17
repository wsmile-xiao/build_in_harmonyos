#!/usr/bin/env python3
"""Run the upstream Catch2 binary and emit a machine-readable marker."""

import re
import subprocess
import sys


def main():
    if len(sys.argv) != 2:
        print("usage: run_upstream_tests.py <binary>")
        return 2

    binary = sys.argv[1]
    result = subprocess.run(
        [binary, "--reporter", "compact"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    output = result.stdout or ""
    print(output)

    if result.returncode != 0:
        print("UPSTREAM_TEST_RESULT total=0 failures=1 errors=1 skipped=0")
        return result.returncode

    match = re.search(
        r"All tests passed\s*\((\d+)\s+assertions in\s+(\d+)\s+test cases\)",
        output,
    )
    if match:
        assertions = int(match.group(1))
        cases = int(match.group(2))
    else:
        match = re.search(
            r"Passed all\s+(\d+)\s+test cases with\s+(\d+)\s+assertions\.",
            output,
        )
        if not match:
            print("UPSTREAM_TEST_RESULT total=0 failures=1 errors=1 skipped=0")
            print("could not parse Catch2 result", file=sys.stderr)
            return 1
        cases = int(match.group(1))
        assertions = int(match.group(2))
    print(
        "UPSTREAM_TEST_RESULT total=%d assertions=%d failures=0 errors=0 skipped=0"
        % (cases, assertions)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
