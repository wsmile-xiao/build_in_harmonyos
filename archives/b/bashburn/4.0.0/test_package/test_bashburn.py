#!/usr/bin/env python3
"""bashburn consumer test (R34): executable present (shell script)."""
import os
import sys


def main() -> int:
    exe = os.path.join(sys.argv[1], "bin", "bashburn")
    if not os.path.isfile(exe):
        print(f"FAIL: bashburn executable missing: {exe}", file=sys.stderr)
        return 1
    print("OK: bashburn executable present (shell script)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
