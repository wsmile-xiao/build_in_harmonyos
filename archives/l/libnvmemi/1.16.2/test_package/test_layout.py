#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""libnvmemi 1.16.2 适配自检（M，非上游用例）。

上游官方测试（test/mi、test/mi-mctp 等 31 个 meson 用例）在 recipe 的 build() 里
真跑；完整消费者用例是 test_libnvme_mi.c（见 MANIFEST.yml）。这里检查的是
**conan 包的交付形态**：MI 库/公共头/pkg-config 契约/许可是否齐全、是否误带
同源码树的 libnvme.so、是否夹带上游测试产物。
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
    incdir = os.path.join(pkg, "include")
    libs = sorted(os.listdir(libdir)) if os.path.isdir(libdir) else []
    print("适配自检（M）: %s" % pkg)

    print("\n[1] NVMe-MI 共享库交付（含 soname 链）")
    mi = [n for n in libs if n.startswith("libnvme-mi.so")]
    check(bool(mi), "lib/libnvme-mi.so*", ",".join(mi))
    check(any(n.startswith("libnvme-mi.so.1.") for n in mi),
          "带版本号的 .so（soname 链完整）", ",".join(n for n in mi if ".so.1" in n))
    for n in mi:
        path = os.path.join(libdir, n)
        check(os.path.islink(path) or os.path.isfile(path), "lib/%s 可用" % n)

    print("\n[2] 未误带同源码树的 A 面库 libnvme（本包只交付 MI 库）")
    check(not [n for n in libs if n.startswith("libnvme.so")], "lib/ 无 libnvme.so*", ",".join(libs))
    check(not os.path.exists(os.path.join(incdir, "libnvme.h")), "include/ 无 libnvme.h")

    print("\n[3] 消费者需要的公共头文件（libnvme-mi.h 的包含闭包）")
    for rel in ("libnvme-mi.h", os.path.join("nvme", "mi.h"), os.path.join("nvme", "types.h"),
                os.path.join("nvme", "tree.h"), os.path.join("nvme", "log.h"),
                os.path.join("nvme", "util.h"), os.path.join("nvme", "ioctl.h")):
        check(os.path.isfile(os.path.join(incdir, rel)), "include/%s" % rel)

    print("\n[4] pkg-config 契约可重定位（meson 以 --prefix=/ 安装，前缀必须重写）")
    pc = os.path.join(libdir, "pkgconfig", "libnvme-mi.pc")
    check(os.path.isfile(pc), "lib/pkgconfig/libnvme-mi.pc 交付")
    if os.path.isfile(pc):
        body = open(pc).read()
        check("libnvme-mi" in body and "-lnvme-mi" in body, "pkg-config 名称与库名正确")
        check("prefix=${pcfiledir}/../.." in body, "prefix 已改为相对 pcfiledir")
        check("prefix=/" not in body.replace("prefix=${pcfiledir}/../..", ""),
              "无残留的绝对前缀 prefix=/")

    print("\n[5] 许可与安装纯净性")
    check(os.path.isfile(os.path.join(pkg, "licenses", "COPYING")),
          "licenses/COPYING（LGPL-2.1-or-later）")
    junk = []
    hidden = []
    for root, dirs, files in os.walk(pkg):
        for n in files:
            if (n.startswith("test-") or n.endswith((".o", ".a", ".pdb", ".la"))
                    or n in ("meson.build", "meson-private", "build.ninja")):
                junk.append(os.path.relpath(os.path.join(root, n), pkg))
        # 注意判定对象是 walk 出来的**条目名**（目录名/文件名），不是 dirpath：
        # dirpath 在 Conan 2 下是绝对路径，对它判 startswith(".") 恒为 False。
        for n in list(dirs) + list(files):
            if n.startswith("."):
                hidden.append(os.path.relpath(os.path.join(root, n), pkg))
    check(not junk, "无上游测试程序/构建中间产物", ",".join(junk[:6]))
    check(not hidden, "无隐藏文件残留（JC5）", ",".join(hidden[:6]))

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
