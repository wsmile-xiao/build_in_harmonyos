#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tdom 0.9.6 适配自检（M，非上游用例）。

上游官方测试（tests/all.tcl 的 tcltest 套件）在 recipe 的 build() 里用 `make check`
真跑；完整消费者用例是 test_tdom.tcl。这里检查的是 **conan 包的交付形态**：
TEA 布局（lib/tdom0.9.6/ 下 .so + stub + Tcl 脚本）、公开头、许可、纯净性。
"""
from __future__ import print_function

import os
import sys

FAILURES = []
COUNT = [0]
TEA_FILES = ("libtdom0.9.6.so", "libtdomstub0.9.6.a", "pkgIndex.tcl", "tdom.tcl")


def check(ok, label, detail=""):
    COUNT[0] += 1
    if not ok:
        FAILURES.append(label)
    print("  [%s] %s%s" % ("ok" if ok else "FAIL", label, ("  " + detail) if detail else ""))
    return ok


def main(argv):
    pkg = argv[1]
    teadir = os.path.join(pkg, "lib", "tdom0.9.6")
    incdir = os.path.join(pkg, "include")
    print("适配自检（M）: %s" % pkg)

    print("\n[1] TEA 布局：lib/tdom0.9.6/ 下交付扩展与 Tcl 侧脚本")
    for name in TEA_FILES:
        path = os.path.join(teadir, name)
        check(os.path.isfile(path), "lib/tdom0.9.6/%s" % name,
              "%d 字节" % os.path.getsize(path) if os.path.isfile(path) else "缺失")

    print("\n[2] 扩展是真正的 ELF 共享库（不是占位文件）")
    so = os.path.join(teadir, "libtdom0.9.6.so")
    if os.path.isfile(so):
        with open(so, "rb") as handle:
            head = handle.read(20)
        check(head[:4] == b"\x7fELF", "libtdom0.9.6.so 有 ELF magic")
        check(len(head) >= 18 and head[16] == 3, "ELF 类型 = ET_DYN（共享对象）",
              "e_type=%d" % (head[16] if len(head) >= 18 else -1))
        check(os.path.getsize(so) > 100 * 1024, "扩展体积 > 100KB（含 expat 解析器）",
              "%d 字节" % os.path.getsize(so))
    else:
        check(False, "libtdom0.9.6.so 存在")

    print("\n[3] Tcl 侧脚本可被 package require 使用")
    pkgindex = os.path.join(teadir, "pkgIndex.tcl")
    tdomtcl = os.path.join(teadir, "tdom.tcl")
    if os.path.isfile(pkgindex):
        body = open(pkgindex, encoding="utf-8", errors="replace").read()
        check("tdom" in body and "0.9.6" in body, "pkgIndex.tcl 注册 tdom 0.9.6")
    else:
        check(False, "pkgIndex.tcl 存在")
    if os.path.isfile(tdomtcl):
        body = open(tdomtcl, encoding="utf-8", errors="replace").read()
        check(len(body) > 1000 and "proc" in body, "tdom.tcl 是 Tcl 侧实现（非空壳）",
              "%d 字节" % len(body))
    else:
        check(False, "tdom.tcl 存在")

    print("\n[4] 公开头 / TEA 配置 / 许可")
    check(os.path.isfile(os.path.join(incdir, "tdom.h")), "include/tdom.h")
    check(os.path.isfile(os.path.join(pkg, "lib", "tdomConfig.sh")), "lib/tdomConfig.sh")
    check(os.path.isfile(os.path.join(pkg, "licenses", "LICENSE")), "licenses/LICENSE（MPL-2.0）")

    print("\n[5] 安装纯净性（无可执行文件/构建中间产物/隐藏文件/意外的 usr 前缀）")
    bins = os.listdir(os.path.join(pkg, "bin")) if os.path.isdir(os.path.join(pkg, "bin")) else []
    check(not bins, "无 bin/（tdom 不装可执行文件，故不需要 commands.json）", ",".join(bins))
    check(not os.path.isdir(os.path.join(pkg, "usr")), "无 usr/ 前缀（TEA 安装路径已归位）")
    junk = []
    hidden = []
    for root, dirs, files in os.walk(pkg):
        for name in files:
            if name.endswith((".o", ".lo", ".obj", ".pdb")) or name in ("config.log", "build.ninja"):
                junk.append(os.path.relpath(os.path.join(root, name), pkg))
        for name in dirs + files:
            if name.startswith("."):
                hidden.append(os.path.relpath(os.path.join(root, name), pkg))
    check(not junk, "无构建中间产物", ",".join(junk[:6]))
    check(not hidden, "无隐藏文件（JC5）", ",".join(hidden[:6]))
    check(not os.path.isdir(os.path.join(pkg, "tests")), "未夹带上游测试用例目录")

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
