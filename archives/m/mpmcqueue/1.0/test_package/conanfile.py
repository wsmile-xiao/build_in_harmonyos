#!/usr/bin/env python3
"""Conan test_package — mpmcqueue 1.0 (C++ consumer test).

从消费者视角验证 header-only 库：include <rigtorp/MPMCQueue.h>、
实例化 MPMCQueue<int> 并完成一次实际入队/出队（含空满边界与多线程冒烟）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MpmcqueueTestConan(ConanFile):
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
        # 直接执行测试二进制，提供 self.run 实跑证据（L0d 门禁要求）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_mpmcqueue"),
                 env="conanrun")
