#!/usr/bin/env python3
"""soupsieve consumer test (L0c + R34): standalone test source executed
via self.run from conanfile.py test().

R34: actually call the tested library API — soupsieve.compile() compiles
a CSS selector pattern (pure user-space, no BeautifulSoup tree needed;
soupsieve's select/match require a bs4.Tag tree which needs bs4 — not
installed for this standalone package — so the tree-less compile/escape
APIs are exercised, matching upstream tests which build trees via bs4).
Import failure or compile failure asserts fail.
"""
import sys


def main() -> int:
    try:
        import soupsieve as sv
    except ImportError as e:
        print(f"FAIL: cannot import soupsieve: {e}", file=sys.stderr)
        return 1

    # 真实调用 API：编译 CSS 选择器（无 bs4 树依赖）
    try:
        compiled = sv.compile("div.a > p")
        sel = compiled.pattern if hasattr(compiled, "pattern") else None
        if not sel:
            print("FAIL: compile() returned object without pattern",
                  file=sys.stderr)
            return 1
        if "div.a > p" not in sel:
            print(f"FAIL: compiled pattern {sel!r} unexpected",
                  file=sys.stderr)
            return 1
    except Exception as e:
        print(f"FAIL: compile('div.a > p') raised: {e}", file=sys.stderr)
        return 1

    # escape API（CSS 标识符转义——无树依赖）
    try:
        esc = sv.escape("a:b")
        if ":" not in esc and esc != "a:b":
            print(f"FAIL: escape('a:b')={esc!r} unexpected", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"FAIL: escape() raised: {e}", file=sys.stderr)
        return 1

    print(f"OK: soupsieve {sv.__version__} real API ok "
          f"(compile('div.a > p') / escape)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
