#!/usr/bin/env python3
"""packaging consumer test (R34): module importable from package site-packages
+ real packaging API usage (Version parse + SpecifierSet match)."""
import os
import subprocess
import sys

SMOKE_PY = r'''
import sys
sys.path[0:0] = __import__("os").environ["PYTHONPATH"].split(":")
import packaging
print("packaging", packaging.__version__)

from packaging.version import Version
from packaging.specifiers import SpecifierSet

# 真实 API：Version 解析 + SpecifierSet 匹配
v = Version("1.2.3")
assert v.major == 1 and v.minor == 2 and v.micro == 3
assert str(v) == "1.2.3"

spec = SpecifierSet(">=1.0,<2.0")
assert spec.contains("1.5.0")
assert not spec.contains("2.0.0")

print("OK: packaging Version/SpecifierSet works")
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    site = os.path.join(pkg, "lib", "python3.12", "site-packages")
    mod = os.path.join(site, "packaging", "__init__.py")
    if not os.path.isfile(mod):
        print(f"FAIL: packaging module missing: {mod}", file=sys.stderr)
        return 1
    env = dict(os.environ)
    env["PYTHONPATH"] = site
    # 用调用本脚本的 python（必然存在且可执行——沙箱 PATH 无 python3 实测）
    py = sys.executable
    r = subprocess.run([py, "-c", SMOKE_PY], capture_output=True,
                       text=True, env=env)
    if r.returncode != 0:
        print(f"FAIL: packaging API: {r.stderr}", file=sys.stderr)
        return 1
    print(r.stdout.strip())
    print("OK: packaging module + Version/SpecifierSet real API works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
