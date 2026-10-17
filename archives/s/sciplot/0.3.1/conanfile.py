#!/usr/bin/env python3
"""Conan recipe — sciplot 0.3.1 (CMake, header-only).

sciplot 是一个基于 gnuplot 的现代 C++17 科学绘图头文件库。
header-only（CMake INTERFACE library），无任何第三方依赖，仅传播 cxx_std_17 编译特性。
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SciplotConan(ConanFile):
    name = "sciplot"
    version = "0.3.1"
    description = "A modern C++ scientific plotting library powered by gnuplot"
    license = "MIT"
    homepage = "https://sciplot.github.io"
    url = ""  # CI fills this
    topics = ("plotting", "gnuplot", "header-only", "cpp17")

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
        # E092: CMake 不识别 OHOS 为目标平台，映射为 Linux/aarch64
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # 上游 tests 子项目 tests/testing-project 声明 cmake_minimum_required(VERSION 3.0)，
        # CMake 4.x 已移除对 <3.5 的兼容，需放行策略版本下限。
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # header-only 库：关闭示例与文档，保留上游测试作为消费者编译验证
        tc.variables["SCIPLOT_BUILD_EXAMPLES"] = "OFF"
        tc.variables["SCIPLOT_BUILD_TESTS"] = "ON"
        tc.variables["SCIPLOT_BUILD_DOCS"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游测试: sciplot 用 add_custom_target(tests) 注册测试而非 CTest，
        # cmake.test() 会找不存在的 "test" 目标，因此直接运行测试二进制。
        tests_bin = os.path.join(self.cpp.build.bindirs[0], "tests", "sciplot-cpptests")
        self.run(tests_bin, env="conanrun")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "sciplot")
        self.cpp_info.set_property("cmake_target_name", "sciplot::sciplot")
        self.cpp_info.libs = []