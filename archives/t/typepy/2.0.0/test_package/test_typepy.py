#!/usr/bin/env python3
"""typepy consumer test (R34): real API — Integer TypeChecker + version."""
import sys


def main() -> int:
    import typepy

    if typepy.__version__ != "2.0.0":
        print(f"FAIL: typepy version {typepy.__version__}", file=sys.stderr)
        return 1
    # 真实 API：Integer TypeChecker（参照上游 test/checker/
    # test_checker_integer.py——mbstrdecoder 依赖链真实运行）
    ok_int = typepy.Integer("42", typepy.StrictLevel.MIN).is_type()
    ok_str = typepy.Integer("abc", typepy.StrictLevel.MIN).is_type()
    if not ok_int or ok_str:
        print(f"FAIL: Integer check ok_int={ok_int} ok_str={ok_str}",
              file=sys.stderr)
        return 1
    print("OK: typepy 2.0.0 (Integer TypeChecker ok, mbstrdecoder linked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
