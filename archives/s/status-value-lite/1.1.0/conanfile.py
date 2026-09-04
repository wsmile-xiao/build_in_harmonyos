#!/usr/bin/env python3
"""Conan recipe — status-value-lite 1.1.0 (CMake header-only library).

status-value-lite 是 std::experimental::status_value 的 C++11/14/17 单文件头文件回移库
（Martin Moene 的 nonstd-lite 系列）。header-only（CMake INTERFACE library），无任何依赖。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building


class StatusValueLiteConan(ConanFile):
    name = "status-value-lite"
    version = "1.1.0"
    description = "A class for status and optional value for C++11 and later, C++98 variant provided in a single-file header-only library"
    license = "BSL-1.0"
    homepage = "https://github.com/nonstd-lite/status-value-lite"
    url = ""  # CI fills this
    topics = ("status-value", "header-only", "cpp11", "cpp17")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        # 无补丁/额外源文件，本版本不需要 exports_sources 内容
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 不识别 OHOS 目标平台，映射为 Linux/aarch64
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # 集成上游测试（lest 框架）
        tc.variables["NSSV_OPT_BUILD_TESTS"] = True
        tc.variables["NSSV_OPT_BUILD_EXAMPLES"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 运行上游 CTest；交叉编译场景跳过运行时测试
        if cross_building(self):
            self.output.info("cross-building: skip upstream CTest")
            return
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "status-value-lite")
        self.cpp_info.set_property("cmake_target_name", "nonstd::status_value-lite")
        self.cpp_info.libs = []
