#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""d0-blind-id 1.0 适配自检（M，非上游用例）。

检查 conan 包的交付形态：两个库（ELF 共享对象）、公开头、pkg-config 契约、
bin/blind_id（R38 申报在源码树侧）、3-clause BSD 许可、无 libtool .la /
构建残留 / 隐藏文件。

注：R38 的 `commands.json` 是**源码树级**申报文件（仓库 2000+ 配方同款，
不随 conan 包装发行），所以这里按「脚本位置向上两级/三级」去找它——
conan 的 test_package 是直接从源码树跑的（CI 实测路径
`<repo>/archives/d/d0-blind-id/1.0/test_package/conanfile.py`）。
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


def is_elf_shared(path):
    try:
        with open(path, "rb") as handle:
            head = handle.read(20)
    except IOError:
        return False
    return head[:4] == b"\x7fELF" and len(head) >= 18 and head[16] == 3


def commands_json_candidates():
    """R38 申报文件的候选位置（源码树级，按仓库标准顺序）。

    软件级 `archives/<首字母>/<包名>/commands.json` 是仓库标准位置（L0k 与
    ci/conan/hooks/pre-commit 都只认它）；本包同时在版本目录保留了一份。
    脚本自身位于 `<版本目录>/test_package/`，所以：
      软件级 = dirname(dirname(脚本目录))/commands.json
      版本级 = dirname(脚本目录)/commands.json
    """
    here = os.path.dirname(os.path.abspath(__file__))
    version_dir = os.path.dirname(here)
    software_dir = os.path.dirname(version_dir)
    return [os.path.join(software_dir, "commands.json"),
            os.path.join(version_dir, "commands.json")]


def main(argv):
    pkg = argv[1]
    libdir = os.path.join(pkg, "lib")
    incdir = os.path.join(pkg, "include", "d0_blind_id")
    bindir = os.path.join(pkg, "bin")
    libs = sorted(os.listdir(libdir)) if os.path.isdir(libdir) else []
    print("适配自检（M）: %s" % pkg)

    print("\n[1] 两个库交付齐全且是 ELF 共享对象")
    for name in ("libd0_blind_id.so", "libd0_rijndael.so"):
        found = [n for n in libs if n.startswith(name)]
        check(bool(found), "lib/%s*" % name, ",".join(found[:3]))
        for n in found:
            p = os.path.join(libdir, n)
            if os.path.isfile(p) and not os.path.islink(p):
                check(is_elf_shared(p), "lib/%s 是 ELF ET_DYN" % n,
                      "%d 字节" % os.path.getsize(p))
                break

    print("\n[2] 公开头文件（消费者只需 #include <d0_blind_id/d0_blind_id.h>）")
    for rel in ("d0_blind_id.h", "d0.h", "d0_rijndael.h"):
        check(os.path.isfile(os.path.join(incdir, rel)), "include/d0_blind_id/%s" % rel)

    print("\n[3] pkg-config 契约可重定位")
    for name in ("d0_blind_id.pc", "d0_rijndael.pc"):
        pc = os.path.join(libdir, "pkgconfig", name)
        check(os.path.isfile(pc), "lib/pkgconfig/%s" % name)
        if os.path.isfile(pc):
            body = open(pc).read()
            check("prefix=${pcfiledir}/../.." in body,
                  "lib/pkgconfig/%s 的 prefix 已重写为相对 pcfiledir" % name)

    print("\n[4] CLI 交付与 R38 申报（源码树级）")
    check(os.path.isfile(os.path.join(bindir, "blind_id")), "bin/blind_id（上游演示程序）")
    candidates = commands_json_candidates()
    declared = [c for c in candidates if os.path.isfile(c)]
    check(bool(declared), "R38 申报存在（%s）"
          % " 或 ".join(os.path.relpath(c) for c in candidates))
    if declared:
        decl = declared[0]
        body = open(decl).read()
        check('"name": "d0-blind-id"' in body and '"type": "tool"' in body
              and '"d0-blind-id/1.0"' in body and '"blind_id"' in body,
              "%s 的 name/type/ref/commands 与包一致" % os.path.relpath(decl))

    print("\n[5] 许可与安装纯净性")
    check(os.path.isfile(os.path.join(pkg, "licenses", "COPYING")),
          "licenses/COPYING（上游 3-clause BSD 原文）")
    junk = []
    hidden = []
    for root, dirs, files in os.walk(pkg):
        for name in files:
            if name.endswith((".la", ".o", ".lo", ".obj", ".la.tmp")):
                junk.append(os.path.relpath(os.path.join(root, name), pkg))
        for name in dirs + files:
            if name.startswith("."):
                hidden.append(os.path.relpath(os.path.join(root, name), pkg))
    check(not junk, "无 libtool .la / 构建中间产物", ",".join(junk[:6]))
    check(not hidden, "无隐藏文件（JC5）", ",".join(hidden[:6]))

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
