#!/usr/bin/env python3
"""Conan recipe — acorn-fdisk 3.0.6 (Makefile)

acorn-fdisk is a partition editor for Acorn/RISC OS machines. It is built
from a plain upstream Makefile (no configure script).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class AcornFdiskConan(ConanFile):
    name = "acorn-fdisk"
    version = "3.0.6"
    description = "Partition editor for Acorn/RISC OS machines"
    license = "GPL-1.0-or-later"
    homepage = "https://www.arm.linux.org.uk/machines/riscpc/stage-2/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} is not supported"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c")
        if compiler:
            return compiler
        return "cc"

    def build(self):
        apply_conandata_patches(self)
        compiler = self._compiler()
        # 顶层 Makefile 默认 STRIP=strip / LDFLAGS=-N 在 OHOS 上不适用：
        # 显式覆盖为 no-op，编译器显式传入 Conan 工具链 clang。
        # -j1：该文件系统不允许 make jobserver mkfifo，禁用并行 jobserver。
        # Makefile 位于 source 目录（basic_layout src_folder="src"），用 -C 进入。
        self.run(
            f'make -C "{self.source_folder}" -j1 CC="{compiler}" STRIP=: LDFLAGS=""',
            env=["conanbuild"],
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        doc_dir = os.path.join(self.package_folder, "share", "doc", "acorn-fdisk")
        copy(self, "fdisk", self.source_folder, bin_dir, keep_path=False)
        # 以 Debian 命名惯例安装为 acorn-fdisk，避免与系统 fdisk 混淆
        os.rename(os.path.join(bin_dir, "fdisk"), os.path.join(bin_dir, "acorn-fdisk"))
        copy(self, "README", self.source_folder, doc_dir, keep_path=False)
        copy(self, "ChangeLog", self.source_folder, doc_dir, keep_path=False)
        # 上游 tarball 不含 COPYING，依据 Debian copyright 声明 GPL-1+
        license_dir = os.path.join(self.package_folder, "licenses")
        os.makedirs(license_dir, exist_ok=True)
        with open(os.path.join(license_dir, "COPYING"), "w", encoding="utf-8") as stream:
            stream.write(
                "acorn-fdisk (arm-fdisk) is Copyright (C) 1997-1998 Russell King.\n"
                "\n"
                "This program is free software; you can redistribute it and/or\n"
                "modify it under the terms of the GNU General Public License as\n"
                "published by the Free Software Foundation; either version 1, or\n"
                "(at your option) any later version.\n"
                "\n"
                "This program is distributed in the hope that it will be useful,\n"
                "but WITHOUT ANY WARRANTY; without even the implied warranty of\n"
                "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n"
                "GNU General Public License for more details.\n"
                "\n"
                "The upstream tarball does not ship a license file; this notice\n"
                "follows the Debian packaging copyright metadata (GPL-1+).\n"
            )
        if os.name != "nt":
            os.chmod(os.path.join(bin_dir, "acorn-fdisk"), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
