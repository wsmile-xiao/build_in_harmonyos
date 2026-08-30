#!/usr/bin/env python3
"""chardet consumer test (R34): real API — detect() + version check."""
import sys


def main() -> int:
    import chardet

    if chardet.__version__ != "5.2.0":
        print(f"FAIL: chardet version {chardet.__version__}", file=sys.stderr)
        return 1
    # 真实 API：detect() 编码检测（核心——**非 ASCII** 的 UTF-8 字节——
    # 纯 ASCII 会检测为 ascii 而非 utf-8——实测 #6587）
    result = chardet.detect("héllo wörld".encode("utf-8"))
    if not result or result.get("encoding") != "utf-8":
        print(f"FAIL: detect result {result!r}", file=sys.stderr)
        return 1
    print("OK: chardet 5.2.0 (detect ok, version check)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
