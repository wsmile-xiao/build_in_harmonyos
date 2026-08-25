#!/usr/bin/env python3
"""chardet consumer test (L0c + R34): standalone test source executed
via self.run from conanfile.py test().

R34: actually call the tested API — chardet.detect() on known-encoded
bytes (universal encoding detector, pure user-space). Import failure or
wrong result asserts fail.
"""
import sys


def main() -> int:
    try:
        import chardet
    except ImportError as e:
        print(f"FAIL: cannot import chardet: {e}", file=sys.stderr)
        return 1

    # 真实调用 API：UTF-8 文本编码检测（纯用户态）
    data = "hello 世界".encode("utf-8")
    try:
        result = chardet.detect(data)
    except Exception as e:
        print(f"FAIL: chardet.detect() raised: {e}", file=sys.stderr)
        return 1

    if not isinstance(result, dict) or "encoding" not in result:
        print(f"FAIL: detect() returned {result!r} (expected dict with "
              f"'encoding')", file=sys.stderr)
        return 1
    if result["encoding"] not in ("utf-8", "UTF-8"):
        print(f"FAIL: detect() encoding={result['encoding']!r} "
              f"(expected utf-8)", file=sys.stderr)
        return 1

    # version 存在
    if not hasattr(chardet, "__version__"):
        print("FAIL: chardet.__version__ missing", file=sys.stderr)
        return 1

    print(f"OK: chardet {chardet.__version__} real API ok "
          f"(detect('hello 世界') encoding={result['encoding']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
