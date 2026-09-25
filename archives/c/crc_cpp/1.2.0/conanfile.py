#!/usr/bin/env python3
"""Conan recipe — crc_cpp 1.2.0 (header-only constexpr CRC library).

crc_cpp 是 header-only 的 constexpr / 编译期 CRC 库（C++20，small-table 查找表，
支持 8~64 位常见 CRC 算法，MIT）。无编译步骤：全部实现位于 include/crc_cpp.h。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class CrcCppConan(ConanFile):
    name = "crc_cpp"
    version = "1.2.0"
    description = "CRC routines — header only, constexpr / compile time small-table based CRC library"
    license = "MIT"
    homepage = "https://github.com/AshleyRoll/crc_cpp"
    url = ""  # CI fills this
    topics = ("crc", "crc32", "constexpr", "header-only", "cpp20")

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
        copy(self, "crc_cpp.h",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE",
             src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "crc_cpp")
        self.cpp_info.set_property("cmake_target_name", "crc_cpp::crc_cpp")