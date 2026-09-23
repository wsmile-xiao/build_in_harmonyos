#!/usr/bin/env python3
"""Conan test_package — icecream-cpp 1.0.0 消费者验证（R34：实质调用被测库 API）."""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class IcecreamCppTestConan(ConanFile):
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
        # L0d：test() 必须包含 self.run 实际执行逻辑（R34），显式运行消费者可执行文件
        self.run("./test_icecream-cpp", env="conanrun")