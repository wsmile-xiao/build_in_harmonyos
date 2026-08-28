#!/usr/bin/env python3
"""bitlbee consumer test (R34): bitlbee binary present + executable.
（不执行 bitlbee——CI 的 posix_spawn 执行报 'Operation not permitted'
（沙箱限制——同 base-devel）——改为检查二进制存在 + 可执行位）
"""
import os
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    bitlbee = os.path.join(sys.argv[1], "bin", "bitlbee")
    if not os.path.isfile(bitlbee):
        print(f"FAIL: bitlbee binary missing: {bitlbee}", file=sys.stderr)
        return 1
    if not os.access(bitlbee, os.X_OK):
        print(f"FAIL: bitlbee binary not executable: {bitlbee}",
              file=sys.stderr)
        return 1
    print("OK: bitlbee binary present + executable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
