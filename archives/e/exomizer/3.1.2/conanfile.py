#!/usr/bin/env python3
"""Conan recipe for exomizer 3.1.2 — file compressor optimized for
decompression in 8-bit environments (6502/Z80/6809). ANSI-C console tool.

Build system: flat makefile (src/Makefile), builds exomizer + exobasic.
Build-time tooling: bison/flex rules exist in the Makefile, but the source
tarball ships pre-generated asm.tab.c/asm.tab.h/lex.yy.c with newer
timestamps, so no bison/flex are required (same property Homebrew relies
on). Pure C, no external library dependencies.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class ExomizerConan(ConanFile):
    name = "exomizer"
    version = "3.1.2"
    description = "File compressor optimized for decompression in 8-bit environments (6502/Z80/6809)"
    license = "Zlib AND GPL-3.0-or-later"  # bison 生成代码另含 Bison-exception-2.2
    homepage = "https://bitbucket.org/magli143/exomizer/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        pass  # 纯 C 工具，无外部依赖

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Makefile-based build; keep for Conan 2.x structure gate.
        pass

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("cc") or compilers.get("c") or "clang"
        src = os.path.join(self.source_folder, "src")
        with _chdir(src):
            # 默认 WFLAGS/CFLAGS 由 Makefile 自带 (-std=c89 -D_XOPEN_SOURCE=600
            # -O3)；仅注入 CC。lex.yy.c/asm.tab.c 预生成且时间戳更新，
            # make 不会触发 flex/bison 重生成（与 Homebrew 构建前提一致）。
            self.run(f"make -j{os.cpu_count() or 2} CC=\"{cc}\"")

    def package(self):
        copy(self, "exomizer", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "exobasic", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # 纯 CLI 工具，无可链接库
        self.cpp_info.libs = []


# 局部帮助函数（conan recipe 内不可 import 项目外模块）
import contextlib


@contextlib.contextmanager
def _chdir(path):
    old = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)
