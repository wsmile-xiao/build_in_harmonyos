#!/usr/bin/env python3
"""Conan recipe — variant-lite 2.0.0 (CMake header-only library).

variant-lite 是 std::variant 的 C++98/11/14/17 单文件头文件回移库。
header-only（CMake INTERFACE library），无任何依赖。
"""
from conan import ConanFile
from conan.tools.files import get
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class VariantLiteConan(ConanFile):
    name = "variant-lite"
    version = "2.0.0"
    description = "A C++17-like variant for C++98, C++11 and later in a single-file header-only library"
    license = "BSL-1.0"
    homepage = "https://github.com/martinmoene/variant-lite"
    url = ""  # CI fills this
    topics = ("variant", "header-only", "cpp11", "cpp17")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake does not recognize OHOS as a target platform.
        # OHOS 的 Conan arch=armv8 不能直接作为 CMAKE_SYSTEM_PROCESSOR，需映射为 aarch64；
        # Linux 保留实际架构值（str(self.settings.arch)），避免 x86_64 等场景被错误覆盖。
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        elif self.settings.os == "Linux":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.variables["VARIANT_LITE_OPT_BUILD_TESTS"] = True
        tc.variables["VARIANT_LITE_OPT_BUILD_EXAMPLES"] = False
        # Force use of nonstd::variant instead of std::variant.
        # Upstream test/variant.t.cpp (issue 31, convert-copy-construct cases) relies on
        # variant-lite's own converting constructor semantics that differ from std::variant
        # (std::variant rejects int -> variant<double, std::string> by overload resolution).
        # The OHOS clang 15 libc++ std::variant implementation triggers hard errors during
        # template instantiation, breaking the cpp17 test target. Selecting the nonstd
        # implementation keeps the upstream test expectations consistent across all
        # language standards and avoids the libc++ incompatibility.
        tc.variables["VARIANT_LITE_OPT_SELECT_NONSTD"] = True
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
        self.cpp_info.set_property("cmake_file_name", "variant-lite")
        self.cpp_info.set_property("cmake_target_name", "nonstd::variant-lite")
        self.cpp_info.libs = []
