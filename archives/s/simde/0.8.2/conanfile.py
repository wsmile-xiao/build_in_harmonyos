#!/usr/bin/env python3
"""Conan recipe — simde 0.8.2 (header-only SIMD library).

simde 提供跨架构 SIMD 头文件（simde/ 目录，469 个头文件），无编译产物。
上游使用 meson 仅安装头文件；本配方直接以 header-library 方式打包 include 目录。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class SimdeConan(ConanFile):
    name = "simde"
    version = "0.8.2"
    package_type = "header-library"

    description = "SIMDe: portable SIMD intrinsics across architectures (header-only)"
    homepage = "https://github.com/simd-everywhere/simde"
    license = "MIT"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # header-only：无编译产物；仅应用补丁（当前 patches 为空）
        apply_conandata_patches(self)

    def package(self):
        copy(self, "simde/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "simde")
        self.cpp_info.set_property("cmake_target_name", "simde::simde")
        self.cpp_info.includedirs = ["include"]