#!/usr/bin/env python3
"""configargparse consumer test (L0c + R34): standalone test source executed
via self.run from conanfile.py test().

R34: actually call the tested API — configargparse.ArgParser() +
add_argument() + parse_args() on argv (config-file+CLI parser, pure
user-space). Import failure or wrong result asserts fail.
"""
import sys


def main() -> int:
    try:
        import configargparse
    except ImportError as e:
        print(f"FAIL: cannot import configargparse: {e}", file=sys.stderr)
        return 1

    # 真实调用 API：ArgParser + add_argument + parse_args（纯用户态）
    try:
        parser = configargparse.ArgParser()
        parser.add_argument("--name", default="world")
        args = parser.parse_args(["--name", "harmony"])
    except Exception as e:
        print(f"FAIL: ArgParser API raised: {e}", file=sys.stderr)
        return 1

    if getattr(args, "name", None) != "harmony":
        print(f"FAIL: parse_args(['--name','harmony']).name="
              f"{getattr(args, 'name', None)!r} (expected 'harmony')",
              file=sys.stderr)
        return 1

    print(f"OK: configargparse {getattr(configargparse, '__version__', '?')} "
          f"real API ok (ArgParser.parse_args(['--name','harmony'])"
          f".name='harmony')")
    return 0


if __name__ == "__main__":
    sys.exit(main())
