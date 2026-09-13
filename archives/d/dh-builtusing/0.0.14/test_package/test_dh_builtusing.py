#!/usr/bin/env python3
"""Consumer verification for dh-builtusing (R34: real package content).

Checks the installed package (not the source tree):
1. bin/dh_builtusing exists and contains the Built-Using substvar core
   (dh-builtusing: pattern + addsubstvar call).
2. lib/perl5/builtusing.pm exists and wires the dh sequencer
   (insert_before dh_gencontrol dh_builtusing).
3. bin/dh_builtusing contains the D/P/S pattern-encoding logic
   (y/DPS/.+*/ transliteration + S -> .* wildcard).

Prints per-check OK lines plus a final RESULT line consumed by
test_package/conanfile.py for HMBS_TEST_PACKAGE_RESULT numbers.
Exit 0 only when all checks pass (harness detects failure via rc).
"""
import os
import sys


def check(path, needles, label):
    if not os.path.isfile(path):
        print(f"FAIL: {label} missing: {path}")
        return False
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError as e:
        print(f"FAIL: {label} unreadable: {e}")
        return False
    if not text.strip():
        print(f"FAIL: {label} is empty (toybox-tar style empty fixture?)")
        return False
    for needle in needles:
        if needle not in text:
            print(f"FAIL: {label} lacks {needle!r}")
            return False
    print(f"OK: {label}")
    return True


def main():
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument")
        return 1
    pkg = sys.argv[1]
    passed = 0
    failed = 0

    dh = os.path.join(pkg, "bin", "dh_builtusing")
    if check(dh, ["builtusing:", "addsubstvar"], "dh_builtusing core"):
        passed += 1
    else:
        failed += 1

    pm = os.path.join(pkg, "lib", "perl5", "builtusing.pm")
    if check(pm, ["insert_before", "dh_gencontrol", "dh_builtusing"],
             "builtusing.pm sequencer"):
        passed += 1
    else:
        failed += 1

    if check(dh, ["y/DPS/.+*/", "s/ S /"], "DPS pattern encoding"):
        passed += 1
    else:
        failed += 1

    print(f"RESULT: {passed} passed, {failed} failed")
    return 0 if failed == 0 and passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
