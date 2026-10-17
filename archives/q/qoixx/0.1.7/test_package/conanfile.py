#!/usr/bin/env python3
"""Conan test_package — qoixx 0.1.7 消费者视角真实用例（L1 / R34 / PF3）.

test() 用 self.run() 真实执行编译出的 test_qoixx（PF3/CI L0c 口径），
test.cpp 里任一断言失败 → 进程 rc != 0 → conan create 失败。
消费者断言数以运行期末行 `QOIXX-CONSUMER checks=<N>` 为准（见 MANIFEST.yml，N=14）。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class QoixxTestConan(ConanFile):
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
            return
        # PF3/L0c：必须真实执行被测二进制（任一断言失败 rc != 0 即让本测试失败）
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_qoixx")
        self.run(cmd, env="conanrun")
