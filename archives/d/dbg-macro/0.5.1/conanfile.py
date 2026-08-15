#!/usr/bin/env python3
"""Conan recipe — dbg-macro 0.5.1 (header-only).

dbg(...) debug macro library (sharkdp). Header-only, zero dependencies.
"""
from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class DbgMacroConan(ConanFile):
    name = "dbg-macro"
    version = "0.5.1"
    package_type = "header-library"

    description = "dbg(...) macro for printf-style debugging (header-only)"
    homepage = "https://github.com/sharkdp/dbg-macro"
    license = "MIT"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"

    exports_sources = "patches/*"

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 测试依赖 Catch2 子模块（tarball 不含），禁用
        tc.variables["DBG_MACRO_ENABLE_TESTS"] = "OFF"
        # 上游 CMakeLists 声明 cmake_minimum_required(3.1)，CMake 4.x 已移除
        # <3.5 兼容——CMAKE_POLICY_VERSION_MINIMUM 须以命令行 cache 变量传入
        # （toolchain variables 不生效，cmake_minimum_required 检查更早）
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        # header-only：CMake 配置验证头文件结构完整
        cmake = CMake(self)
        cmake.configure()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "dbg_macro")
        self.cpp_info.set_property("cmake_target_name", "dbg_macro::dbg_macro")
        self.cpp_info.includedirs = ["include"]