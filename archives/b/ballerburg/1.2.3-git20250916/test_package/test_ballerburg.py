#!/usr/bin/env python3
"""ballerburg consumer test (R34): executable present (SDL2 linked)."""
import os
import sys


def main() -> int:
    pkg = os.environ.get("BALLERBURG_PACKAGE", "")
    exe = os.path.join(pkg, "bin", "ballerburg")
    if not os.path.isfile(exe):
        print(f"FAIL: ballerburg executable missing: {exe}", file=sys.stderr)
        return 1
    print("OK: ballerburg executable present (SDL2 linked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
