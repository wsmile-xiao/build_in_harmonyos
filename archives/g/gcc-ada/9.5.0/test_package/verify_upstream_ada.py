#!/usr/bin/env python3
"""Run selected upstream GNAT and ACATS tests on HarmonyOS."""

import os
import subprocess
import sys


GNAT_DG_TESTS = (
    "modular2",
    "fixedpnt",
    "concat_length",
    "array31",
    "overflow_sum3",
    "access_test",
    "aggr1",
    "array10",
    "alignment2",
    "abstract_with_anonymous_result",
    "array3",
    "array4",
    "array6",
    "array12",
    "array21",
    "array30",
    "array33",
    "array34",
    "array_bounds_test",
    "access4",
    "access_discr2",
    "aggr3",
    "alignment1",
    "alignment7",
    "alignment8",
    "alignment9",
    "alignment10",
    "modular1",
    "modular3",
    "fixedpnt5",
)
ACATS_TESTS = (
    "a22006b",
    "c2a021b",
    "c38006a",
    "c54a23a",
    "c95040a",
    "a22006c",
    "a22006d",
    "a35101b",
    "c23006a",
    "c48004a",
    "c55c02a",
)


def run_program(path, expected_output=None):
    try:
        result = subprocess.run(
            [path],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        print("upstream Ada test timed out: {}".format(path), file=sys.stderr)
        return False
    except FileNotFoundError:
        print("upstream Ada test executable was not found: {}".format(path),
              file=sys.stderr)
        return False
    except PermissionError:
        print("upstream Ada test executable is not runnable: {}".format(path),
              file=sys.stderr)
        return False

    if result.returncode != 0:
        print(
            "upstream Ada test exited with status {}: {}".format(
                result.returncode, path
            ),
            file=sys.stderr,
        )
        if result.stdout:
            print(result.stdout, end="", file=sys.stderr)
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        return False
    if (
        expected_output
        and expected_output.casefold() not in result.stdout.casefold()
    ):
        print(
            "upstream Ada test did not emit {!r}: {}".format(
                expected_output, path
            ),
            file=sys.stderr,
        )
        if result.stdout:
            print(result.stdout, end="", file=sys.stderr)
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        return False
    return True


def main():
    if len(sys.argv) != 2:
        print("usage: verify_upstream_ada.py <upstream-build-root>", file=sys.stderr)
        return 2

    root = sys.argv[1]
    for test_name in GNAT_DG_TESTS:
        executable = os.path.join(root, "gnat.dg", test_name, test_name)
        if not run_program(executable):
            return 1
        print("PASS: gnat.dg/{}.adb".format(test_name))
    print("UPSTREAM_GNAT_DG_SUBSET={}/{}".format(
        len(GNAT_DG_TESTS), len(GNAT_DG_TESTS)
    ))

    for test_name in ACATS_TESTS:
        executable = os.path.join(root, "acats", test_name, test_name)
        expected = "==== {} PASSED".format(test_name.upper())
        if not run_program(executable, expected):
            return 1
        print("PASS: ACATS/{}".format(test_name.upper()))
    print("UPSTREAM_ACATS_SUBSET={}/{}".format(
        len(ACATS_TESTS), len(ACATS_TESTS)
    ))
    print("UPSTREAM_ADA_SUBSET_TOTAL={}/{}".format(
        len(GNAT_DG_TESTS) + len(ACATS_TESTS),
        len(GNAT_DG_TESTS) + len(ACATS_TESTS),
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
