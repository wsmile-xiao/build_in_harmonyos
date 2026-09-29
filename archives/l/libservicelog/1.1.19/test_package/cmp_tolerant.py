#!/usr/bin/env python3
"""Timestamp-tolerant comparator, a port of the upstream run_tests
`diff_with_result_without_timestamp` semantics:

  diff -a -y --suppress-common-line EXPECTED ACTUAL | cut -d ' ' -f1,2

Every line pair that differs byte-for-byte is inspected; if the EXPECTED
line's leading field name is one of the volatile fields (timestamps,
platform, node name) the line is ignored regardless of its value,
otherwise the comparison fails. Line counts must match (diff -y aligns
by line).

Usage: cmp_tolerant.py <expected> <actual>
"""
import sys

IGNORE = (
    "Log Timestamp:",
    "Event Timestamp:",
    "Update Timestamp:",
    "Platform:",
    "Node Name:",
)


def is_volatile(line):
    # upstream run_tests:73 compares only the leading field name(s)
    # (cut -d ' ' -f1,2) against the volatile set; a differing line is
    # ignored when its name field matches, whatever the value is.
    return line.lstrip().startswith(IGNORE)


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: cmp_tolerant.py <expected> <actual>")
    with open(sys.argv[1], "r", encoding="latin-1") as fh:
        expected = fh.read().splitlines()
    with open(sys.argv[2], "r", encoding="latin-1") as fh:
        actual = fh.read().splitlines()

    bad = 0
    for i in range(max(len(expected), len(actual))):
        exp = expected[i] if i < len(expected) else "<missing>"
        act = actual[i] if i < len(actual) else "<missing>"
        if exp == act:
            continue
        if is_volatile(exp):
            continue
        print("diff line {}: expected={!r} actual={!r}".format(i + 1, exp, act))
        bad += 1

    if bad:
        sys.exit("comparison FAILED: {} differing line(s)".format(bad))
    print("comparison OK (timestamp/platform/node tolerant)")


if __name__ == "__main__":
    main()
