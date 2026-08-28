#!/usr/bin/env python3
"""base-files consumer test (R34): etc/debian_version present (config pkg)."""
import os
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    dv = os.path.join(sys.argv[1], "etc", "debian_version")
    if not os.path.isfile(dv):
        print(f"FAIL: etc/debian_version missing: {dv}", file=sys.stderr)
        return 1
    print("OK: base-files etc/debian_version present (config package)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
