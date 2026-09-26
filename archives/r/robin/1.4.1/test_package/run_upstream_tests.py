#!/usr/bin/env python3
"""Run the upstream Boost.Test binary and emit a machine-readable marker."""

import re
import subprocess
import sys


def main():
    if len(sys.argv) != 2:
        print("usage: run_upstream_tests.py <binary>")
        return 2

    binary = sys.argv[1]
    result = subprocess.run(
        [binary, "--log_level=test_suite", "--report_level=detailed"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    output = result.stdout or ""
    print(output)

    match = re.search(r"Running\s+(\d+)\s+test cases", output)
    if result.returncode != 0:
        print("UPSTREAM_TEST_RESULT total=0 failures=1 errors=1 skipped=0")
        return result.returncode
    if not match:
        print("UPSTREAM_TEST_RESULT total=0 failures=1 errors=1 skipped=0")
        print("could not parse Boost.Test case count", file=sys.stderr)
        return 1

    total = int(match.group(1))
    print(
        "UPSTREAM_TEST_RESULT total=%d failures=0 errors=0 skipped=0" % total
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
