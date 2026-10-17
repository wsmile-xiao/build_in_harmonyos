#!/usr/bin/env python3
"""rl-accel 0.9.1 鸿蒙专项测试（新增）。

用法: python3 test_rl_accel_ohos.py <path-to-_rl_accel.abi3.so>

验证对象是**已打包产物**在 OHOS 平台上的可用性与一致性，覆盖三项只在
HarmonyOS/aarch64-musl 上才有意义的事实：

  1. ELF 身份：AArch64 (EM_AARCH64=183) + 64 位小端 —— 产物确实面向
     HarmonyOS PC 目标架构，而非构建机 x86。
  2. .codesign 段存在：OHOS 沙箱 dlopen 强校验该段（缺失时报误导性的
     ``Permission denied``，E212），产物必须自带。
  3. NEEDED 含 libpython3.12.so.1.0：这是 OHOS/musl 的**适配点**——musl 不把
     Python 符号导出到全局符号表，扩展必须显式链接 libpython；glibc 下同一
     abi3 模块无需该 NEEDED。缺失即说明适配未生效。
  4. 运行期一致性：在 musl 下复算两条与 libc/字节序强相关的路径
     （fp_str 走 snprintf 的数值格式化；calcChecksum 走 32 位大端字累加），
     确认无平台偏差。

仅使用标准库（struct/importlib），不依赖 reportlab 本体。
"""
import importlib.util
import os
import struct
import sys

SO_PATH = sys.argv[1]

EM_AARCH64 = 183
CHECKS = []


def check_true(name, cond, detail=""):
    CHECKS.append(bool(cond))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}{(' ' + detail) if detail else ''}")


def read_elf(path):
    with open(path, "rb") as fh:
        data = fh.read()
    is_elf = data[:4] == b"\x7fELF"
    bits = data[4] if len(data) > 4 else None      # 1=32bit, 2=64bit
    endian = data[5] if len(data) > 5 else None    # 1=LE, 2=BE
    machine = struct.unpack_from("<H", data, 0x12)[0] if is_elf else None
    sections = []
    dynamic = []
    if is_elf and bits == 2 and endian == 1:
        e_shoff, = struct.unpack_from("<Q", data, 0x28)
        e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", data, 0x3a)
        if e_shoff and e_shnum:
            strtab_off, = struct.unpack_from(
                "<Q", data, e_shoff + e_shstrndx * e_shentsize + 0x18)
            strtab_size, = struct.unpack_from(
                "<Q", data, e_shoff + e_shstrndx * e_shentsize + 0x20)
            strtab = data[strtab_off:strtab_off + strtab_size]
            for i in range(e_shnum):
                off = e_shoff + i * e_shentsize
                name_off, = struct.unpack_from("<I", data, off)
                end = strtab.index(b"\0", name_off)
                sections.append(strtab[name_off:end].decode("latin1"))
                sh_type, = struct.unpack_from("<I", data, off + 0x04)
                sh_offset, = struct.unpack_from("<Q", data, off + 0x18)
                sh_size, = struct.unpack_from("<Q", data, off + 0x20)
                if sh_type == 6:  # SHT_DYNAMIC
                    dynamic.append(data[sh_offset:sh_offset + sh_size])
    return {"is_elf": is_elf, "bits": bits, "endian": endian,
            "machine": machine, "sections": sections, "dynamic": dynamic}


def dynamic_needed(data, endian):
    """解析 .dynamic 段里的 DT_NEEDED(1) 目标库名。"""
    dt_strtab = dt_strsz = 0
    entries = []
    for blob in data["dynamic"]:
        for k in range(0, len(blob) - 15, 16):
            tag, val = struct.unpack_from(endian + "qQ", blob, k)
            entries.append((tag, val))
            if tag == 5:    # DT_STRTAB
                dt_strtab = val
            elif tag == 10:  # DT_STRSZ
                dt_strsz = val
            elif tag == 0:   # DT_NULL
                break
    if not dt_strtab or not dt_strsz:
        return []
    with open(SO_PATH, "rb") as fh:
        fh.seek(dt_strtab)
        strtab = fh.read(dt_strsz)
    return [strtab[v:strtab.index(b"\0", v)].decode("latin1")
            for tag, v in entries if tag == 1]


# ── 1/2/3：ELF 身份、.codesign、NEEDED ─────────────────────────────
elf = read_elf(SO_PATH)
check_true("is ELF", elf["is_elf"])
check_true("64-bit", elf["bits"] == 2, f"(EI_CLASS={elf['bits']})")
check_true("little-endian", elf["endian"] == 1, f"(EI_DATA={elf['endian']})")
check_true("EM_AARCH64", elf["machine"] == EM_AARCH64,
           f"(e_machine={elf['machine']})")
check_true("has .codesign section", ".codesign" in elf["sections"])
check_true("filename is _rl_accel.abi3.so",
           os.path.basename(SO_PATH) == "_rl_accel.abi3.so")

needed = dynamic_needed(elf, "<")
check_true("NEEDED libpython3.12.so.1.0 (musl 适配点)",
           any("libpython3.12" in n for n in needed), f"(NEEDED={needed})")
check_true("NEEDED libc.so", any(n == "libc.so" for n in needed))

# ── 4：运行期一致性（musl printf / 字节序） ────────────────────────
spec = importlib.util.spec_from_file_location("_rl_accel", SO_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
check_true("extension loaded from package path", mod.__name__ == "_rl_accel")
check_true("module exposes version", mod.version == "0.9.1")

# fp_str 走 libc snprintf；musl 下固定值应仍与上游算法一致
check_true("fp_str musl formatting",
           mod.fp_str(1.5, 2.0, 0.1, 1e-8) == "1.5 2 .1 0")
# calcChecksum 以大端 32 位字累加，与 CPU 字节序无关（验证 aarch64 小端下正确）
check_true("calcChecksum big-endian words",
           mod.calcChecksum(b"Hello cruel world!") == 142323306)
# Ascii85 位运算在小端 CPU 上无偏差
check_true("asciiBase85 on aarch64",
           mod.asciiBase85Encode(b"\x00\x00\x00\x00") == "z~>"
           and mod.asciiBase85Decode("87cURD]iP1F_,A3GAhM<A0C~>")
           == b"Hello cruel world!")

passed = sum(1 for c in CHECKS if c)
print(f"\nrl-accel 0.9.1 OHOS-specific: {passed}/{len(CHECKS)} passed")
sys.exit(0 if passed == len(CHECKS) else 1)
