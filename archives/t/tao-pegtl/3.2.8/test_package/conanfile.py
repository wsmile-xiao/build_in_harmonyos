#!/usr/bin/env python3
"""Conan test_package — tao-pegtl 3.2.8 header-only 消费者验证 (R34).

真实 include 并调用 pegtl 解析接口，不伪造输出。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TaopegtlTestConan(ConanFile):
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
        # L0d 门禁要求 test() 含 self.run 实际执行被测二进制
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_tao_pegtl"),
                 env="conanrun")