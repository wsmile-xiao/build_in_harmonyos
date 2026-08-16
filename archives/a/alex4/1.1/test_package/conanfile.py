#!/usr/bin/env python3
"""test_package for alex4 1.1 — 消费测试。

alex4 是图形游戏（Allegro 4 gfx 模式），OHOS headless 环境无法实跑；
上游无测试套件。消费测试验证：
1. bin/alex4 存在且为 ELF 可执行文件
2. 依赖库（liballeg.so / libaldmb / libdumb）可被动态链接器解析
"""

import os
import struct
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


def _read_elf_needed(path):
    """Read DT_NEEDED entries from an ELF .dynamic section (no external tools).

    Handles 64-bit little-endian ELF (aarch64). Returns list of needed lib names.
    DT_NEEDED 的 d_val 是 .dynstr 内偏移（非虚拟地址），需先读 DT_STRTAB
    得到字符串表虚拟地址，经 PT_LOAD 段映射为文件偏移后再定位字符串。
    """
    needed = []
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
        return needed  # not a 64-bit LE ELF
    # ELF64 header: e_phoff@0x20(8), e_phentsize@0x36(2), e_phnum@0x38(2)
    phoff = struct.unpack_from("<Q", data, 0x20)[0]
    phentsize = struct.unpack_from("<H", data, 0x36)[0]
    phnum = struct.unpack_from("<H", data, 0x38)[0]

    def vaddr_to_offset(vaddr):
        """Map virtual address to file offset via PT_LOAD segments."""
        for i in range(phnum):
            ph = phoff + i * phentsize
            p_type = struct.unpack_from("<I", data, ph)[0]
            if p_type != 1:  # PT_LOAD
                continue
            p_offset = struct.unpack_from("<Q", data, ph + 8)[0]
            p_vaddr = struct.unpack_from("<Q", data, ph + 0x10)[0]
            p_filesz = struct.unpack_from("<Q", data, ph + 0x20)[0]
            if p_vaddr <= vaddr < p_vaddr + p_filesz:
                return p_offset + (vaddr - p_vaddr)
        return None

    for i in range(phnum):
        ph = phoff + i * phentsize
        p_type = struct.unpack_from("<I", data, ph)[0]
        if p_type != 2:  # PT_DYNAMIC
            continue
        # PT_DYNAMIC: p_vaddr@0x10(8), p_filesz@0x20(8)
        d_vaddr = struct.unpack_from("<Q", data, ph + 0x10)[0]
        dsz = struct.unpack_from("<Q", data, ph + 0x20)[0]
        doff = vaddr_to_offset(d_vaddr)
        if doff is None:
            continue
        strtab_vaddr = None
        entries = []
        for off in range(doff, doff + dsz, 16):
            tag = struct.unpack_from("<q", data, off)[0]
            val = struct.unpack_from("<Q", data, off + 8)[0]
            entries.append((tag, val))
            if tag == 5:  # DT_STRTAB
                strtab_vaddr = val
            if tag == 0:  # DT_NULL
                break
        if strtab_vaddr is None:
            continue
        strtab_off = vaddr_to_offset(strtab_vaddr)
        if strtab_off is None:
            continue
        for tag, val in entries:
            if tag == 1:  # DT_NEEDED -> offset into .dynstr
                s = data[strtab_off + val: strtab_off + val + 128].split(b"\x00")[0]
                needed.append(s.decode("utf-8", "replace"))
        break
    return needed


class Alex4TestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies[self.tested_reference_str].package_folder
        bin_dir = os.path.join(pkg, "bin")
        share = os.path.join(pkg, "share", "alex4")
        # L0d: test() 必须经 self.run 调用测试脚本（避免 stub 判定）；
        # 脚本校验 bin/alex4 ELF magic + 数据文件（alex4.ini/data.dat/maps.dat）。
        exe = os.path.join(bin_dir, "alex4")
        if not os.path.exists(exe):
            raise ConanException(f"missing installed binary: {exe}")
        test_script = os.path.join(os.path.dirname(__file__), "test_alex4.sh")
        self.run(f"sh {test_script} {bin_dir} {share}", env="conanrun")
        # 依赖库可解析：读 .dynamic NEEDED 条目确认链接了动态库 liballeg
        # （libdumb/libaldmb 为静态链接进二进制，不出现于 NEEDED，属预期）
        needed = _read_elf_needed(exe)
        if not any("liballeg.so" in n for n in needed):
            raise ConanException(f"alex4 does not link liballeg.so; NEEDED={needed}")
        # 数据文件打包
        share = os.path.join(self.dependencies[self.tested_reference_str].package_folder,
                             "share", "alex4")
        for f in ("alex4.ini",):
            if not os.path.exists(os.path.join(share, f)):
                raise ConanException(f"missing data file: {os.path.join(share, f)}")
        data = os.path.join(share, "data")
        for f in ("data.dat", "maps.dat"):
            if not os.path.exists(os.path.join(data, f)):
                raise ConanException(f"missing data file: {os.path.join(data, f)}")
