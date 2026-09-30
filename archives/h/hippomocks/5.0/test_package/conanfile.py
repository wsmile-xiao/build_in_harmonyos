#!/usr/bin/env python3
"""Conan test_package — hippomocks 5.0 consumer test.

Consumer view: builds a small business-style component using ONLY the
public header (hippomocks.h via <hippomocks.h>), the public API
(MockRepository / Mock<T> / ExpectCall / Return / With / VerifyAll),
links against the installed package and runs the mock scenario.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class HippomocksTestConan(ConanFile):
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
        # 消费者用例：直接运行并断言退出码（R34 实质测试，非空壳）
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_hippomocks")
        self.run(test_bin, env="conanrun")
        # 鸿蒙专项测试：独立于消费者用例计数
        ohos_bin = os.path.join(self.cpp.build.bindirs[0], "test_hippomocks_ohos")
        self.run(ohos_bin, env="conanrun")