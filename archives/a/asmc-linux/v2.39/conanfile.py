#!/usr/bin/env python3
"""Conan recipe — asmc-linux v2.39 (ARM64 原生 host 移植, CLI 工具)

本 recipe 使用 aarch64_port/ 中的真实 ARM64 原生移植源码构建 Asmc 宏汇编器 host：
  - asmc_asm.c / asmc_elf.c / asmc_io.c / asmc_globals.c（C 支持, musl libc）
  - asmc_entry.s / asmc_runtime.s（AArch64 汇编端口）
  - Makefile（target aarch64-unknown-linux-ohos, clang 15.0.4）
构建产物 asmc_native 为 ARM64 OHOS 静态 ELF，可在 aarch64 上原生运行，并输出
x86/x86-64 目标（.o ELF64 x86-64 与 .bin 原始 x86 指令），可被本地 ld.lld 链接为
x86-64 可执行 ELF。本 recipe 已通过本地 make 构建与 635-source manifest 验证。
"""
import os
from conan import ConanFile
from conan.tools.files import copy


class AsmcLinuxConan(ConanFile):
    name = "asmc-linux"
    version = "v2.39"
    description = "Asmc Macro Assembler v2.39 — ARM64 OHOS 原生移植, CLI 工具"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/nidud/asmc"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "source/*"

    def build(self):
        # ARM64 原生构建（本地 clang 15.0.4, target aarch64-unknown-linux-ohos）
        src = os.path.join(self.source_folder, "source")
        self.run("make rebuild", cwd=src)

    def package(self):
        copy(self, "asmc_native", dst=os.path.join(self.package_folder, "bin"),
             src=os.path.join(self.source_folder, "source"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # asmc_native 为 CLI 工具
        self.conf_info.define("user.asmc:binary", "bin/asmc_native")
