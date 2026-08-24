#!/usr/bin/env python3
"""ruamel.yaml.clib consumer test (L0c + R34): standalone test source
executed via self.run from conanfile.py test().

The C extension (_ruamel_yaml.so) is designed to be used embedded in
the ruamel.yaml package (its init imports ruamel.yaml.error etc.) —
as a standalone accelerator package we verify the shared object is
complete and its module-init entry symbol is present (nm check; same
pattern as ats2-lang libatslib symbol verification). Real runtime
calls require the ruamel.yaml package at import time.

Usage: test_clib.py <site-packages>
"""
import os
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <site-packages>", file=sys.stderr)
        return 2
    site = sys.argv[1]
    so = os.path.join(site, "ruamel", "yaml", "clib",
                      "_ruamel_yaml.so")
    if not os.path.isfile(so):
        raise AssertionError(f"_ruamel_yaml.so missing in {site}")
    # R34: 验证 C 扩展完整性——模块初始化入口符号存在
    # (PyInit__ruamel_yaml——CPython 扩展加载入口)
    nm_cmd = "/data/service/hnp/bin/llvm-nm"
    if not os.path.isfile(nm_cmd):
        nm_cmd = "nm"
    nm = subprocess.run([nm_cmd, "-D", so], capture_output=True,
                        text=True, timeout=60)
    if nm.returncode != 0:
        raise AssertionError(f"nm failed on {so}: {nm.stderr[:200]}")
    if "PyInit__ruamel_yaml" not in nm.stdout:
        raise AssertionError("PyInit__ruamel_yaml entry missing "
                             "(C ext incomplete)")
    print("OK: ruamel.yaml.clib 0.2.15 (_ruamel_yaml.so + "
          "PyInit__ruamel_yaml entry verified)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
