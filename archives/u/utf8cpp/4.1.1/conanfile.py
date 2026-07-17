#!/usr/bin/env python3
"""Conan recipe — utf8cpp 4.1.1 (CMake header-only library).

utf8cpp 是一个 C++ UTF-8 编解码库，header-only（INTERFACE library）。
无任何依赖，仅包含头文件。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Utf8cppConan(ConanFile):
    name = "utf8cpp"
    version = "4.1.1"
    description = "C++ portable library for working with utf-8 encoding"
    license = "BSL-1.0"
    homepage = "https://github.com/nemtrif/utfcpp"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake does not recognize OHOS as a target platform
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # 集成上游测试用例 (R33: 上游测试应在 build() 阶段执行)
        tc.variables["UTF8CPP_ENABLE_TESTS"] = True
        tc.variables["UTF8CPP_ENABLE_BENCHMARKS"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 运行上游测试 (6 个 CTest 用例: negative/cpp11/cpp17/cpp20/apitests/noexceptionstests)
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "utf8cpp")
        self.cpp_info.set_property("cmake_target_name", "utf8cpp::utf8cpp")
        self.cpp_info.libs = []
