#!/usr/bin/env python3
"""construct consumer test（R34：真实调用被测库 API）。

只依赖 construct 自身（无 extras），覆盖解析/构建双向与嵌套结构：
  * Struct + Int8ub/Int16ub：build 出精确字节、parse 回来
  * Array + GreedyRange：变长解析
  * 校验 build→parse 往返一致
导入失败或任一断言失败即返回非零。
"""
import sys


def main() -> int:
    try:
        import construct
    except ImportError as e:
        print(f"FAIL: cannot import construct: {e}", file=sys.stderr)
        return 1

    try:
        from construct import Struct, Int8ub, Int16ub, Array, GreedyRange, Byte
    except Exception as e:
        print(f"FAIL: cannot import construct API: {e}", file=sys.stderr)
        return 1

    # 1) 定长结构：build → 精确字节；parse → 还原
    try:
        fmt = Struct("a" / Int8ub, "b" / Int16ub)
        data = fmt.build({"a": 1, "b": 2})
        if data != b"\x01\x00\x02":
            print(f"FAIL: build() = {data!r}, expected b'\\x01\\x00\\x02'",
                  file=sys.stderr)
            return 1
        parsed = fmt.parse(data)
        if parsed.a != 1 or parsed.b != 2:
            print(f"FAIL: parse() = {parsed!r}", file=sys.stderr)
            return 1
        if fmt.sizeof() != 3:
            print(f"FAIL: sizeof() = {fmt.sizeof()}, expected 3", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"FAIL: Struct API raised: {e}", file=sys.stderr)
        return 1

    # 2) 变长：Array(3) 与 GreedyRange 往返
    try:
        arr = Array(3, Byte)
        if arr.build([1, 2, 3]) != b"\x01\x02\x03":
            print("FAIL: Array(3, Byte) build wrong", file=sys.stderr)
            return 1
        if list(arr.parse(b"\x01\x02\x03")) != [1, 2, 3]:
            print("FAIL: Array(3, Byte) parse wrong", file=sys.stderr)
            return 1
        gr = GreedyRange(Byte)
        if list(gr.parse(b"\x0a\x0b\x0c\x0d")) != [10, 11, 12, 13]:
            print("FAIL: GreedyRange(Byte) parse wrong", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"FAIL: Array/GreedyRange API raised: {e}", file=sys.stderr)
        return 1

    print(f"OK: construct {construct.__version__} real API ok "
          f"(Struct/Array/GreedyRange build+parse round-trip)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
