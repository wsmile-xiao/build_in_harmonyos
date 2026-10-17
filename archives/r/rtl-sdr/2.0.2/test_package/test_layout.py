#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rtl-sdr 2.0.2 适配自检（M，非上游用例）。

上游**没有测试套件**（如实声明），真跑的证据在 test_rtlsdr.c（消费者用例）与
recipe build() 的 8 个 CLI 启动冒烟。这里检查的是 **conan 包的交付形态**：
librtlsdr.so（含 DT_SONAME）、公共头、8 个 CLI、pkg-config 契约可重定位、
许可、以及是否误带构建机路径 / 不可重定位的上游 CMake export / 隐藏文件。
"""
from __future__ import print_function

import os
import struct
import sys

FAILURES = []
COUNT = [0]

CLI_TOOLS = ("rtl_sdr", "rtl_fm", "rtl_tcp", "rtl_test",
             "rtl_eeprom", "rtl_adsb", "rtl_power", "rtl_biast")


def check(ok, label, detail=""):
    COUNT[0] += 1
    if not ok:
        FAILURES.append(label)
    print("  [%s] %s%s" % ("ok" if ok else "FAIL", label,
                           ("  " + detail) if detail else ""))
    return ok


def elf_type_and_soname(path):
    """纯 Python 解析 ELF：返回 (e_type, DT_SONAME)。不依赖 readelf。"""
    with open(path, "rb") as handle:
        data = handle.read()
    if data[:4] != b"\x7fELF":
        return None, None
    if data[4] != 2:                      # 只支持 ELF64（aarch64/x86_64 都是）
        raise ValueError("not ELF64")
    order = "<" if data[5] == 1 else ">"
    e_type, = struct.unpack_from(order + "H", data, 16)
    e_shoff, = struct.unpack_from(order + "Q", data, 40)
    e_shentsize, = struct.unpack_from(order + "H", data, 58)
    e_shnum, = struct.unpack_from(order + "H", data, 60)
    soname = None
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        sh_type, = struct.unpack_from(order + "I", data, off + 4)
        if sh_type != 6:                  # SHT_DYNAMIC
            continue
        sh_offset, = struct.unpack_from(order + "Q", data, off + 24)
        sh_size, = struct.unpack_from(order + "Q", data, off + 32)
        sh_link, = struct.unpack_from(order + "I", data, off + 40)
        str_off, = struct.unpack_from(order + "Q", data,
                                      e_shoff + sh_link * e_shentsize + 24)
        for j in range(sh_size // 16):    # Elf64_Dyn
            d_tag, = struct.unpack_from(order + "q", data, sh_offset + j * 16)
            d_val, = struct.unpack_from(order + "Q", data, sh_offset + j * 16 + 8)
            if d_tag == 0:                # DT_NULL
                break
            if d_tag == 14:               # DT_SONAME
                end = data.index(b"\x00", str_off + d_val)
                soname = data[str_off + d_val:end].decode("utf-8", "replace")
    return e_type, soname


def main(argv):
    pkg = argv[1]
    libdir = os.path.join(pkg, "lib")
    incdir = os.path.join(pkg, "include")
    bindir = os.path.join(pkg, "bin")
    libs = sorted(os.listdir(libdir)) if os.path.isdir(libdir) else []
    print("适配自检（M）: %s" % pkg)

    print("\n[1] librtlsdr 共享库（含 DT_SONAME，HMDFS 不建符号链接）")
    so = os.path.join(libdir, "librtlsdr.so")
    check(os.path.isfile(so), "lib/librtlsdr.so 交付为实体文件")
    etype, soname = elf_type_and_soname(so) if os.path.isfile(so) else (None, None)
    check(etype == 3, "librtlsdr.so 是 ELF ET_DYN 共享对象", "e_type=%s" % etype)
    check(soname == "librtlsdr.so",
          "DT_SONAME 存在且为相对名（L5a：下游链接器可按 SONAME 寻址）",
          "SONAME=%s" % soname)
    if os.path.isfile(so):
        check(not [n for n in libs if n.startswith("librtlsdr.so.") or n == "librtlsdr.a"],
              "lib/ 只留一份库（shared 选项：无 .a、无版本化 .so 链）", ",".join(libs))
    else:
        check(os.path.isfile(os.path.join(libdir, "librtlsdr.a")),
              "静态构建时交付 lib/librtlsdr.a")

    print("\n[2] 消费者公共头文件")
    for rel in ("rtl-sdr.h", "rtl-sdr_export.h"):
        check(os.path.isfile(os.path.join(incdir, rel)), "include/%s" % rel)

    print("\n[3] 命令行工具（8 个，均为 ELF 可执行）")
    for tool in CLI_TOOLS:
        path = os.path.join(bindir, tool)
        ok = os.path.isfile(path) and os.access(path, os.X_OK)
        if ok:
            et, _ = elf_type_and_soname(path)
            ok = et in (2, 3)             # ET_EXEC / PIE
        check(ok, "bin/%s 存在且可执行" % tool)

    print("\n[4] pkg-config 契约可重定位（CMake install 前缀 + 构建机 libusb 路径）")
    pc = os.path.join(libdir, "pkgconfig", "librtlsdr.pc")
    check(os.path.isfile(pc), "lib/pkgconfig/librtlsdr.pc 交付")
    if os.path.isfile(pc):
        with open(pc) as handle:
            body = handle.read()
        check("-lrtlsdr" in body, "pkg-config Libs 指向 librtlsdr")
        check("prefix=${pcfiledir}/../.." in body, "prefix 已改为相对 pcfiledir")
        bad_paths = [ln for ln in body.splitlines()
                     if ("-I" in ln or "-L" in ln) and "/" in ln.split("-I")[-1].split("-L")[-1]
                     and "${" not in ln]
        check(not bad_paths, "Cflags/Libs 无构建机绝对路径残留",
              ";".join(bad_paths[:2]))

    print("\n[5] 许可与安装纯净性")
    copying = os.path.join(pkg, "licenses", "COPYING")
    check(os.path.isfile(copying), "licenses/COPYING（GPL-2.0-or-later）交付")
    if os.path.isfile(copying):
        with open(copying, errors="replace") as handle:
            head = handle.read(4096)
        check("GENERAL PUBLIC LICENSE" in head and "Version 2" in head,
              "COPYING 正文为 GPL-2.0")
    check(not os.path.isdir(os.path.join(libdir, "cmake", "rtlsdr")),
          "未带上游不可重定位的 lib/cmake/rtlsdr export（内含构建机 libusb 绝对路径）")
    junk, hidden = [], []
    for root, dirs, files in os.walk(pkg):
        for name in files:
            rel = os.path.relpath(os.path.join(root, name), pkg)
            if name.endswith((".o", ".lo", ".la", ".deps", ".tmp", ".log")):
                junk.append(rel)
        for name in list(dirs) + list(files):
            if name.startswith("."):
                hidden.append(os.path.relpath(os.path.join(root, name), pkg))
    check(not junk, "无构建中间产物（.o/.lo/.la/.log）", ",".join(junk[:6]))
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
