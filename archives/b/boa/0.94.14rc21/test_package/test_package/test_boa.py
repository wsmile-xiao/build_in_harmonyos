#!/usr/bin/env python3
"""Conan test_package for boa — 验证 boa 可执行 + usage 输出真实可用。

用法: python3 test_boa.py <package_folder>
"""
import os
import subprocess
import sys

PASS_MARKERS = [
    "PASS: boa 可执行文件存在",
    "PASS: boa usage 输出真实",
]


def main():
    pkg_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    boa_bin = os.path.join(pkg_dir, "bin", "boa")
    if not os.path.isfile(boa_bin):
        print("FAIL: boa 可执行文件不存在（%s）" % boa_bin)
        return 1
    print("PASS: boa 可执行文件存在")
    # boa 无 --help 选项（getopt c:dl:f:r:）——非法选项触发 usage 输出
    # （boa.c getopt default 分支调用 usage() 后退出）——沙箱无 /etc/boa，
    # 无参数运行会 chdir /etc/boa 失败——用 -x 触发 usage 更可靠
    r = subprocess.run([boa_bin, "-x"], capture_output=True, text=True, timeout=30)
    out = (r.stdout or "") + (r.stderr or "")
    if "Usage" not in out and "usage" not in out:
        print("FAIL: boa 无 usage 输出（rc=%d，out=%s）" % (r.returncode, out[:120]))
        return 1
    print("PASS: boa usage 输出真实")
    return 0


if __name__ == "__main__":
    sys.exit(main())
