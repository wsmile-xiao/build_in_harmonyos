#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""libinklevel 0.9.7 消费者测试（conan test_package）

test() 直接执行消费者测试程序并按返回码判定，不用 ctest 中转：
CI 的 test() 实际执行检查（L0d / PF3）要求 test_package 内显式调用 self.run()。
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("cross-build, skip consumer test execution")
            return
        bindir = self.cpp.build.bindirs[0]
        # 消费者契约测试 + 鸿蒙 PC 平台特有测试（两个可执行文件，均须 RC=0）
        exe_consumer = os.path.join(bindir, "test_package")
        exe_ohos = os.path.join(bindir, "test_ohos")
        self.run(f'"{exe_consumer}"', env="conanrun")
        self.run(f'"{exe_ohos}"', env="conanrun")
