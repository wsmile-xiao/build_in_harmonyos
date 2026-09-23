#!/usr/bin/env python3
"""Conan test_package — cpmtools 2.23 消费者测试（CMake 构建 + popen 直读断言）。"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class CpmtoolsTestConan(ConanFile):
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
        if not can_run(self):
            self.output.info("cross-building: cpmtools runtime checks deferred to OHOS runner")
            return
        bin_dir = os.path.join(self.dependencies["cpmtools"].package_folder, "bin")
        exe = os.path.join(self.cpp.build.bindir, "test_cpmtools")
        self.run(f'"{exe}" "{bin_dir}"')