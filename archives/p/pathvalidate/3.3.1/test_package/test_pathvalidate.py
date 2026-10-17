#!/usr/bin/env python3
"""pathvalidate consumer test (L0c + R34): standalone test source executed
via self.run from conanfile.py test().

R34: actually call the tested API — pathvalidate.sanitize_filename() on a
filename with invalid chars (path/filename sanitization, pure user-space).
Import failure or wrong result asserts fail.
"""
import sys


def main() -> int:
    try:
        import pathvalidate
    except ImportError as e:
        print(f"FAIL: cannot import pathvalidate: {e}", file=sys.stderr)
        return 1

    # 真实调用 API：文件名清理（纯用户态）
    try:
        cleaned = pathvalidate.sanitize_filename("a/b?c*")
    except Exception as e:
        print(f"FAIL: sanitize_filename() raised: {e}", file=sys.stderr)
        return 1

    if not isinstance(cleaned, str) or "/" in cleaned or "*" in cleaned:
        print(f"FAIL: sanitize_filename('a/b?c*')={cleaned!r} "
              f"(invalid chars not removed)", file=sys.stderr)
        return 1

    # 校验 API（valid filename 通过 / 非法失败）
    try:
        pathvalidate.validate_filename("hello.txt")  # 合法不应抛
    except Exception as e:
        print(f"FAIL: validate_filename('hello.txt') raised: {e}",
              file=sys.stderr)
        return 1

    print(f"OK: pathvalidate {getattr(pathvalidate, '__version__', '?')} "
          f"real API ok (sanitize_filename('a/b?c*')={cleaned!r} / "
          f"validate_filename('hello.txt'))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
