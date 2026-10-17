#!/usr/bin/env python3
"""Conan test_package — Conan L1 official test (consumer view).

CI runs this automatically via `conan create` (which invokes test_package).
test() 显式运行消费者二进制（L0d 要求非 stub）：二进制调用被测包的公开 API
（ClownResampler_Precompute / LowLevel_Init / LowLevel_Resample）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ClownresamplerTestConan(ConanFile):
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
        # 显式运行消费者可执行文件（非 stub）：公开 API 实际调用 + 可观察输出。
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_clownresampler"),
                 env="conanrun")
