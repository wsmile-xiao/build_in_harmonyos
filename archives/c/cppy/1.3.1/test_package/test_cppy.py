#!/usr/bin/env python3
"""cppy consumer test (R34): import cppy + get_include() + cppy.h exists."""
import os
import sys


def main() -> int:
    site = os.path.join(sys.argv[1], "lib", "python3.12", "site-packages")
    sys.path.insert(0, site)
    try:
        import cppy
    except Exception as e:
        print(f"FAIL: import cppy: {e}", file=sys.stderr)
        return 1
    # get_include() 返回头文件目录
    try:
        inc = cppy.get_include()
        if not os.path.isdir(inc):
            print(f"FAIL: get_include() dir missing: {inc}", file=sys.stderr)
            return 1
        cppy_h = os.path.join(inc, "cppy", "cppy.h")
        if not os.path.isfile(cppy_h):
            print(f"FAIL: cppy/cppy.h missing: {cppy_h}", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"FAIL: get_include(): {e}", file=sys.stderr)
        return 1
    print(f"OK: cppy {cppy.__version__} imported + get_include() "
          f"-> cppy/cppy.h exists (pure Python header lib)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
