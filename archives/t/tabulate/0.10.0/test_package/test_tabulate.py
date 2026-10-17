#!/usr/bin/env python3
"""tabulate consumer test (L0c + R34): standalone test source executed
via self.run from conanfile.py test().

R34: actually call the tested API — tabulate.tabulate() formats tabular
data (pure user-space). Import failure or wrong result asserts fail.
"""
import sys


def main() -> int:
    try:
        import tabulate
    except ImportError as e:
        print(f"FAIL: cannot import tabulate: {e}", file=sys.stderr)
        return 1

    # 真实调用 API：表格格式化（纯用户态）
    try:
        table = tabulate.tabulate(
            [["a", 1], ["b", 2]], headers=["letter", "num"])
    except Exception as e:
        print(f"FAIL: tabulate() raised: {e}", file=sys.stderr)
        return 1

    if not isinstance(table, str):
        print(f"FAIL: tabulate() returned {type(table)!r} (expected str)",
              file=sys.stderr)
        return 1
    # 输出应包含表头与分隔线
    if "letter" not in table or "num" not in table:
        print(f"FAIL: tabulate() output missing headers: {table!r}",
              file=sys.stderr)
        return 1
    if "---" not in table and "===" not in table:
        print(f"FAIL: tabulate() output missing separator: {table!r}",
              file=sys.stderr)
        return 1

    print(f"OK: tabulate {getattr(tabulate, '__version__', '?')} real API ok "
          f"(tabulate(headers=['letter','num'])->{len(table)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
