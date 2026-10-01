#!/usr/bin/env python3
"""kamailio-cpl 产物结构 / 平台合规检查（纯 Python 解析 ELF，无外部工具依赖）。

检查对象是 conan 打包后的 cplc.so 与其随包文件，聚焦“这是一个能在 OHOS/musl
运行时被 kamailio 加载的模块”所必需的结构性事实。

环境变量:
  KAMAILIO_CPL_MODULE         打包后的 cplc.so 路径
  KAMAILIO_CPL_PACKAGE_FOLDER 包根目录
返回码: 0 全部通过；1 存在失败项。
"""
import os
import struct
import sys

FAILURES = []
# kamailio core 契约符号：模块 .so 有意留作 UND，由核心二进制在运行时提供。
# 出现这些 UND 符号即证明产物是“由 kamailio 运行时加载的模块”，而非自包含库。
CORE_CONTRACT_SYMBOLS = {
    "find_export", "register_procs", "run_top_route", "route_lookup",
    "db_bind_mod", "db_check_table_version", "pv_parse_spec2", "set_dst_uri",
    "setbflag", "append_branch", "add_avp", "_km_log_func", "_shm_root",
}
CONTRACT_NAMES = ("cpl_run_script", "cpl_process_register",
                  "cpl_process_register_norpl", "cpl_dtd_file", "db_url",
                  "cpl_xml_column", "cpl_bin_column")


def check(cond, label, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    if not cond:
        FAILURES.append(label)
    return bool(cond)


class Elf:
    """最小 ELF 解析：头部 + 节表 + .dynamic + .dynsym（够用即止）。"""

    def __init__(self, path):
        with open(path, "rb") as fh:
            self.data = fh.read()
        d = self.data
        if d[:4] != b"\x7fELF":
            raise ValueError("不是 ELF 文件")
        self.cls, self.endian = d[4], d[5]
        self.fmt = "<" if self.endian == 1 else ">"
        self.e_type, self.e_machine = struct.unpack_from(self.fmt + "HH", d, 16)
        e_shoff, = struct.unpack_from(self.fmt + "Q", d, 40)
        e_shentsize, e_shnum, e_shstrndx = struct.unpack_from(self.fmt + "HHH", d, 58)
        self.sections = []
        for i in range(e_shnum):
            off = e_shoff + i * e_shentsize
            name, stype, flags, addr, soff, size, link, info, align, entsize = \
                struct.unpack_from(self.fmt + "IIQQQQIIQQ", d, off)
            self.sections.append({"name_off": name, "type": stype, "offset": soff,
                                  "size": size, "link": link, "entsize": entsize})
        raw = self._section_raw(e_shstrndx)
        for sec in self.sections:
            end = raw.find(b"\0", sec["name_off"])
            sec["name"] = raw[sec["name_off"]:end].decode("utf-8", "replace")
        self.by_name = {s["name"]: s for s in self.sections}

    def _section_raw(self, idx):
        sec = self.sections[idx]
        return self.data[sec["offset"]:sec["offset"] + sec["size"]]

    def dynamic_entries(self):
        """返回 [(tag, val)]；NEEDED/RPATH/RUNPATH 的 val 是 .dynstr 内偏移。"""
        sec = self.by_name.get(".dynamic")
        if not sec:
            return []
        out = []
        for off in range(0, sec["size"], 16):
            tag, val = struct.unpack_from(self.fmt + "qQ", self.data, sec["offset"] + off)
            if tag == 0:
                break
            out.append((tag, val))
        return out

    def dynstr(self):
        sec = self.by_name.get(".dynstr")
        return self.data[sec["offset"]:sec["offset"] + sec["size"]] if sec else b""

    def dynsym(self):
        """返回 [{'name': str, 'shndx': int}]。"""
        sec = self.by_name.get(".dynsym")
        if not sec:
            return []
        strtab = self._section_raw(sec["link"]) if sec["link"] else b""
        entsize = sec["entsize"] or 24
        out = []
        for off in range(0, sec["size"], entsize):
            base = sec["offset"] + off
            name_off, info, other, shndx, value, size = \
                struct.unpack_from(self.fmt + "IBBHQQ", self.data, base)
            end = strtab.find(b"\0", name_off)
            name = strtab[name_off:end].decode("utf-8", "replace") if name_off else ""
            out.append({"name": name, "shndx": shndx})
        return out


def main():
    module = os.environ.get("KAMAILIO_CPL_MODULE", "")
    pkg = os.environ.get("KAMAILIO_CPL_PACKAGE_FOLDER", "")
    if not module or not pkg:
        print("需要环境变量 KAMAILIO_CPL_MODULE / KAMAILIO_CPL_PACKAGE_FOLDER")
        return 2

    if not check(os.path.isfile(module), "打包模块 cplc.so 存在", module):
        return 1

    elf = Elf(module)
    check(elf.cls == 2 and elf.endian == 1, "ELF64 小端（aarch64）")
    check(elf.e_type == 3, "ET_DYN（共享模块）", f"e_type={elf.e_type}")
    check(elf.e_machine == 183, "EM_AARCH64", f"e_machine={elf.e_machine}")

    dyn = elf.dynamic_entries()
    needed = [elf.dynstr()[v:elf.dynstr().find(b"\0", v)].decode()
              for t, v in dyn if t == 1]
    check(any(n.startswith("libxml2.so") for n in needed),
          "NEEDED 含 libxml2 共享库（CPL 解析/校验依赖）", f"NEEDED={needed}")
    check(any(n.startswith("libc.so") for n in needed),
          "NEEDED 含 OHOS musl libc.so", f"NEEDED={needed}")
    check(not [t for t, _ in dyn if t in (15, 29)],
          "无 RPATH/RUNPATH（不泄漏构建机/宿主路径）")

    syms = elf.dynsym()
    names = {s["name"] for s in syms}
    undefined = {s["name"] for s in syms if s["shndx"] == 0}
    check(any(s["name"] == "exports" and s["shndx"] != 0 for s in syms),
          "定义 kamailio 模块契约符号 exports")
    check(len(undefined & CORE_CONTRACT_SYMBOLS) >= 10,
          "UND 含 kamailio core 契约符号（证明为运行时加载模块，非自包含库）",
          f"命中 {len(undefined & CORE_CONTRACT_SYMBOLS)} 个")

    dtd = os.path.join(pkg, "lib", "kamailio", "modules", "cpl-06.dtd")
    check(os.path.isfile(dtd) and os.path.getsize(dtd) > 4000,
          "随包发布 cpl-06.dtd（cpl_dtd_file 参数所指向的 CPL DTD）", dtd)
    copying = os.path.join(pkg, "licenses", "COPYING")
    check(os.path.isfile(copying) and os.path.getsize(copying) > 1000,
          "随包发布 GPL 许可证文本 licenses/COPYING")

    raw = elf.data
    missing = [n for n in CONTRACT_NAMES if n.encode() not in raw]
    check(not missing, "模块内嵌导出命令/参数契约名", f"缺失={missing}" if missing else
          f"{', '.join(CONTRACT_NAMES)}")

    if FAILURES:
        print(f"\nFAILED: {len(FAILURES)} 项 — {FAILURES}")
        return 1
    print("\nALL STRUCTURE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
