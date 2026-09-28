#!/usr/bin/env python3
"""Conan consumer test for packaged libshrinkwrap 1.2.0 (L1)."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibshrinkwrapTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

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
        # R34: 直接再跑一次二进制，保证 test_libshrinkwrap.cpp 的断言真实执行
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_libshrinkwrap"),
                 env="conanrun")
