#!/usr/bin/env python3
"""dataproperty consumer test (R34): import dataproperty + version."""
import os
import sys


def main() -> int:
    site = os.path.join(sys.argv[1], "lib", "python3")
    sys.path.insert(0, site)
    try:
        import dataproperty
    except Exception as e:
        print(f"FAIL: import dataproperty: {e}", file=sys.stderr)
        return 1
    print("OK: dataproperty imported (pure Python library)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
