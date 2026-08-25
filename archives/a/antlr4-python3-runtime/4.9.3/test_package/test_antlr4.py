#!/usr/bin/env python3
"""antlr4-python3-runtime consumer test (L0c + R34): standalone test source
executed via self.run from conanfile.py test().

R34: actually call the tested API — antlr4.InputStream("...") builds an
input stream (pure user-space runtime object; antlr4 runtime has no
upstream test suite — generated-parser runtime, sdist contains no tests).
Import failure or API failure asserts fail.
"""
import sys


def main() -> int:
    try:
        import antlr4
    except ImportError as e:
        print(f"FAIL: cannot import antlr4: {e}", file=sys.stderr)
        return 1

    # 真实调用 API：InputStream 构造（纯用户态）
    try:
        stream = antlr4.InputStream("hello world")
        text = stream.getText(0, len("hello world") - 1)
        if text != "hello world":
            print(f"FAIL: InputStream.getText()={text!r} (expected "
                  f"'hello world')", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"FAIL: InputStream API raised: {e}", file=sys.stderr)
        return 1

    # CommonTokenStream 类存在（TokenStream 基础设施）
    if not hasattr(antlr4, "CommonTokenStream"):
        print("FAIL: antlr4.CommonTokenStream missing", file=sys.stderr)
        return 1

    print("OK: antlr4-python3-runtime 4.9.3 real API ok "
          "(InputStream('hello world') round-trip / CommonTokenStream)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
