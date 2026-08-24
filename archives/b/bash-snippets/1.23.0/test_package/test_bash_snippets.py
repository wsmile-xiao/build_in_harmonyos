#!/usr/bin/env python3
"""Conan test_package for bash-snippets — 验证工具脚本真实可执行。"""
import os
import subprocess
import sys


def main():
    pkg_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    bin_dir = os.path.join(pkg_dir, "bin")
    tools = ["bash-snippets", "cheat", "crypt", "currency", "todo", "weather"]
    fails = 0

    for t in tools:
        p = os.path.join(bin_dir, t)
        if not os.path.isfile(p):
            print(f"FAIL: bin/{t} 缺失")
            fails += 1
            continue
        # 真实执行 -v（版本输出——不依赖网络）
        r = subprocess.run(["/data/service/hnp/bin/bash", p, "-v"],
                           capture_output=True, text=True, timeout=60)
        out = (r.stdout or "") + (r.stderr or "")
        if "Version" in out:
            print(f"PASS: {t} -v 输出 Version")
        else:
            print(f"FAIL: {t} -v 无 Version 输出: {out.strip()[:80]}")
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
