#!/usr/bin/env python3
"""Conan test_package — ut 2.3.1 消费者验证。

真实 include <boost/ut.hpp> 并执行断言（R34），由 conan create 自动运行。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class UtTestConan(ConanFile):
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
        # Alternatively, run the binary directly:
        # self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_ut')}", env="conanrun")
