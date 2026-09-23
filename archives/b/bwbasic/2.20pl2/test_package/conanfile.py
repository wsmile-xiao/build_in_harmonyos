#!/usr/bin/env python3
"""Test package for bwbasic 2.20pl2 (BASIC interpreter CLI tool)

消费者测试：以包内 bwbasic 二进制执行一段内嵌 BASIC 程序，
断言算术/关系/数组执行输出与无效下标的错误路径。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BwbasicTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: skip runtime test")
            return
        driver = os.path.join(self.cpp.build.bindirs[0], "test_consumer")
        bwbasic_bin = os.path.join(
            self.dependencies["bwbasic"].cpp_info.bindirs[0], "bwbasic")
        self.run('"%s" "%s"' % (driver, bwbasic_bin), env="conanrun")
