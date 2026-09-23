#!/usr/bin/env python3
"""Conan test_package — pixelmatch-cpp 0.10.0 (header-only consumer test).

CI runs this automatically via `conan create` (which invokes test_package).
The consumer test compiles against the installed public header and calls
the public API mapbox::pixelmatch() with real RGBA buffers.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PixelmatchcppTestConan(ConanFile):
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
        # 直接运行已编译的消费者测试二进制（真实调用 mapbox::pixelmatch()，
        # 1x1 黑白像素 mismatch=1、相同图像 mismatch=0），非零退出码即失败。
        # L0d 静态检查要求 test() 必须含 self.run() 真实执行测试入口。
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_pixelmatch_cpp")
        self.run(f'"{test_bin}"', env="conanrun")
        # 同时经 ctest 注册表运行，保留上游入口统计口径。
        cmake = CMake(self)
        cmake.test()
