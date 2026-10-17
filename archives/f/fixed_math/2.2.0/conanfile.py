#!/usr/bin/env python3
"""Conan recipe — fixed_math 2.2.0 (CMake, header-only C++23 fixed-point math).

fixed_math is a header-only C++23 fixed-point math library.
Installs headers + CMake package config (fixed_math::fixed_math).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class FixedmathConan(ConanFile):
    name = "fixed_math"
    version = "2.2.0"
    description = "Header-only C++23 fixed-point math library"
    license = "BSL-1.0"
    homepage = "https://github.com/arturbac/fixed_math"
    url = ""  # CI fills this

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
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # 上游单测通过 CPMAddPackage 从 GitHub 拉 arturbac/ut-ext (boost-ext/ut)，
        # CI worker 网络禁 GitHub 会失败；fixed_math 为 header-only 库，test_package
        # 已含消费者测试覆盖，配方构建关闭上游单测（上游测试台账另行枚举）。
        tc.variables["FIXEDMATH_ENABLE_UNIT_TESTS"] = "OFF"
        tc.variables["FIXEDMATH_ENABLE_DEVEL_CODE"] = "OFF"
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
        # 上游 install 把头文件装到 include/fixed_math（下划线），但 README/示例
        # 均用 #include <fixedmath/...>（无下划线）；按文档路径补装一份，保证
        # 消费者按官方文档 include 可用。
        src_inc = os.path.join(self.source_folder, "fixed_lib", "include", "fixedmath")
        copy(self, "*.h", src=src_inc, dst=os.path.join(self.package_folder, "include", "fixedmath"))
        copy(self, "*.hpp", src=src_inc, dst=os.path.join(self.package_folder, "include", "fixedmath"))
        copy(self, "LICENCE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "fixed_math")
        self.cpp_info.set_property("cmake_target_name", "fixed_math::fixed_math")
