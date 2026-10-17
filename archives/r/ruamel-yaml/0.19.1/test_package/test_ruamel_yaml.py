#!/usr/bin/env python3
"""ruamel.yaml consumer test (L0c + R34): standalone test source
executed via self.run from conanfile.py test().

R34: actually call the tested API — ruamel.yaml YAML roundtrip
(pure user-space).

Usage: test_ruamel_yaml.py <site-packages>
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <site-packages>", file=sys.stderr)
        return 2
    site = sys.argv[1]
    if not os.path.isdir(os.path.join(site, "ruamel", "yaml")):
        raise AssertionError(f"ruamel/yaml package missing in {site}")
    sys.path.insert(0, site)
    # R34: 真实调用被测库 API（YAML 解析 + 往返保留注释）
    import ruamel.yaml

    yaml = ruamel.yaml.YAML()
    data = yaml.load("a: 1\nb: [1, 2]\n")
    if data["a"] != 1 or data["b"] != [1, 2]:
        raise AssertionError(f"unexpected parse: {data!r}")
    # roundtrip（dump 后重新解析）
    import io
    buf = io.StringIO()
    yaml.dump(data, buf)
    data2 = yaml.load(buf.getvalue())
    if data2["a"] != 1:
        raise AssertionError(f"roundtrip failed: {data2!r}")
    print(f"OK: ruamel.yaml 0.19.1 (load + roundtrip ok)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
