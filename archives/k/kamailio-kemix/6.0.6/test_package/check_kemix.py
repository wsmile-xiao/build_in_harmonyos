#!/usr/bin/env python3
"""check_kemix.py — kamailio-kemix 6.0.6 打包产物结构校验（R34 实质验证）

纯 Python 标准库实现（不依赖 readelf/objdump，命令行工具缺失时也可运行），
直接解析 ELF64 头 / 节表 / .dynamic / .dynsym，验证：

  1. 产物存在且为普通文件
  2. ELF64 小端
  3. 类型 ET_DYN（共享对象）
  4. 架构 EM_AARCH64（HarmonyOS PC 目标）
  5. 动态依赖仅 libc（kemix 模块无第三方库依赖，与打包口径一致）
  6. 导出模块描述符符号 exports
  7. 导出 KEMI 注册入口符号 mod_register
  8. 未定义符号面含 core 契约 sr_kemi_modules_add / sr_kemi_xval_null
     （说明 kemix.so 是 core 插件，运行时由 kamailio 主程序提供这些符号）
  9. 无 DT_RPATH / DT_RUNPATH（不把宿主前缀写进产物）
 10. 许可证文件 licenses/COPYING 存在、非空且为 GPL 文本
 11. 模块文件大小在合理区间

环境变量：KEMIX_MODULE（kemix.so 绝对路径）、KEMIX_PACKAGE_FOLDER（包根目录）
"""
import os
import struct
import sys

ET_DYN = 3
EM_AARCH64 = 183
DT_NEEDED = 1
DT_RPATH = 15
DT_RUNPATH = 29
SHT_DYNSYM = 11
STB_GLOBAL = 1
STB_WEAK = 2

CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    return ok


class Elf64:
    """最小 ELF64 小端解析器：节表 + .dynamic + .dynsym。"""

    def __init__(self, data):
        self.data = data
        if data[:4] != b"\x7fELF":
            raise ValueError("not an ELF file")
        self.ei_class = data[4]
        self.ei_data = data[5]
        # e_type / e_machine 均为 2 字节；紧随其后才是 4 字节 e_version
        self.e_type, self.e_machine = struct.unpack_from("<HH", data, 16)
        (self.e_shoff,) = struct.unpack_from("<Q", data, 40)
        (self.e_shentsize,) = struct.unpack_from("<H", data, 58)
        (self.e_shnum,) = struct.unpack_from("<H", data, 60)
        (self.e_shstrndx,) = struct.unpack_from("<H", data, 62)
        self.sections = []
        for i in range(self.e_shnum):
            off = self.e_shoff + i * self.e_shentsize
            (name, stype, _flags, _addr, soff, size, link, _info, _align, entsize) = \
                struct.unpack_from("<IIQQQQIIQQ", data, off)
            self.sections.append({"name_off": name, "type": stype, "offset": soff,
                                  "size": size, "link": link, "entsize": entsize})
        shstr = self.sections[self.e_shstrndx]
        for s in self.sections:
            s["name"] = self._cstr(shstr["offset"] + s["name_off"])
        self.by_name = {s["name"]: s for s in self.sections}

    def _cstr(self, off, limit=4096):
        end = self.data.index(b"\x00", off, off + limit)
        return self.data[off:end].decode("utf-8", "replace")

    def dynamic(self):
        """.dynamic 条目列表 [(tag, val)]。"""
        sec = self.by_name.get(".dynamic")
        if not sec:
            return []
        out = []
        for off in range(sec["offset"], sec["offset"] + sec["size"], 16):
            tag, val = struct.unpack_from("<qQ", self.data, off)
            out.append((tag, val))
        return out

    def dynsyms(self):
        """[(name, bind, is_defined)]，bond/type 由 st_info 拆出。"""
        sym, dynstr = self.by_name.get(".dynsym"), self.by_name.get(".dynstr")
        if not sym or not dynstr:
            return []
        out = []
        for off in range(sym["offset"], sym["offset"] + sym["size"], sym["entsize"] or 24):
            st_name, st_info, _other, st_shndx, _val, _size = struct.unpack_from(
                "<IBBHQQ", self.data, off)
            name = self._cstr(dynstr["offset"] + st_name) if st_name else ""
            bind = st_info >> 4
            out.append((name, bind, st_shndx != 0))
        return out

    def needed(self):
        dynstr = self.by_name.get(".dynstr")
        names = []
        for tag, val in self.dynamic():
            if tag == DT_NEEDED and dynstr:
                names.append(self._cstr(dynstr["offset"] + val))
        return names

    def rpaths(self):
        dynstr = self.by_name.get(".dynstr")
        out = []
        for tag, val in self.dynamic():
            if tag in (DT_RPATH, DT_RUNPATH) and dynstr:
                out.append(self._cstr(dynstr["offset"] + val))
        return out


def main():
    module = os.environ.get("KEMIX_MODULE", "")
    pkg = os.environ.get("KEMIX_PACKAGE_FOLDER", "")
    print("kamailio-kemix 6.0.6 打包产物校验")
    print(f"  KEMIX_MODULE={module}")
    print(f"  KEMIX_PACKAGE_FOLDER={pkg}")

    if not check("C1 产物存在且为普通文件", os.path.isfile(module), module):
        print("\nFAILED CHECKS: 1/1")
        return 1

    data = open(module, "rb").read()
    elf = Elf64(data)

    check("C2 ELF64 小端", elf.ei_class == 2 and elf.ei_data == 1,
          f"class={elf.ei_class} data={elf.ei_data}")
    check("C3 类型为共享对象 ET_DYN", elf.e_type == ET_DYN, f"e_type={elf.e_type}")
    check("C4 架构为 AArch64", elf.e_machine == EM_AARCH64,
          f"e_machine={elf.e_machine}")

    needed = sorted(set(elf.needed()))
    third_party = [n for n in needed if not n.startswith("libc.so") and n not in ("libdl.so.2",)]
    check("C5 动态依赖仅 libc（无第三方库）", not third_party,
          f"DT_NEEDED={needed}")

    syms = elf.dynsyms()
    defined = {n for n, b, d in syms if d and b in (STB_GLOBAL, STB_WEAK)}
    undefined = {n for n, b, d in syms if not d and n}
    check("C6 导出模块描述符符号 exports", "exports" in defined, "dlsym 入口")
    check("C7 导出 KEMI 注册入口符号 mod_register", "mod_register" in defined,
          "loadmodule 期注册 sr_kemi_kx_exports")

    core_contract = {"sr_kemi_modules_add", "sr_kemi_xval_null"}
    missing = sorted(core_contract - undefined)
    check("C8 未定义符号面含 core 契约（core 插件特征）", not missing,
          f"undefined∩core={sorted(core_contract & undefined)}"
          + (f" 缺: {missing}" if missing else ""))

    meta = {"module_version", "module_interface_ver", "module_flags"}
    meta_missing = sorted(meta - defined)
    check("C8b 导出模块元数据符号 module_version/interface_ver/flags",
          not meta_missing, f"{sorted(meta & defined)}" + (f" 缺: {meta_missing}" if meta_missing else ""))

    rpaths = elf.rpaths()
    check("C9 无 RPATH/RUNPATH（R49 不写宿主前缀）", not rpaths, f"rpath={rpaths}")

    copying = os.path.join(pkg, "licenses", "COPYING")
    lic_ok = os.path.isfile(copying) and os.path.getsize(copying) > 0
    lic_text = open(copying, "rb").read(4096).upper() if lic_ok else b""
    check("C10 许可证文件 GPL 文本存在", lic_ok and b"GNU GENERAL PUBLIC LICENSE" in lic_text,
          f"{copying} ({os.path.getsize(copying) if lic_ok else 0} bytes)")

    size = os.path.getsize(module)
    check("C11 模块大小在合理区间（10KB–4MB）", 10 * 1024 < size < 4 * 1024 * 1024,
          f"{size} bytes（上游文档 kx.* 全量 69 个 KEMI 函数）")

    passed = sum(1 for _n, ok in CHECKS if ok)
    total = len(CHECKS)
    print()
    if passed == total:
        print(f"ALL CHECKS PASSED ({passed}/{total})")
        return 0
    print(f"FAILED CHECKS: {total - passed}/{total}")
    for n, ok in CHECKS:
        if not ok:
            print(f"  - {n}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
