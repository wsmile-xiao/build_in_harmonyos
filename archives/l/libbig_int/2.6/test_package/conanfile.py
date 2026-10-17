#!/usr/bin/env python3
"""Conan test_package — libbig_int 2.6 L1 test.

消费者视角验证：仅通过已安装的公开头文件 (big_int_full.h) 与公开 API 编译、
链接并运行，验证 test.c 中 10 组断言全部通过（退出码 0）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibbigIntTestConan(ConanFile):
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
        # 直接运行消费者可执行文件（L0d 门禁要求 test() 内含 self.run）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libbig_int"),
                 env="conanrun")