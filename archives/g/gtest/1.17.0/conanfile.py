#!/usr/bin/env python3
"""Conan recipe — gtest 1.17.0 (CMake).

Google Test C++ testing framework. Zero dependencies, C++17.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches
import os

required_conan_version = ">=2.0"


class GtestConan(ConanFile):
    name = "gtest"
    version = "1.17.0"
    package_type = "library"

    description = "Google Test C++ testing framework"
    homepage = "https://github.com/google/googletest"
    license = "BSD-3-Clause"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.variables["BUILD_GMOCK"] = "ON"
        tc.variables["INSTALL_GTEST"] = "ON"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 构建上游测试套件（gtest_build_tests + gmock_build_tests）
        tc.variables["gtest_build_tests"] = "ON"
        tc.variables["gmock_build_tests"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "gtest")
        self.cpp_info.set_property("cmake_target_name", "gtest::gtest")
        self.cpp_info.libs = ["gtest"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]