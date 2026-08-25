#!/usr/bin/env python3
"""soupsieve consumer test (L0c + R34): standalone test source executed
via self.run from conanfile.py test().

R34: actually call the tested API — soupsieve.compile() compiles a CSS
selector pattern (pure user-space; soupsieve 2.4.1 does not import bs4
at top level, so standalone import works — unlike 2.9.2).
Import failure or compile failure asserts fail.
"""
import sys


def main() -> int:
    try:
        import soupsieve as sv
    except ImportError as e:
        print(f"FAIL: cannot import soupsieve: {e}", file=sys.stderr)
        return 1

    # 真实调用 API：编译 CSS 选择器（纯用户态，无 bs4 依赖）
    try:
        compiled = sv.compile("div.a > p")
        sel = compiled.pattern if hasattr(compiled, "pattern") else None
        if not sel or "div.a > p" not in sel:
            print(f"FAIL: compile() pattern={sel!r} unexpected",
                  file=sys.stderr)
            return 1
    except Exception as e:
        print(f"FAIL: compile('div.a > p') raised: {e}", file=sys.stderr)
        return 1

    print(f"OK: soupsieve {sv.__version__} real API ok "
          f"(compile('div.a > p'))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
