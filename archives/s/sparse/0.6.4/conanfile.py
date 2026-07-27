#!/usr/bin/env python3
"""Conan recipe — sparse 0.6.4 (Makefile)"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SparseConan(ConanFile):
    name = "sparse"
    version = "0.6.4"
    description = "C semantic parser and static analysis tool"
    license = "MIT"
    homepage = "https://sparse.sourceforge.net/"
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
        compiler_executables = self.conf.get("tools.build:compiler_executables", default={})
        cc = compiler_executables.get("c", "clang")
        self.run(f"make CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "sparse", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "cgcc", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "libsparse.a", self.source_folder, os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", self.source_folder, os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["sparse"]
        self.cpp_info.bindirs = ["bin"]
