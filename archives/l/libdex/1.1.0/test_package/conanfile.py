#!/usr/bin/env python3
"""Conan test_package — libdex L1 消费者测试。

CI 通过 conan create 自动运行（调用 test_package）：编译 test.c 为 test_libdex
可执行文件，并在 test() 中实际运行，验证已安装的 libdex 公开头文件/API
（dex_init/dex_scheduler_spawn/dex_future_get_status/dex_future_get_value）
可被第三方编译、链接、调用并正常运行。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibdexTestConan(ConanFile):
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
        self.run("ctest --output-on-failure", env="conanrun")
