#!/usr/bin/env python3
"""Conan test_package — fcitx5-utils 5.1.13

R34: 实质依赖被测包 API（find_package(Fcitx5Utils) + 链接 Fcitx5::Utils +
调用 stringutils/Key/SemanticVersion/StandardPaths 等真实 API，非空壳测试）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building


class Fcitx5UtilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # 头文件使用 std::span 等 C++20 设施；profile 可能是 cppstd=17，
        # 需显式覆盖 cppstd 块（与主配方一致）
        if self.settings.compiler.cppstd != "20":
            tc.blocks["cppstd"].values = {"cppstd": "20", "cppstd_extensions": "OFF"}
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        # 真实运行调用库 API 的可执行文件（鸿蒙特有测试，本机为 aarch64 OHOS 可原生运行）
        cmake = CMake(self)
        cmake.test()
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_fcitx5_utils"), env="conanrun")