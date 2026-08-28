#!/usr/bin/env python3
"""libtry-tiny-perl consumer test (R34): Try/Tiny.pm present (pure Perl)."""
import os
import sys


def main() -> int:
    pm = os.path.join(sys.argv[1], "lib", "perl5", "Try", "Tiny.pm")
    if not os.path.isfile(pm):
        print(f"FAIL: Try/Tiny.pm missing: {pm}", file=sys.stderr)
        return 1
    print("OK: Try/Tiny.pm present (pure Perl module)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
