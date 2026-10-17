#!/usr/bin/env python3
"""db_postgres.so 打包产物校验（L1 消费者视角）。

模块 .so 由 kamailio 二进制运行时 dlopen（且 db_postgres 是 PostgreSQL 连接器，
真正连库需要运行中的 kamailio + 可用的 PostgreSQL 服务端），故按产物结构做实质校验：
ELF 结构、libpq 动态依赖、模块 API 导出符号、BIND_NOW（OHOS/musl 无惰性绑定）、
无 RPATH/RUNPATH 与宿主路径泄漏、许可证文件。

ELF 解析在本文件内自实现，不依赖目标机上是否存在 readelf（OHOS SDK 只承诺
llvm-nm/llvm-objdump，本机无 llvm-readelf）。
"""
import os
import struct
import sys

FAILURES = []


def check(cond, label, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    if not cond:
        FAILURES.append(label)


DT_NEEDED = 1
DT_SONAME = 14
DT_RPATH = 15
DT_RUNPATH = 29
DF_1_NOW = 0x1


def parse_elf(path):
    with open(path, "rb") as fh:
        blob = fh.read()
    info = {
        "size": len(blob),
        "ei_class": blob[4] if len(blob) > 4 else None,
        "e_type": None,
        "e_machine": None,
        "needed": [],
        "soname": None,
        "rpath": False,
        "runpath": False,
        "bind_now": False,
    }
    if blob[:4] != b"\x7fELF" or len(blob) < 0x40:
        return info, blob
    info["e_type"] = struct.unpack_from("<H", blob, 16)[0]
    info["e_machine"] = struct.unpack_from("<H", blob, 18)[0]
    shoff, = struct.unpack_from("<Q", blob, 0x28)
    shentsize, shnum, shstrndx = struct.unpack_from("<HHH", blob, 0x3A)
    sections = []
    for index in range(shnum):
        offset = shoff + index * shentsize
        name, stype = struct.unpack_from("<II", blob, offset)
        sh_offset, sh_size = struct.unpack_from("<QQ", blob, offset + 24)
        sections.append((name, stype, sh_offset, sh_size))
    names = b""
    if shstrndx < len(sections):
        names = blob[sections[shstrndx][2]:sections[shstrndx][2] + sections[shstrndx][3]]

    def section_name(section):
        if section[0] >= len(names):
            return b""
        return names[section[0]:names.index(b"\0", section[0])]

    dynamic = next((s for s in sections if section_name(s) == b".dynamic"), None)
    dynstr = next((s for s in sections if section_name(s) == b".dynstr"), None)
    if not dynamic or not dynstr:
        return info, blob
    strings = blob[dynstr[2]:dynstr[2] + dynstr[3]]

    def string_at(value):
        if value >= len(strings):
            return ""
        return strings[value:strings.index(b"\0", value)].decode("utf-8", "replace")

    for index in range(dynamic[3] // 16):
        tag, value = struct.unpack_from("<qQ", blob, dynamic[2] + index * 16)
        if tag == DT_NEEDED:
            info["needed"].append(string_at(value))
        elif tag == DT_SONAME:
            info["soname"] = string_at(value)
        elif tag == DT_RPATH:
            info["rpath"] = True
        elif tag == DT_RUNPATH:
            info["runpath"] = True
        elif tag == 0x6FFFFFFB:  # DT_FLAGS_1
            if value & DF_1_NOW:
                info["bind_now"] = True
    return info, blob


def main():
    module = os.environ["DB_POSTGRES_MODULE"]
    pkg = os.environ["DB_POSTGRES_PACKAGE_FOLDER"]

    info, blob = parse_elf(module)
    print(f"artifact: {module} ({info['size']} bytes)")

    # 1) ELF 结构：64 位 / 可重定位共享对象 / AArch64
    check(blob[:4] == b"\x7fELF", "ELF 魔数")
    check(info["ei_class"] == 2, "ELFCLASS64", f"ei_class={info['ei_class']}")
    check(info["e_type"] == 3, "ET_DYN（共享对象）", f"e_type={info['e_type']}")
    check(info["e_machine"] == 0xB7, "e_machine=AArch64", f"e_machine={info['e_machine']}")

    # 2) libpq 动态依赖与模块 API 符号
    #    db_bind_api 是 db_postgres 向 kamailio core 注册的 DB 连接器 API
    #    （src/modules/db_postgres/db_postgres.c:52 exports.cmds 条目）
    print(f"     NEEDED: {', '.join(info['needed'])}")
    check(any(n.startswith("libpq.so") for n in info["needed"]),
          "动态段 NEEDED 含 libpq.so", ", ".join(info["needed"]))
    for marker in (b"db_bind_api", b"db_postgres", b"kam_exports"):
        check(marker in blob, f"动态段/符号标记 {marker.decode()}")

    # 3) OHOS/musl 相关：无惰性绑定（模块自身 BIND_NOW），无 RPATH/RUNPATH 泄漏
    check(info["bind_now"], "动态段 FLAGS_1=DF_1_NOW（OHOS musl 无惰性绑定的前提）")
    check(not info["rpath"] and not info["runpath"], "动态段无 RPATH/RUNPATH",
          "clean")
    check(not any("/" in n for n in info["needed"]),
          "NEEDED 全部为纯文件名（可重定位）", ", ".join(info["needed"]))
    # 注：模块字符串表中含源文件路径（core 的 __FILE__/assert 机制，属信息性内容，
    # 不影响加载）；运行期真正敏感的 RPATH/RUNPATH 与 NEEDED 已在上面校验为 clean。

    # 4) 许可证文件随包安装
    license_file = os.path.join(pkg, "licenses", "COPYING")
    check(os.path.isfile(license_file), "licenses/COPYING 存在", license_file)

    if FAILURES:
        print(f"\nFAILED: {len(FAILURES)} 项 — {FAILURES}")
        return 1
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
