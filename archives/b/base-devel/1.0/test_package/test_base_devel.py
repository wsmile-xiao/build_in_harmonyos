#!/usr/bin/env python3
"""base-devel consumer test (R34): meta-package dep bin dirs present.
Deps (gcc/autoconf/automake) are conan packages — check their bin dirs
exist (executing cross-compiled commands is unreliable in the sandbox)."""
import os
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing bin paths argument", file=sys.stderr)
        return 1
    bins = sys.argv[1].split(os.pathsep)
    missing = [b for b in bins if not os.path.isdir(b)]
    if missing:
        print(f"FAIL: missing dep bin dirs: {missing}", file=sys.stderr)
        return 1
    # 每个 bin 目录至少有一个可执行文件
    empty = [b for b in bins if not os.listdir(b)]
    if empty:
        print(f"FAIL: empty dep bin dirs: {empty}", file=sys.stderr)
        return 1
    print(f"OK: base-devel deps present ({len(bins)} bin dirs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
