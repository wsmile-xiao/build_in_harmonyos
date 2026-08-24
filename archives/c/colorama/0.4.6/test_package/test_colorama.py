#!/usr/bin/env python3
"""colorama consumer test (L0c + R34): standalone test source executed
via self.run from conanfile.py test().

R34: actually call the tested API — colorama Fore/Style/init (pure
user-space).

Usage: test_colorama.py <site-packages>
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <site-packages>", file=sys.stderr)
        return 2
    site = sys.argv[1]
    if not os.path.isdir(os.path.join(site, "colorama")):
        raise AssertionError(f"colorama package missing in {site}")
    sys.path.insert(0, site)
    # R34: 真实调用被测库 API
    import colorama
    from colorama import Fore, Style, init

    init()
    # Fore.RED 等颜色码 + 包裹字符串
    s = f"{Fore.RED}red{Style.RESET_ALL}"
    if "\x1b[" not in s:
        raise AssertionError(f"no ANSI escape in output: {s!r}")
    # ansi 码值核验（Fore.RED 应为 31 色）
    if Fore.RED != "\x1b[31m":
        raise AssertionError(f"unexpected Fore.RED: {Fore.RED!r}")
    print(f"OK: colorama 0.4.6 (init + Fore.RED + Style.RESET_ALL ok)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
