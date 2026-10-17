#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""db5.3 5.3.28 适配自检（M，非上游用例）。

检查交付形态：C 库（ELF ET_DYN）+ 无版本号链接 + 公开头 + 14 个 db_* 工具
（ELF 可执行、与 commands.json 申报一致）+ Sleepycat 许可 + 构建期 Tcl 绑定/
libtool .la/上游 docs 都已剔除 + 无构建残留与隐藏文件。
用法：python3 test_layout.py <package_folder>
"""
from __future__ import print_function

import os
import stat
import sys

FAILURES = []
COUNT = [0]

# 与版本目录内 commands.json 的 versions.<ver>.commands 一致（R38 申报清单）
TOOLS = ("db_archive", "db_checkpoint", "db_deadlock", "db_dump", "db_hotbackup",
         "db_load", "db_log_verify", "db_printlog", "db_recover", "db_replicate",
         "db_stat", "db_tuner", "db_upgrade", "db_verify")


def check(ok, label, detail=""):
    COUNT[0] += 1
    if not ok:
        FAILURES.append(label)
    print("  [%s] %s%s" % ("ok" if ok else "FAIL", label,
                           ("  " + detail) if detail else ""))
    return ok


def elf_header(path):
    try:
        with open(path, "rb") as handle:
            head = handle.read(20)
    except (IOError, OSError):
        return None
    if head[:4] != b"\x7fELF" or len(head) < 18:
        return None
    return head


def main(argv):
    if len(argv) < 2:
        print("usage: test_layout.py <package_folder>")
        return 2
    pkg = argv[1]
    libdir = os.path.join(pkg, "lib")
    incdir = os.path.join(pkg, "include")
    bindir = os.path.join(pkg, "bin")
    libs = sorted(os.listdir(libdir)) if os.path.isdir(libdir) else []
    bins = sorted(os.listdir(bindir)) if os.path.isdir(bindir) else []
    print("适配自检（M）: %s" % pkg)

    print("\n[1] C 库交付：libdb-5.3.so 是 ELF 共享对象")
    so = os.path.join(libdir, "libdb-5.3.so")
    head = elf_header(so) if os.path.isfile(so) else None
    check(head is not None and head[16] == 3,
          "lib/libdb-5.3.so 存在且是 ELF ET_DYN",
          "%d 字节" % os.path.getsize(so) if os.path.isfile(so) else "缺失")
    if head is not None:
        with open(so, "rb") as handle:
            blob = handle.read()
        for symbol in ("db_create", "db_env_create", "db_version"):
            check(symbol.encode() in blob, "libdb-5.3.so 导出 %s" % symbol)

    print("\n[2] 无版本号链接（-ldb 也能链上）")
    unversioned = [n for n in libs if n in ("libdb.so", "libdb-5.so")]
    check(bool(unversioned), "lib/ 存在无版本号链接 libdb[-5].so", ",".join(unversioned))
    for name in unversioned:
        path = os.path.join(libdir, name)
        check(os.path.islink(path) and os.path.realpath(path).endswith("libdb-5.3.so"),
              "lib/%s -> libdb-5.3.so" % name,
              os.path.realpath(path) if os.path.islink(path) else "非符号链接")

    print("\n[3] 公开头（消费者 #include <db.h>）")
    hdr = os.path.join(incdir, "db.h")
    check(os.path.isfile(hdr), "include/db.h")
    if os.path.isfile(hdr):
        body = open(hdr, "r", errors="replace").read()
        check("db_create" in body and "DB_VERSION_MAJOR" in body,
              "include/db.h 含公开 API 与版本宏",
              "%d 字节" % os.path.getsize(hdr))
    check(os.path.isfile(os.path.join(incdir, "db_cxx.h")),
          "include/db_cxx.h（上游 install 一并产物）")

    print("\n[4] 14 个 db_* CLI 工具（R38 申报清单一致）")
    missing = [n for n in TOOLS if n not in bins]
    check(not missing, "bin/ 下 14 个 db_* 工具齐全", ",".join(missing))
    not_exec = [n for n in TOOLS if n in bins
                and not (os.stat(os.path.join(bindir, n)).st_mode & stat.S_IXUSR)]
    check(not not_exec, "全部工具带可执行位", ",".join(not_exec))
    bad_elf = [n for n in TOOLS if n in bins and elf_header(os.path.join(bindir, n)) is None]
    check(not bad_elf, "全部工具是 ELF 可执行", ",".join(bad_elf))

    print("\n[5] 许可")
    lic = os.path.join(pkg, "licenses", "LICENSE")
    check(os.path.isfile(lic), "licenses/LICENSE（上游 Sleepycat 许可）")
    if os.path.isfile(lic):
        text = open(lic, "r", errors="replace").read()
        check("Sleepycat" in text or "Berkeley DB" in text,
              "许可正文可辨认（Sleepycat / Berkeley DB）", "%d 字节" % len(text))

    print("\n[6] 安装纯净性")
    junk = [n for n in libs if n.endswith((".la", ".lo", ".o", ".tmp"))]
    check(not junk, "lib/ 无 libtool .la / 构建中间产物", ",".join(junk[:6]))
    tcl = [n for n in libs if n.startswith("libdb_tcl")]
    check(not tcl, "Tcl 绑定未进包（只是构建期测试设施）", ",".join(tcl))
    static = [n for n in libs if n.endswith(".a")]
    check(not static, "shared 构建下无残留静态库", ",".join(static))
    check(not os.path.isdir(os.path.join(pkg, "docs")),
          "上游 docs/（5200+ 生成 HTML）已剔除")
    hidden = []
    for root, dirs, files in os.walk(pkg):
        for name in dirs + files:
            if name.startswith(".") or name == "__pycache__":
                hidden.append(os.path.relpath(os.path.join(root, name), pkg))
    check(not hidden, "无隐藏文件 / __pycache__ 残留", ",".join(hidden[:6]))

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
