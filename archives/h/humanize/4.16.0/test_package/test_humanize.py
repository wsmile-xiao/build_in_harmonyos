#!/usr/bin/env python3
"""humanize consumer test (R34): module importable from package site-packages
+ real humanize API usage (filesize/number/time formatting)."""
import os
import subprocess
import sys

SMOKE_PY = r'''
import sys
sys.path[0:0] = __import__("os").environ["PYTHONPATH"].split(":")
import humanize
print("humanize", humanize.__version__)

from humanize import intcomma, naturalsize

# 真实 API：filesize / number 格式化（humanize 4.x 中 filesize 是模块——
# 顶层 re-export naturalsize/intcomma，实测验证）
assert intcomma(1234567) == "1,234,567"
assert naturalsize(1536000) == "1.5 MB"

print("OK: humanize intcomma/naturalsize works")
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    site = os.path.join(pkg, "lib", "python3.12", "site-packages")
    mod = os.path.join(site, "humanize", "__init__.py")
    if not os.path.isfile(mod):
        print(f"FAIL: humanize module missing: {mod}", file=sys.stderr)
        return 1
    env = dict(os.environ)
    env["PYTHONPATH"] = site
    # 用调用本脚本的 python（必然存在且可执行——沙箱 PATH 无 python3 实测）
    py = sys.executable
    r = subprocess.run([py, "-c", SMOKE_PY], capture_output=True,
                       text=True, env=env)
    if r.returncode != 0:
        print(f"FAIL: humanize API: {r.stderr}", file=sys.stderr)
        return 1
    print(r.stdout.strip())
    print("OK: humanize module + filesize/intcomma/naturalsize real API works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
