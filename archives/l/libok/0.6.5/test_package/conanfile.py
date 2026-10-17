#!/usr/bin/env python3
"""Conan test_package — libok 0.6.5 L1 测试。

通过已安装的 libok 公开头文件与库（find_package + libok::libok）编译
消费者程序 test_libok，并在 test() 中实际运行该二进制（R34/PF3）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibokTestConan(ConanFile):
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
        # 实际运行消费者二进制（验证第三方可编译、链接并调用公开 API）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libok"), env="conanrun")
        # 实际运行鸿蒙特有测试（r02：验证 OHOS 目标上 TAP 输出管线）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_ohos"), env="conanrun")
