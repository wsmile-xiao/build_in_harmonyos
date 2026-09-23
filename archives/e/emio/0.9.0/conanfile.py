#!/usr/bin/env python3
"""Conan recipe — emio 0.9.0 (header-only, CMake-based).

C++20 character input/output library for embedded systems. Header-only:
packages include/emio/*.hpp plus the LICENSE file. No dependencies.
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class EmioConan(ConanFile):
    name = "emio"
    version = "0.9.0"
    package_type = "header-library"

    description = "Character input/output library for embedded systems (C++20, header-only)"
    homepage = "https://github.com/Viatorus/emio"
    license = "MIT"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("io", "format", "scan", "header-only", "c++20", "embedded")

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # header-only: nothing to compile; patches (currently empty) applied for completeness
        apply_conandata_patches(self)

    def package(self):
        # header-only——安装 include/emio/ 头文件目录（含 detail/ 子目录）
        import shutil as _shutil
        inc_dst = os.path.join(self.package_folder, "include")
        _shutil.copytree(os.path.join(self.source_folder, "include", "emio"),
                         os.path.join(inc_dst, "emio"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "emio")
        self.cpp_info.set_property("cmake_target_name", "emio::emio")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
