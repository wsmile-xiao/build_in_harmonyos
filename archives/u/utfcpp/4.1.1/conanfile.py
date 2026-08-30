#!/usr/bin/env python3
"""Conan recipe — utfcpp 4.1.1 (CMake header-only library).

utfcpp 是一个 C++ 可移植 UTF-8 处理库，header-only（INTERFACE library，
CMake target utf8cpp::utf8cpp）。仅需 CMake 配置安装头文件和 CMake
配置文件，无二进制编译。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class UtfcppConan(ConanFile):
    name = "utfcpp"
    version = "4.1.1"
    description = "UTF-8 with C++ in a Portable Way"
    license = "BSL-1.0"
    homepage = "https://github.com/nemtrif/utfcpp"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def configure(self):
        # R32: 平台判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                "utfcpp 只支持 Linux/OHOS/FreeBSD/Macos/Windows，当前: {}".format(self.settings.os))

    def layout(self):
        cmake_layout(self)

    def package_id(self):
        # header-only 库，所有 settings 组合产出相同的包内容
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake does not recognize OHOS as a target platform
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.variables["CMAKE_CXX_STANDARD"] = 14
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = True
        tc.variables["UTF8CPP_ENABLE_TESTS"] = True
        tc.variables["UTF8CPP_ENABLE_BENCHMARKS"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if not cross_building(self):
            cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "utf8cpp")
        self.cpp_info.set_property("cmake_target_name", "utf8cpp::utf8cpp")
        # 上游头文件安装在 include/utf8cpp/ 子目录（消费方 #include
        # <utf8.h>——上游 INTERFACE_INCLUDE_DIRECTORIES 即指向
        # include/utf8cpp）。conan 默认 includedirs 是 include，需显式
        # 指向 include/utf8cpp 否则 test_package 编译报 utf8.h 找不到
        self.cpp_info.includedirs = ["include/utf8cpp"]
        self.cpp_info.libs = []
