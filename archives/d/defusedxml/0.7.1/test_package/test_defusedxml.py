#!/usr/bin/env python3
"""defusedxml consumer test (L0c + R34): standalone test source executed
via self.run from conanfile.py test().

R34: actually call the tested API — defusedxml.ElementTree safe XML
parsing (pure user-space, core functionality — no lxml needed).

Usage: test_defusedxml.py <site-packages>
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <site-packages>", file=sys.stderr)
        return 2
    site = sys.argv[1]
    if not os.path.isdir(os.path.join(site, "defusedxml")):
        raise AssertionError(f"defusedxml package missing in {site}")
    sys.path.insert(0, site)
    # R34: 真实调用被测库 API（核心 ElementTree——不涉及可选 lxml）
    from defusedxml import ElementTree as DET

    root = DET.fromstring("<root><item>safe</item></root>")
    if root.tag != "root" or root[0].tag != "item":
        raise AssertionError(f"defusedxml parse failed: {root.tag}")
    print(f"OK: defusedxml 0.7.1 (ElementTree safe parse ok: "
          f"{root.tag}/{root[0].tag})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
