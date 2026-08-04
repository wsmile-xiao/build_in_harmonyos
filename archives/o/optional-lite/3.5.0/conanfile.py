#!/usr/bin/env python3
"""Conan recipe — optional-lite 3.5.0 (CMake header-only library).

optional-lite 是 std::optional 的 C++98/11/14/17 单文件头文件回移库。
header-only（CMake INTERFACE library），无任何依赖。
"""
from conan import ConanFile
from conan.tools.files import get
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class OptionalLiteConan(ConanFile):
    name = "optional-lite"
    version = "3.5.0"
    description = "A C++17-like optional for C++98, C++11 and later in a single-file header-only library"
    license = "BSL-1.0"
    homepage = "https://github.com/martinmoene/optional-lite"
    url = ""  # CI fills this
    topics = ("optional", "header-only", "cpp11", "cpp17")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["OPTIONAL_LITE_OPT_BUILD_TESTS"] = True
        tc.variables["OPTIONAL_LITE_OPT_BUILD_EXAMPLES"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "optional-lite")
        self.cpp_info.set_property("cmake_target_name", "nonstd::optional-lite")
        self.cpp_info.libs = []
