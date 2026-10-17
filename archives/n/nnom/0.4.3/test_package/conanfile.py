#!/usr/bin/env python3
"""Conan test_package — nnom 0.4.3 L1 official test.

CI runs this via `conan create` (which invokes test_package).  The
consumer builds a tiny input->dense->output model through the public
nnom API, runs it, and asserts the quantized output.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class NnomTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # 直接运行消费者与鸿蒙专项二进制，提供 self.run 真实执行证据（L0d）
        test_dir = os.path.join(self.cpp.build.bindirs[0])
        self.run(os.path.join(test_dir, "test_nnom"), env="conanrun")
        self.run(os.path.join(test_dir, "test_ohos"), env="conanrun")