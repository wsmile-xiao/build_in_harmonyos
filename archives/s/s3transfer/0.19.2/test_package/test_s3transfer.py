#!/usr/bin/env python3
"""s3transfer consumer test (R34): import s3transfer (pure Python)."""
import os
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    site = os.path.join(sys.argv[1], "lib", "python3")
    sys.path.insert(0, site)
    try:
        import s3transfer
    except Exception as e:
        print(f"FAIL: import s3transfer: {e}", file=sys.stderr)
        return 1
    print("OK: s3transfer imported (pure Python library)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
