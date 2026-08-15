#!/usr/bin/env python3
"""Conan recipe — dlpack 1.3 (header-only).

DLPack: Open In Memory Tensor Structure (deep learning tensor exchange
standard). Header-only, zero dependencies.
"""
from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class DlpackConan(ConanFile):
    name = "dlpack"
    version = "1.3"
    package_type = "header-library"

    description = "Open In Memory Tensor Structure (header-only, zero deps)"
    homepage = "https://github.com/dmlc/dlpack"
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
        # BUILD_MOCK：编译 mock_main.cc 验证 dlpack.h API（上游测试）
        tc.variables["BUILD_MOCK"] = "ON"
        tc.variables["BUILD_DOCS"] = "OFF"
        tc.generate()

    def build(self):
        # header-only：BUILD_MOCK 编译验证 API 可用（上游 tests/scripts/task_build.sh）
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "dlpack")
        self.cpp_info.set_property("cmake_target_name", "dlpack::dlpack")
        self.cpp_info.includedirs = ["include"]