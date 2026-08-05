#!/usr/bin/env python3
"""Conan recipe — expected-lite 0.6.3 (CMake header-only library).

expected-lite 是 std::expected 的 C++11/14/17 单文件头文件回移库。
header-only（CMake INTERFACE library），无任何依赖。
"""
from conan import ConanFile
from conan.tools.files import get
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building


class ExpectedLiteConan(ConanFile):
    name = "expected-lite"
    version = "0.6.3"
    description = "Expected objects in C++11 and later in a single-file header-only library"
    license = "BSL-1.0"
    homepage = "https://github.com/martinmoene/expected-lite"
    url = ""  # CI fills this
    topics = ("expected", "header-only", "cpp11", "cpp17")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

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
        tc.variables["EXPECTED_LITE_OPT_BUILD_TESTS"] = True
        tc.variables["EXPECTED_LITE_OPT_BUILD_EXAMPLES"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 运行上游测试 (4 个 CTest 用例: cpp11/cpp14/cpp17/cpp20)
        # 交叉编译场景下跳过运行时测试，与 test_package/conanfile.py 行为一致
        if cross_building(self):
            self.output.info("cross-building: skip upstream CTest")
            return
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "expected-lite")
        self.cpp_info.set_property("cmake_target_name", "nonstd::expected-lite")
        self.cpp_info.libs = []
