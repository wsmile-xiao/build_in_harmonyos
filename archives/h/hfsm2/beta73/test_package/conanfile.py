#!/usr/bin/env python3
"""Conan test_package — hfsm2 beta73 消费者验证（L1）。

真实调用 hfsm2 API（MachineT + Root + transition），验证 header-only
头文件在 OHOS aarch64 工具链下能被消费者正常 include、编译并运行。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_hfsm2")
            self.run(bin_path, env="conanrun")