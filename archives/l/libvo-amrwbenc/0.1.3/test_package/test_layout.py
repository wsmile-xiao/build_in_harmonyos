#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""libvo-amrwbenc 0.1.3 适配自检（M，非上游用例）。

上游 0.1.3 没有测试目录/测试目标（N=0），官方验证方式就是用它自己的 CLI 编一段
音频；这里检查的是 **conan 包的交付形态**：库、公开头、pkg-config 契约、
命令行工具、许可、安装纯净性。
"""
from __future__ import print_function

import os
import sys

FAILURES = []
COUNT = [0]


def check(ok, label, detail=""):
    COUNT[0] += 1
    if not ok:
        FAILURES.append(label)
    print("  [%s] %s%s" % ("ok" if ok else "FAIL", label, ("  " + detail) if detail else ""))
    return ok


def main(argv):
    pkg = argv[1]
    libdir = os.path.join(pkg, "lib")
    incdir = os.path.join(pkg, "include", "vo-amrwbenc")
    bindir = os.path.join(pkg, "bin")
    print("适配自检（M）: %s" % pkg)

    libs = os.listdir(libdir) if os.path.isdir(libdir) else []
    print("\n[1] 库与公开头文件")
    found = [n for n in libs if n.startswith("libvo-amrwbenc.so") or n.startswith("libvo-amrwbenc.a")]
    check(bool(found), "lib/libvo-amrwbenc.{so,a} 交付", ",".join(sorted(found)[:4]))
    elf = sorted(n for n in found if n.endswith(".so"))
    if elf:
        with open(os.path.join(libdir, elf[0]), "rb") as handle:
            check(handle.read(4) == b"\x7fELF", "共享库是 ELF（可被链接）", elf[0])
    elif found:
        with open(os.path.join(libdir, sorted(found)[0]), "rb") as handle:
            check(handle.read(8).startswith(b"!<arch>"), "静态库是 ar 归档", sorted(found)[0])
    check(os.path.isfile(os.path.join(incdir, "enc_if.h")),
          "include/vo-amrwbenc/enc_if.h（公开 C API）")

    print("\n[2] pkg-config 契约（消费者按 .pc 取编译参数）")
    pc = os.path.join(libdir, "pkgconfig", "vo-amrwbenc.pc")
    text = open(pc, encoding="utf-8").read() if os.path.isfile(pc) else ""
    check("Name: VisualOn AMR-WB encoder" in text and "Version: 0.1.3" in text
          and "-lvo-amrwbenc" in text,
          "lib/pkgconfig/vo-amrwbenc.pc（Name/Version/Libs 正确）")

    print("\n[3] 命令行工具（本包同时交付 amrwb-enc）")
    cli = os.path.join(bindir, "amrwb-enc")
    check(os.path.isfile(cli) and os.access(cli, os.X_OK),
          "bin/amrwb-enc 可执行")
    if os.path.isfile(cli):
        with open(cli, "rb") as handle:
            check(handle.read(4) == b"\x7fELF", "amrwb-enc 是 ELF 可执行文件")

    print("\n[4] 许可与安装纯净性")
    licenses = os.path.join(pkg, "licenses")
    names = os.listdir(licenses) if os.path.isdir(licenses) else []
    copying = os.path.join(licenses, "COPYING")
    check("NOTICE" in names and os.path.isfile(copying), "licenses/{COPYING,NOTICE} 交付")
    if os.path.isfile(copying):
        check("Apache License" in open(copying, encoding="utf-8", errors="ignore").read(),
              "COPYING 声明 Apache-2.0")
    stray = []
    for root, _dirs, files in os.walk(pkg):
        for name in files:
            if name.endswith((".c", ".cc", ".cpp", ".o", ".lo", ".in")):
                stray.append(os.path.join(os.path.relpath(root, pkg), name))
    check(not stray, "未夹带源码/中间产物（.c/.o/.lo/.in）",
          "" if not stray else ",".join(stray[:4]))

    print("\n" + "=" * 60)
    print("适配自检 %d 条，通过 %d 条，失败 %d 条"
          % (COUNT[0], COUNT[0] - len(FAILURES), len(FAILURES)))
    if FAILURES:
        for item in FAILURES:
            print("  - %s" % item)
        return 1
    print("[test] %d/%d assertions passed" % (COUNT[0], COUNT[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
