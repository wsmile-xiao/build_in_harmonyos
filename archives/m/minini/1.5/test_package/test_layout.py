#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""minini 1.5 适配自检（M，非上游用例）。"""
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
    incdir = os.path.join(pkg, "include")
    libdir = os.path.join(pkg, "lib")
    print("适配自检（M）: %s" % pkg)

    print("\n[1] 静态库与公开头文件")
    libs = os.listdir(libdir) if os.path.isdir(libdir) else []
    check("libminIni.a" in libs, "lib/libminIni.a 交付", ",".join(libs))
    if "libminIni.a" in libs:
        with open(os.path.join(libdir, "libminIni.a"), "rb") as handle:
            check(handle.read(8).startswith(b"!<arch>"), "libminIni.a 是 ar 归档")
    check(os.path.isfile(os.path.join(incdir, "minIni.h")), "include/minIni.h")
    glue = [n for n in (os.listdir(incdir) if os.path.isdir(incdir) else [])
            if n.startswith("minGlue")]
    check(len(glue) >= 2, "glue 头文件交付（minGlue.h 等）", ",".join(sorted(glue)[:4]))

    print("\n[2] 内嵌源码与许可")
    src = os.path.join(pkg, "share", "minini", "minIni.c")
    check(os.path.isfile(src), "share/minini/minIni.c（上游『拖源码进工程』用法）")
    if os.path.isfile(src):
        text = open(src, encoding="utf-8", errors="ignore").read()
        check("ini_putbool(const mTCHAR" in text,
              "内嵌源码已含 TCHAR→mTCHAR 移植修正")
    licenses = os.listdir(os.path.join(pkg, "licenses")) if os.path.isdir(os.path.join(pkg, "licenses")) else []
    check("LICENSE" in licenses and "NOTICE" in licenses, "licenses/{LICENSE,NOTICE}")

    print("\n[3] 安装纯净性")
    stray = []
    for root, _dirs, files in os.walk(pkg):
        for name in files:
            if name.endswith((".o", ".lo", ".a.tmp")) or name.startswith("test_"):
                stray.append(os.path.join(os.path.relpath(root, pkg), name))
    check(not stray, "未夹带中间产物与测试程序", ",".join(stray[:4]))

    print("\n" + "=" * 56)
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
