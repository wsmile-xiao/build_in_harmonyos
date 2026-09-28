#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for paxctl 0.9 — PaX flag control for ELF binaries.

paxctl 是 PaX Team 的工具（GPL-2.0），用于**按二进制逐个**查询与修改
PaX 的 ELF 程序头标志（PT_PAX_FLAGS）。PaX 是内核级入侵防御机制
（PAGEEXEC / SEGMEXEC / MPROTECT / RANDMMAP / RANDEXEC / EMUTRAMP），
少数应用因设计或实现缺陷与之不兼容，需要按可执行文件豁免某些强制策略；
反向地，在"软模式"下也可以用 paxctl 为选定程序**打开**保护。

核心操作：
- `-v`  查看某文件的 PaX 标志（12 字符标志串 + 逐条中文/英文说明）
- `-c`  把 PT_GNU_STACK 程序头**转换**成 PT_PAX_FLAGS（就地改写程序头）
- `-C`  新建 PT_PAX_FLAGS 程序头
- `-z`  恢复默认标志（回到 `-------x----`）
- `-p/-P -e/-E -m/-M -r/-R -x/-X -s/-S` 成对地禁用/启用各项保护

OHOS 适配 (aarch64 musl):
- 单编译单元：`paxctl.c` 直接 `#include "paxctl-elf.c"`（上游 Makefile 也只
  编译 paxctl.c），故只需 `clang -o paxctl paxctl.c`
- 无外部库依赖（仅 libc：stdio/stdlib/unistd/getopt/elf/fcntl/errno/
  sys/mman）；musl 全支持，无 patch
- 上游 Makefile 用 `CC:=gcc` 且 `-Wconversion` 等一长串告警开关，在交叉编译
  环境既不可用也会被告警阻断，因此 build() 直驱 clang
- 产出单可执行文件 bin/paxctl
- ★ PaX 本身是 Linux/grsecurity 的内核特性，OHOS 内核对 PT_PAX_FLAGS 的
  **运行时**解释取决于内核配置；但 paxctl 的**文件读写行为**是纯用户态
  ELF 操作，与内核无关，因此本包的验证聚焦于 ELF 层面的确定行为
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get


class PaxctlConan(ConanFile):
    name = "paxctl"
    version = "0.9"
    description = ("PaX flag control for ELF binaries: view/convert/modify "
                   "PT_PAX_FLAGS program headers per executable")
    license = "GPL-2.0-or-later"
    homepage = "https://pax.grsecurity.net/"
    topics = ("pax", "elf", "hardening", "security", "grsecurity", "cli")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # paxctl.c 内部 #include "paxctl-elf.c"（上游 Makefile 同样只编译
        # paxctl.c），因此单个翻译单元即可产出完整程序。
        # 不用上游 Makefile：其 CC:=gcc、CFLAGS 含 -Wconversion 等一长串
        # 告警开关，交叉编译环境不可用且会被告警阻断。
        cc = os.environ.get("CC", "clang")
        cflags = os.environ.get("CFLAGS", "")
        self.run(f"{cc} {cflags} -O2 -w -std=gnu99 -o paxctl paxctl.c")

    def package(self):
        copy(self, "paxctl", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "paxctl.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "paxctl"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
