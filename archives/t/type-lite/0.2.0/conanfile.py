#!/usr/bin/env python3
"""Conan recipe — type-lite 0.2.0 (CMake header-only library).

type-lite 是 C++98/11/14/17 强类型（strong types）单文件头文件库。
header-only（CMake INTERFACE library），无任何依赖。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building


class TypeLiteConan(ConanFile):
    name = "type-lite"
    version = "0.2.0"
    description = "Strong types for C++98, C++11 and later in a single-file header-only library"
    license = "BSL-1.0"
    homepage = "https://github.com/nonstd-lite/type-lite"
    url = ""  # CI fills this
    topics = ("strong-types", "header-only", "cpp11", "cpp17", "cpp98")

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
        # 集成上游测试用例（在 build() 阶段执行）
        tc.variables["TYPE_LITE_OPT_BUILD_TESTS"] = True
        tc.variables["TYPE_LITE_OPT_BUILD_EXAMPLES"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 运行上游测试 (4 个目标: cpp98/cpp11/cpp14/cpp17)
        # 交叉编译场景下跳过运行时测试，与 test_package/conanfile.py 行为一致
        if cross_building(self):
            self.output.info("cross-building: skip upstream CTest")
            return
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "type-lite")
        self.cpp_info.set_property("cmake_target_name", "nonstd::type-lite")
        self.cpp_info.libs = []