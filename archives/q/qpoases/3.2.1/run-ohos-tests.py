#!/usr/bin/env python3
"""Drive the qpOASES upstream unit test suite against the OHOS build.

Mirrors ``testing/runUnitTests`` (the authoritative upstream test list and its
exit-code semantics) but executes the already cross-compiled binaries found in
``<build>/upstream-tests``:

    exit 0   -> PASS
    exit 99  -> DATA-MISSING (the test's external problem data set is absent;
                upstream fetches it from a retired COIN-OR SVN server)
    other    -> FAIL

The split between the three categories, and the exact list of binaries, is
printed so the numbers reported in the PR come from real execution.
"""
import os
import subprocess
import sys

# The authoritative upstream test list, in the order of testing/runUnitTests.
# Entries are (binary, argv tail).
UPSTREAM_TESTS = [
    ("test_matrices", []),
    ("test_matrices2", []),
    ("test_matrices3", []),
    ("test_indexlist", []),
    ("test_example1", []),
    ("test_example1a", []),
    ("test_example1b", []),
    ("test_example2", []),
    ("test_example4", []),
    ("test_example5", []),
    ("test_exampleLP", []),
    ("test_qrecipe", []),
    ("test_qrecipeSchur", []),
    ("test_smallSchur", []),
    ("test_infeasible1", []),
    ("test_hs268", []),
    ("test_example6", []),
    ("test_example7", []),
    ("test_sebastien1", []),
    ("test_vanBarelsUnboundedQP", []),
    ("test_janick1", []),
    ("test_janick2", []),
    ("test_constraintProduct1", []),
    ("test_constraintProduct2", []),
    ("test_guessedWS1", []),
    ("test_externalChol1", []),
    ("test_gradientShift", []),
    ("test_runAllOqpExamples", []),
    ("test_bench", ["Odd"]),
    ("test_bench", ["Ods"]),
    ("test_bench", ["Omd"]),
]

DATA_MISSING = 99


def main():
    argv = sys.argv[1:]
    emulator = []
    bindir = None
    i = 0
    while i < len(argv):
        if argv[i] == "--emulator":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                emulator.append(argv[i])
                i += 1
            continue
        if bindir is None:
            bindir = argv[i]
        i += 1
    if bindir is None:
        bindir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upstream-tests")

    passed, missing, failed = [], [], []
    print("=== qpOASES upstream unit tests (testing/runUnitTests parity) ===")
    print("bindir: %s" % bindir)
    print("emulator: %s" % (" ".join(emulator) if emulator else "(none, native execution)"))
    print("")

    for name, args in UPSTREAM_TESTS:
        exe = os.path.join(bindir, name)
        label = " ".join([name] + args)
        if not os.path.exists(exe):
            failed.append(label)
            print("  FAIL  %-32s (binary not built)" % label)
            continue
        try:
            rc = subprocess.call(emulator + [exe] + args, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, timeout=1800)
        except subprocess.TimeoutExpired:
            failed.append(label)
            print("  FAIL  %-32s (timeout)" % label)
            continue
        if rc == 0:
            passed.append(label)
            print("  PASS  %-32s" % label)
        elif rc == DATA_MISSING:
            missing.append(label)
            print("  SKIP  %-32s (problem data missing, exit 99)" % label)
        else:
            failed.append(label)
            print("  FAIL  %-32s (exit %d)" % (label, rc))

    total_runs = len(UPSTREAM_TESTS)
    decided = len(passed) + len(failed)
    print("")
    print("=== summary ===")
    print("upstream_invocations: %d" % total_runs)
    print("passed:              %d" % len(passed))
    print("data_missing(99):    %d" % len(missing))
    print("failed:              %d" % len(failed))
    print("executed_with_verdict: %d" % decided)
    if decided:
        print("pass_rate_of_executed: %.1f%%" % (100.0 * len(passed) / decided))
    if failed:
        print("FAILED: %s" % ", ".join(failed))
        return 1
    print("RESULT: OK - all upstream tests that could run passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
