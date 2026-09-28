#!/usr/bin/env python3
"""test_package — sockpp 1.0.0 消费者视角验证（L1 / 层 2）。

真实链接并调用 sockpp 公开 API：版本指纹、地址解析、TCP 环回
accept/connect 收发、AF_UNIX socketpair 收发。断言数即 PR 正文
「鸿蒙特有测试」行的取值来源。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class SockppTestConan(ConanFile):
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
        exe = os.path.join(self.cpp.build.bindirs[0], "test_sockpp")
        self.run(exe, env="conanrun")
