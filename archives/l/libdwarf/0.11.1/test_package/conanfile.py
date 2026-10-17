#!/usr/bin/env python3
"""Conan test_package — libdwarf 0.11.1 L1 测试骨架.

bootstrap 阶段建立；adapt 阶段按 R34 完善为真实调用 dwarf_* API 的消费者。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

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
            return
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_package")
        self.run(bin_path, env="conanrun")