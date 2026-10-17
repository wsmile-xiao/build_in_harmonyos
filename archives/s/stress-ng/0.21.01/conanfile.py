#!/usr/bin/env python3
"""Conan recipe for stress-ng — a command-line stress testing tool."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class StressngConan(ConanFile):
    name = "stress-ng"
    version = "0.21.01"
    description = "stress-ng will stress test a computer system in various selectable ways"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ColinIanKing/stress-ng"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        self.run(f"make -C {self.source_folder} CC={cc} -j1")

    def package(self):
        copy(self, "stress-ng", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "stress-ng.1.gz", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
