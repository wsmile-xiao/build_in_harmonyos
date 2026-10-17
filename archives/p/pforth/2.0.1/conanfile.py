#!/usr/bin/env python3
"""Conan recipe for pforth 2.0.1 — 便携式 Forth 解释器（ANSI C + POSIX）。

pForth 是一个用 ANSI C 编写的便携式 Forth 实现，无第三方依赖，仅链接系统
libm。构建是两步引导（bootstrap）：
  1. 编译 C 内核得到 pforth 可执行文件
  2. 运行 pforth 编译 fth/system.fth 生成 pforth.dic 与 pfdicdat.h
  3. 编译 pforth_standalone（内置 dictionary 的独立可执行文件）

在鸿蒙 PC 真机上为原生编译，make 会运行刚编译的 pforth 完成 dictionary
生成，因此必须在 pforth 生成 dictionary 之前对其做 ELF 签名（E077/E135），
否则 OHOS 内核拒绝执行未签名的外来二进制。

R32: POSIX 平台门禁使用 settings.os not in ("Linux", "OHOS")。
R33: 编译器从 Conan conf 获取，禁止裸用 shell 环境变量。
R34: test_package 真实执行 pforth_standalone 的 Forth 求值。
R38: commands.json 在软件级目录声明（tool 类型）。
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class PforthConan(ConanFile):
    name = "pforth"
    version = "2.0.1"
    description = "Portable ANS-like Forth interpreter written in ANSI C."
    license = "0BSD"
    homepage = "https://github.com/philburk/pforth"
    url = "https://github.com/philburk/pforth"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _sign_elf(self, path):
        """OHOS 上对新编译的 ELF 做 selfSign 签名并赋予执行位（E077/E135）。"""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        parent = os.path.dirname(path)
        self.run(
            f'{sign_tool} sign -inFile "{path}" -outFile "{path}" -selfSign 1',
            cwd=parent,
        )
        self.run(f'chmod a+x "{path}"', cwd=parent)

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            self.fail("pforth requires a POSIX host (Linux or OHOS)")
        apply_conandata_patches(self)

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        unix_dir = os.path.join(self.source_folder, "platforms", "unix")

        # Step 1: 编译 C 内核得到 pforth（可执行文件）。
        # R9: make -j1
        self.run(f'make pfdicapp CC="{cc}" -j1', cwd=unix_dir)

        # Step 2: OHOS 上签名 pforth——后续 make 会运行它生成 dictionary。
        if self.settings.os == "OHOS":
            self._sign_elf(os.path.join(unix_dir, "pforth"))

        # Step 3: 运行 pforth 生成 pforth.dic 与 pfdicdat.h，再编译
        # pforth_standalone（内置 dictionary，无需外部 .dic 文件）。
        self.run(f'make pforthapp CC="{cc}" -j1', cwd=unix_dir)

        # Step 4: OHOS 上签名 pforth_standalone（最终交付物）。
        if self.settings.os == "OHOS":
            self._sign_elf(os.path.join(unix_dir, "pforth_standalone"))

        # Step 5: 上游官方测试套件（6 个 Forth 测试脚本，失败退出码 40）。
        self.run("make test", cwd=unix_dir)

    def package(self):
        unix_dir = os.path.join(self.source_folder, "platforms", "unix")
        bin_dir = os.path.join(self.package_folder, "bin")
        # pforth + pforth_standalone 均放入 bin；pforth.dic 与 pforth 同目录，
        # 使 pforth 运行时按默认名 "pforth.dic" 找到 dictionary。
        copy(self, "pforth", unix_dir, bin_dir)
        copy(self, "pforth_standalone", unix_dir, bin_dir)
        copy(self, "pforth.dic", unix_dir, bin_dir)
        copy(self, "license.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
