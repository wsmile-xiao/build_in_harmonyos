#!/usr/bin/env python3
"""Conan test_package — dact 0.8.42 消费者测试（CMake 构建 + popen 直读断言）。"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class DactTestConan(ConanFile):
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
            self.output.info("cross-building: dact runtime checks deferred to OHOS runner")
            return
        pkg = self.dependencies["dact"].package_folder
        exe = os.path.join(self.cpp.build.bindir, "test_dact")
        self.run(f'"{exe}" "{pkg}"')