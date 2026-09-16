#!/usr/bin/env python3
"""Conan recipe — googletest 1.17.0 (CMake).

GoogleTest + GoogleMock C++ testing framework. Zero dependencies, C++17.
Upstream-native package name (googletest); same source as gtest/1.17.0(.1)
(published under the conan-style name). CMakeDeps exports GTestConfig.cmake
with GTest::gtest / GTest::gtest_main / GTest::gmock / GTest::gmock_main
targets, matching upstream's installed config package, so downstream
`find_package(GTest CONFIG REQUIRED)` (e.g. scnlib) resolves against this
package.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches
import os

required_conan_version = ">=2.0"


class GoogletestConan(ConanFile):
    name = "googletest"
    version = "1.17.0"
    package_type = "library"

    description = "GoogleTest and GoogleMock: C++ testing and mocking framework"
    homepage = "https://github.com/google/googletest"
    license = "BSD-3-Clause"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    exports_sources = "patches/*"

    def export_sources(self):
        copy(self, "LICENSE", src=self.recipe_folder, dst=self.export_sources_folder)

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
        # CMakeDeps 生成 GTestConfig.cmake：与上游 googletest CMake install 导出的
        # config 包名一致（find_package(GTest)），下游 scnlib 等可直接消费
        self.cpp_info.set_property("cmake_file_name", "GTest")

        gtest = self.cpp_info.components["gtest"]
        gtest.libs = ["gtest"]
        gtest.set_property("cmake_target_name", "GTest::gtest")

        gtest_main = self.cpp_info.components["gtest_main"]
        gtest_main.libs = ["gtest_main"]
        gtest_main.requires = ["gtest"]
        gtest_main.set_property("cmake_target_name", "GTest::gtest_main")

        gmock = self.cpp_info.components["gmock"]
        gmock.libs = ["gmock"]
        gmock.requires = ["gtest"]
        gmock.set_property("cmake_target_name", "GTest::gmock")

        gmock_main = self.cpp_info.components["gmock_main"]
        gmock_main.libs = ["gmock_main"]
        gmock_main.requires = ["gmock", "gtest"]
        gmock_main.set_property("cmake_target_name", "GTest::gmock_main")
