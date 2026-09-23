#!/usr/bin/env python3
"""Conan test_package for is_utf8 1.4.1 — 消费者视角测试（L1/层2）。

编译 test.cpp（链接 is_utf8::is_utf8 并实际调用 API），
can_run 时运行 ./is_utf8_test，失败即 conan create 失败。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class IsUtf8TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run(os.path.join(self.cpp.build.bindirs[0], "is_utf8_test"),
                     env="conanrun")
