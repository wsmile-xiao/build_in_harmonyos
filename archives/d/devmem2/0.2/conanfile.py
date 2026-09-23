#!/usr/bin/env python3
"""Conan recipe for devmem2 0.2 — read/write from/to any location in memory.

devmem2 是 www.lartmaker.nl/lartware/ 2004 年原创的极简内存读写工具
（单 .c 文件 ~200 行），用于嵌入式开发中读/写 MMIO 寄存器、GPIO、
DMA 地址等物理内存。literming fork (2025) 增加了多个改进功能。

OHOS 适配 (aarch64 musl):
- 直链 clang 编译单 .c，conan 2.x self.run() 默认 cwd = source_folder
- musl <sys/mman.h> 完整 mmap/munmap 支持（与 glibc 兼容）
- 默认 /dev/mem 在 OHOS 上不一定存在（OH 内核不一定导出
  /dev/mem 给普通进程），但 conan 适配只需 build 成功即可
- 编译产出单可执行文件 bin/devmem2
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get


class Devmem2Conan(ConanFile):
    name = "devmem2"
    version = "0.2"
    description = "Read/write from/to any location in memory (single .c file, ~200 lines)"
    license = "GPL-2.0-only"
    homepage = "https://github.com/literming/devmem2"
    topics = ("memory", "mmio", "embedded", "debug")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def source(self):
        # filename 必须显式给出：codeload 直链末段是 refs/tags/0.2，无扩展名，
        # conan 会按 zip 处理并抛 BadZipFile。
        get(self, **self.conan_data["sources"], filename="devmem2-0.2.tar.gz",
            strip_root=True)

    def build(self):
        # 直链 clang 编译（不嵌 cd，conan 2.x self.run() 默认 cwd=source_folder）
        cc = os.environ.get("CC", "clang")
        cflags = os.environ.get("CFLAGS", "") + " -O2 -Wall"
        self.run(f"{cc} {cflags} -o devmem2 devmem2.c")

    def package(self):
        copy(self, "devmem2", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "devmem2"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share", "licenses"]
