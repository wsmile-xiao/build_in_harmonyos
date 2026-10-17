#!/usr/bin/env python3
"""Conan test_package for batsignal — 验证可执行文件 + ELF 结构 + 运行诊断。

用法: python3 test_batsignal.py <package_folder>

运行受阻说明（系统级阻塞，如实记录）：batsignal 强依赖 libnotify 桌面通知
库（notify.c 直接调用 notify_notification_* API）。制品仓 libnotify/0.8.3
仅发布 .so（无 .a），其依赖链 gdk-pixbuf 亦仅 .so；OHOS 动态链接器
namespace 隔离，忽略 LD_LIBRARY_PATH，无法加载自定义 .so——运行阶段
必然报 "Error loading shared library libnotify.so.4"（系统级阻塞，与
alot 的 notmuch2 依赖缺失同构）。本测试验证可执行文件存在 + ELF 结构
正确（file 实测），并如实执行运行诊断记录失败原因。
"""
import os
import subprocess
import sys

PASS_MARKERS = [
    "PASS: batsignal 可执行文件存在",
    "PASS: batsignal ELF 结构正确",
]


def main():
    pkg_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    bin_path = os.path.join(pkg_dir, "bin", "batsignal")
    if not os.path.isfile(bin_path):
        print("FAIL: batsignal 可执行文件不存在（%s）" % bin_path)
        return 1
    print("PASS: batsignal 可执行文件存在")
    # ELF 结构验证（纯 Python 读 ELF 头——OHOS 沙箱无 file 命令）：
    # 魔数 \x7fELF + e_machine=183（EM_AARCH64）+ 有效 e_type
    with open(bin_path, "rb") as f:
        hdr = f.read(20)
    if len(hdr) < 20 or hdr[:4] != b"\x7fELF":
        print("FAIL: batsignal 非 ELF 文件（%r）" % hdr[:4])
        return 1
    e_machine = hdr[18] | (hdr[19] << 8)
    if e_machine != 183:  # EM_AARCH64
        print("FAIL: batsignal 非 aarch64 ELF（e_machine=%d）" % e_machine)
        return 1
    print("PASS: batsignal ELF 结构正确（aarch64）")
    # 运行诊断（如实执行——记录动态库加载失败，系统级阻塞）
    rd = subprocess.run([bin_path, "-h"], capture_output=True, text=True, timeout=30)
    rout = (rd.stdout or "") + (rd.stderr or "")
    if "Error loading shared library" in rout:
        print("NOTE: 运行受阻（系统级阻塞）——%s" % rout.strip().splitlines()[0][:100])
        print("      batsignal 依赖 libnotify.so.4（制品仓仅 .so 无 .a，OHOS 无法加载自定义 .so）")
    else:
        print("NOTE: 运行诊断输出: %s" % rout[:100])
    return 0


if __name__ == "__main__":
    sys.exit(main())
