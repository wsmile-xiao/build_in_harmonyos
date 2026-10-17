#!/usr/bin/env python3
"""tcolorpy consumer test (L0c + R34): standalone test source executed
via self.run from conanfile.py test().

R34: actually call the tested API — tcolorpy.Color('#ff0000') constructs a
Color object and .red/.green/.blue expose parsed channels (upstream
test_color.py usage: `color = Color(value); color.red/...`). Import
failure or wrong result asserts fail.
"""
import sys


def main() -> int:
    try:
        import tcolorpy
    except ImportError as e:
        print(f"FAIL: cannot import tcolorpy: {e}", file=sys.stderr)
        return 1

    # 真实调用 API：Color 类构造 + RGB 通道解析（上游 test_color.py 用法）
    try:
        color = tcolorpy.Color("#ff0000")
    except Exception as e:
        print(f"FAIL: Color('#ff0000') raised: {e}", file=sys.stderr)
        return 1

    try:
        red, green, blue = color.red, color.green, color.blue
    except AttributeError as e:
        print(f"FAIL: Color has no red/green/blue: {e}", file=sys.stderr)
        return 1
    if (red, green, blue) != (255, 0, 0):
        print(f"FAIL: Color('#ff0000').rgb={(red, green, blue)!r} "
              f"(expected (255, 0, 0))", file=sys.stderr)
        return 1

    print(f"OK: tcolorpy {getattr(tcolorpy, '__version__', '?')} real API ok "
          f"(Color('#ff0000').rgb={(red, green, blue)!r})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
