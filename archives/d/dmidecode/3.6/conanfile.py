#!/usr/bin/env python3
"""Conan recipe for dmidecode 3.6 — command-line SMBIOS/DMI decoder tool.

dmidecode is a pure Makefile project (no configure script).
It reads SMBIOS/DMI data from /dev/mem or sysfs and displays hardware info.
On HarmonyOS/aarch64, /dev/mem may not exist; --from-dump works for offline analysis.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class DmidecodeConan(ConanFile):
    name = "dmidecode"
    version = "3.6"
    description = "读取 SMBIOS/DMI 数据的命令行工具，显示硬件信息"
    license = "GPL-2.0-or-later"
    homepage = "https://www.nongnu.org/dmidecode/"
    url = ""  # CI fills this

    # R32: settings.os must check in ("Linux", "OHOS")
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # No external dependencies

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler path from Conan conf, not bare 'clang' in PATH
        compilers = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cc = compilers.get("c") or "clang"
        self.run(f'make CC="{cc}" -j1', cwd=self.source_folder)

    def package(self):
        # dmidecode is a tool — package the binary and man page
        copy(self, "dmidecode", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "dmidecode.8", os.path.join(self.source_folder, "man"),
             os.path.join(self.package_folder, "share", "man", "man8"))

    def package_info(self):
        # Tool package — no libraries to link
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        # Set bindirs so consumers can find the binary
        self.cpp_info.bindirs = ["bin"]
