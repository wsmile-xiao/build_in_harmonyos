#!/usr/bin/env python3
"""Conan recipe — jthread-lite 0.1.0 (CMake header-only library).

jthread-lite 是 std::jthread 的 C++11 单文件头文件回移库（nonstd-lite 家族）。
header-only（CMake INTERFACE library），无任何编译产物与依赖；
基于 std::thread，构建期仅需安装 include/ 头文件。
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class JthreadLiteConan(ConanFile):
    name = "jthread-lite"
    version = "0.1.0"
    description = "A C++20-like std::jthread for C++11 and later in a single-file header-only library"
    license = "BSL-1.0"
    homepage = "https://github.com/martinmoene/jthread-lite"
    url = ""  # CI fills this
    topics = ("jthread", "thread", "header-only", "cpp11", "cpp17", "cpp20")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            # 上游 CMake 无平台断言；显式声明保证 CMake 4.x 在 OHOS 上正常配置。
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["JTHREAD_LITE_OPT_BUILD_TESTS"] = "OFF"
        tc.variables["JTHREAD_LITE_OPT_BUILD_EXAMPLES"] = "OFF"
        tc.generate()

    def build(self):
        # header-only：仅验证 CMake configure 可解析；无编译产物。
        cmake = CMake(self)
        cmake.configure()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "jthread-lite")
        self.cpp_info.set_property("cmake_target_name", "nonstd::jthread-lite")
        self.cpp_info.libs = []