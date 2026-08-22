#!/usr/bin/env python3
"""text-unidecode consumer test (L0c + R34): standalone test source
executed via self.run from conanfile.py test().

R34: actually call the tested API — text_unidecode.unidecode() decode
(pure user-space).

Usage: test_text_unidecode.py <site-packages>
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <site-packages>", file=sys.stderr)
        return 2
    site = sys.argv[1]
    if not os.path.isdir(os.path.join(site, "text_unidecode")):
        raise AssertionError(f"text_unidecode package missing in {site}")
    sys.path.insert(0, site)
    # R34: 真实调用被测库 API
    from text_unidecode import unidecode

    out = unidecode("北京")
    if not out or "Bei Jing" not in out:
        raise AssertionError(f"unidecode decode failed: {out!r}")
    print(f"OK: text-unidecode 1.3 (unidecode decode ok: "
          f"{unidecode('北京')!r})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
