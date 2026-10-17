#!/usr/bin/env python3
"""Conan test_package for muparserx 4.0.12 — exercises the library API on HarmonyOS PC."""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("Cross-building: defer execution to a HarmonyOS PC device")
            return
        # 消费者冒烟测试
        self.run(os.path.join(self.cpp.build.bindir, "test_package"), env="conanrun")
        # HarmonyOS 专项测试（__OHOS__ 宏 + 求值 + 变量 + 错误路径断言）
        self.run(os.path.join(self.cpp.build.bindir, "harmony_special_test"), env="conanrun")