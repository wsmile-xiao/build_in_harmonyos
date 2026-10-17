#!/usr/bin/env python3
"""more-itertools consumer test (R34): import + call API (chunked/take)."""
import os
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    # 把打包的 site-packages 加入 sys.path
    site = os.path.join(sys.argv[1], "lib", "python3", "site-packages")
    if not os.path.isdir(site):
        print(f"FAIL: site-packages missing: {site}", file=sys.stderr)
        return 1
    sys.path.insert(0, site)
    try:
        import more_itertools
        # 真实调用 API——chunked（分块）+ take（取前 N 个）
        chunks = list(more_itertools.chunked(range(10), 3))
        if chunks != [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]:
            print(f"FAIL: chunked result wrong: {chunks}", file=sys.stderr)
            return 1
        first = list(more_itertools.take(3, iter([10, 20, 30, 40])))
        if first != [10, 20, 30]:
            print(f"FAIL: take result wrong: {first}", file=sys.stderr)
            return 1
    except ImportError as e:
        print(f"FAIL: import more_itertools: {e}", file=sys.stderr)
        return 1
    print("OK: more_itertools import + chunked/take API works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
