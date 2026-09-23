#!/usr/bin/env python3
"""Conan recipe — clipp 1.2.3 (header-only, single include/clipp.h).

clipp is a single-header C++11 command line interfaces library (MIT).
No build step is needed: the full library lives in include/clipp.h.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class ClippConan(ConanFile):
    name = "clipp"
    version = "1.2.3"
    description = "Command line interfaces for modern C++ (single header, C++11)"
    license = "MIT"
    homepage = "https://github.com/muellan/clipp"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only 无编译步骤；补丁管线入口（当前无补丁，apply 为空操作）
        apply_conandata_patches(self)

    def package(self):
        copy(self, "clipp.h",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE",
             src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "clipp")
        self.cpp_info.set_property("cmake_target_name", "clipp::clipp")