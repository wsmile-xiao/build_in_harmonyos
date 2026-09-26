#!/usr/bin/env python3
"""Conan test_package — kann 0.

消费者程序调用 kann 公开 API（kann_layer_*/kann_new/kann_train_fnn1/
kann_apply1）训练并预测 popcount 任务，验证第三方使用者可编译、链接、
调用并正常运行。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class KannTestConan(ConanFile):
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
        # L0d: test() 必须含 self.run()（CI 静态门禁，防空壳测试）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_kann"), env="conanrun")
