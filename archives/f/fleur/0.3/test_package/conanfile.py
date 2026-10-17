#!/usr/bin/env python3
"""Conan test_package — fleur 0.3 消费者验证测试.

test.c 从消费者视角调用 fleur 公开 API（fleur_initialize/add/check/destroy），
通过 Conan CMakeDeps/CMakeToolchain 链接已安装包，验证编译/链接/运行。
test() 以真实 self.run 执行构建出的 test_fleur 消费者二进制（L0d 门禁）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class FleurTestConan(ConanFile):
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
        # L0d: test() 必须包含 self.run 并真实执行消费者二进制（非空壳）
        if can_run(self):
            test_bin = os.path.join(self.cpp.build.bindirs[0], "test_fleur")
            if not os.path.exists(test_bin):
                raise RuntimeError(f"test binary not found: {test_bin}")
            self.run(test_bin, env="conanrun")
