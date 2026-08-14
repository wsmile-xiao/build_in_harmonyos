#!/usr/bin/env python3
"""Conan recipe — dragonbox 1.1.3 (header-only).

Fast float-to-string conversion library (zero dependencies, C++11).
"""
from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class DragonboxConan(ConanFile):
    name = "dragonbox"
    version = "1.1.3"
    package_type = "header-library"

    description = "Fast float-to-string conversion (header-only, zero deps)"
    homepage = "https://github.com/jk-jeon/dragonbox"
    license = "Apache-2.0"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["DRAGONBOX_ENABLE_SUBPROJECT"] = "OFF"
        # 纯 header-only：不构建/安装 libdragonbox_to_chars.a（to_chars 是 header 实现）
        tc.variables["DRAGONBOX_INSTALL_TO_CHARS"] = "OFF"
        tc.generate()

    def build(self):
        # header-only：CMake 配置验证头文件结构完整（不编译库）
        cmake = CMake(self)
        cmake.configure()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE-*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "dragonbox")
        self.cpp_info.set_property("cmake_target_name", "dragonbox::dragonbox")
        self.cpp_info.includedirs = ["include/dragonbox-1.1.3"]