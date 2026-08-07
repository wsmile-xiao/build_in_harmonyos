#!/usr/bin/env python3
"""Conan test_package — libabigail L1 测试.

真测试（R34）：test_libabigail.cc 构造 abigail::ir::environment 并调用
abigail::tools_utils::get_library_version_string()（链接 -labigail 实质调用），
随后 test() 再执行 abidw --version 校验命令行工具可用。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibabigailTestConan(ConanFile):
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
        # 校验命令行工具：abidw --version 应输出 1.4.x 并退出 0
        self.run("abidw --version", env="conanrun")
