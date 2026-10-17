#!/usr/bin/env python3
"""libpath-tiny-perl consumer test (R34): Path/Tiny.pm present (pure Perl)."""
import os
import sys


def main() -> int:
    pm = os.path.join(sys.argv[1], "lib", "perl5", "Path", "Tiny.pm")
    if not os.path.isfile(pm):
        print(f"FAIL: Path/Tiny.pm missing: {pm}", file=sys.stderr)
        return 1
    print("OK: Path/Tiny.pm present (pure Perl module)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
