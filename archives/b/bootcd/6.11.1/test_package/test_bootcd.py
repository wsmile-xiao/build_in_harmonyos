#!/usr/bin/env python3
"""bootcd test_package 校验：断言主脚本存在 + bash 语法可解析。

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

    bindir = os.path.join(pkg, "bin")
    tools = ["bootcd", "bootcdflopcp", "bootcdinitramfshook", "bootcdmodprobe",
             "bootcdoverlayfs", "bootcdproberoot", "bootcdrst",
             "runbootcdmodprobe", "runbootcdproberoot", "src2conf"]
    for t in tools:
        path = os.path.join(bindir, t)
        if not os.path.isfile(path):
            print(f"FAIL: 主脚本缺失 {path}", file=sys.stderr)
            return 1
        # bash 语法校验（OHOS 有 /system/bin/sh 或 bash，用 sh -n 验证可解析）
        r = subprocess.run(["/system/bin/sh", "-n", path],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"FAIL: {t} bash 语法错误: {r.stderr}", file=sys.stderr)
            return 1

    # .lib 共享库脚本也应打包
    libdir = os.path.join(pkg, "share", "bootcd")
    libs = [f for f in os.listdir(libdir) if f.endswith(".lib")] if os.path.isdir(libdir) else []
    if not libs:
        print("FAIL: 无 .lib 共享库脚本打包", file=sys.stderr)
        return 1

    print("OK: bootcd 主脚本存在 + bash 语法可解析 + .lib 共享库已打包")
    return 0


if __name__ == "__main__":
    sys.exit(main())
