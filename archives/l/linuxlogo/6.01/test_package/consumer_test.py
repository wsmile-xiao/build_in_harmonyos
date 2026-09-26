#!/usr/bin/env python3
"""Consumer test source for linuxlogo 6.01 (invoked by conanfile.py test()).

Usage: consumer_test.py <path-to-linux_logo-executable>
Every check is falsifiable on its own; the set fails the build if any
observed property of the rendered output is not satisfied.
"""
import re
import subprocess
import sys

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def main():
    if len(sys.argv) < 2:
        print("usage: consumer_test.py <linux_logo exe>")
        return 2
    exe = sys.argv[1]
    proc = subprocess.run([exe], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          stdin=subprocess.DEVNULL, timeout=90)
    raw = proc.stdout.decode("utf-8", "replace")
    text = ANSI.sub("", raw)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    last = lines[-1] if lines else ""

    checks = [
        ("exit status is 0", proc.returncode == 0),
        ("logo bitmap rendered (>=100 glyph cells)", text.count("#") >= 100),
        ("kernel line present", re.search(r"\bVersion\b.*\bKernel\b", text) is not None),
        ("cpu line present", re.search(r"\d+\s+[\d.]+GHz.*Processors", text) is not None),
        ("memory line present", re.search(r"[\d.]+[KMGT]?B RAM", text) is not None),
        ("hostname line present", 0 < len(last) <= 64 and " " not in last),
    ]
    failed = 0
    for label, ok in checks:
        print("{0} {1}".format("PASS" if ok else "FAIL", label))
        if not ok:
            failed += 1
    if failed:
        print("FAILURES: {0} of {1}; output tail: {2}".format(failed, len(checks), text[-300]))
        return 1
    print("ALL {0} CHECKS PASSED, stdout {1} bytes".format(len(checks), len(raw)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
