#!/usr/bin/env python3
"""Conan recipe — easyloggingpp 9.97.1 (single-header + single .cc logging library).

easyloggingpp 自 issue #445 起为「单头 + 单一源文件」模式：消费者需链接
src/easylogging++.cc（README: "will still need easylogging++.cc file in
order to compile"）。上游 CMakeLists 提供 build_static_lib=ON 生成静态库，
本配方启用它以产出可链接的 libeasyloggingpp.a。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches


class EasyloggingppConan(ConanFile):
    name = "easyloggingpp"
    version = "9.97.1"
    description = "Easylogging++ single header C++ logging library"
    license = "MIT"
    homepage = "https://github.com/abumq/easyloggingpp"
    url = ""  # CI fills this

    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32: 平台判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                "easyloggingpp 只支持 Linux/OHOS/FreeBSD/Macos/Windows，当前: {}".format(self.settings.os))

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake does not recognize OHOS as a target platform
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        # 上游默认 build_static_lib=OFF 只装头文件；启用静态库以产出可链接产物
        tc.variables["build_static_lib"] = True
        tc.variables["CMAKE_CXX_STANDARD"] = 14
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        # 上游 cmake_minimum_required(2.8.7) 与 CMake 4.x 不兼容（CMake 4 移除 <3.5 兼容）
        # 该策略变量须在 configure 早期从 cache 读取，必须用 cache_variables
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "easyloggingpp")
        self.cpp_info.set_property("cmake_target_name", "easyloggingpp::easyloggingpp")
        self.cpp_info.libs = ["easyloggingpp"]
