#!/usr/bin/env python3
"""Conan recipe — string_theory 3.9 (CMake, header-only).

string_theory is a flexible modern C++ string library with type-safe
formatting and parsing. The upstream CMakeLists.txt builds a header-only
INTERFACE library (add_library(string_theory INTERFACE)); only headers
and CMake config files are installed.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class StringTheoryConan(ConanFile):
    name = "string_theory"
    version = "3.9"
    description = "Flexible modern C++ string library with type-safe formatting and parsing"
    license = "MIT"
    homepage = "https://github.com/zrax/string_theory"
    url = "https://github.com/zrax/string_theory"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # header-only INTERFACE 库：只安装头文件与 CMake config。
        # 上游 tests 通过 FetchContent 从 GitHub clone googletest v1.15.2，
        # CI worker 网络禁 GitHub 报连接失败；消费者验证由 test_package 覆盖。
        tc.variables["ST_BUILD_TESTS"] = "OFF"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "string_theory")
        self.cpp_info.set_property("cmake_target_name", "string_theory::string_theory")
