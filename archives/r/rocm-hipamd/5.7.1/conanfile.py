#!/usr/bin/env python3
"""Conan recipe — rocm-hipamd 5.7.1 (HIP header-only, no build system)."""
import os
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RocmHipamdConan(ConanFile):
    name = "rocm-hipamd"
    version = "5.7.1"
    description = "HIP (Heterogeneous-Compute Interface for Portability) from AMD ROCm 5.7.1"
    license = "MIT"
    homepage = "https://github.com/ROCm/HIP"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.cmake", src=os.path.join(self.source_folder, "cmake"),
             dst=os.path.join(self.package_folder, "cmake"))
        copy(self, "hip-lang-config.cmake.in", src=self.source_folder,
             dst=os.path.join(self.package_folder, "cmake"))
        copy(self, "*", src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "VERSION", src=self.source_folder,
             dst=self.package_folder)
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.builddirs = ["cmake"]
