#!/usr/bin/env python3
"""ai.robots.txt 1.47 consumer test — data package verification.

Checks the installed data package: robots.txt exists and contains
"User-agent:" blocks, and lib/pkgconfig/ai-robots-txt.pc exists
(the L1e destructible artifact). Exits non-zero on any failure.
"""
import os
import sys


def main():
    pkg_root = sys.argv[1] if len(sys.argv) > 1 else "."
    failures = 0

    robots = os.path.join(pkg_root, "share", "ai.robots.txt", "robots.txt")
    if not os.path.isfile(robots):
        print("[FAIL] %s missing" % robots)
        failures += 1
    else:
        with open(robots, "rt", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if "User-agent:" not in content:
            print("[FAIL] robots.txt has no 'User-agent:' blocks")
            failures += 1
        else:
            print("[ok] robots.txt present with User-agent blocks")

    pc = os.path.join(pkg_root, "lib", "pkgconfig", "ai-robots-txt.pc")
    if not os.path.isfile(pc):
        print("[FAIL] %s missing (L1e destructible artifact)" % pc)
        failures += 1
    else:
        print("[ok] lib/pkgconfig/ai-robots-txt.pc present")

    if failures:
        print("ai.robots.txt: %d assertion(s) failed" % failures)
        return 1
    print("ai.robots.txt package OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
