#!/usr/bin/env python3
"""Conan test_package for bsdmainutils — 验证 calendar + ncal 可执行 + 真实运行。

用法: python3 test_bsdmainutils.py <package_folder>

calendar 验证方式说明：无参数运行需要 ~/.calendar/calendar 且依赖
/usr/libexec/tradcpp（沙箱无）——改为 `-h` 触发 usage 输出（getopt
default 分支，实测输出 "usage: calendar [-abw] ..."）；ncal 无参数
真实运行输出当月日历（实测通过）。
"""
import os
import subprocess
import sys

PASS_MARKERS = [
    "PASS: calendar 可执行文件存在",
    "PASS: ncal 可执行文件存在",
    "PASS: calendar usage 输出真实",
    "PASS: ncal 真实运行输出（当月日历）",
]


def main():
    pkg_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    calendar_bin = os.path.join(pkg_dir, "bin", "calendar")
    ncal_bin = os.path.join(pkg_dir, "bin", "ncal")
    for name, path in (("calendar", calendar_bin), ("ncal", ncal_bin)):
        if not os.path.isfile(path):
            print("FAIL: %s 可执行文件不存在（%s）" % (name, path))
            return 1
        print("PASS: %s 可执行文件存在" % name)
    # calendar -h：getopt default 分支触发 usage（沙箱无 ~/.calendar 与
    # /usr/libexec/tradcpp——无参数运行会报 "no calendar file"）
    r = subprocess.run([calendar_bin, "-h"], capture_output=True, text=True, timeout=30)
    out = (r.stdout or "") + (r.stderr or "")
    if "usage" not in out.lower():
        print("FAIL: calendar 无 usage 输出（rc=%d，out=%s）" % (r.returncode, out[:120]))
        return 1
    print("PASS: calendar usage 输出真实")
    # ncal 无参数真实运行——输出当月日历（实测通过）
    r = subprocess.run([ncal_bin], capture_output=True, text=True, timeout=30)
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0 or not out.strip():
        print("FAIL: ncal 运行失败（rc=%d，out=%s）" % (r.returncode, out[:120]))
        return 1
    print("PASS: ncal 真实运行输出（当月日历）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
