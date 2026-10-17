#!/usr/bin/env python3
"""bobby test_package 校验：断言 bobby.theme.bash 存在 + bash 语法可解析。

用 Python 而非 shell（OHOS /system/bin/sh 对脚本语法兼容性差；且工作目录名
含括号 "(1)"，未加引号的路径会报 syntax error: unexpected '('）。
"""
import os
import subprocess
import sys


def main():
    if len(sys.argv) < 2:
        print("FAIL: no package dir provided", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    theme = os.path.join(pkg, "share", "bobby", "bobby.theme.bash")
    if not os.path.isfile(theme):
        print(f"FAIL: bobby.theme.bash missing: {theme}", file=sys.stderr)
        return 1
    # bash 语法校验
    r = subprocess.run(["/system/bin/sh", "-n", theme],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL: bobby.theme.bash 语法错误: {r.stderr}", file=sys.stderr)
        return 1
    print("OK: bobby.theme.bash 存在 + bash 语法可解析")
    return 0


if __name__ == "__main__":
    sys.exit(main())
