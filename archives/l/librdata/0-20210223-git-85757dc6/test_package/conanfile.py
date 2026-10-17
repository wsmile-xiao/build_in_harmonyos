#!/usr/bin/env python3
"""Conan test_package — librdata（L1 消费者测试）。

用 CMakeDeps 生成的 librdata-config.cmake 找到被测包，链接 librdata::librdata，
跑一轮「写 → 读」往返（.RData 与 .rds 两条路径），逐项断言公开 API 的行为。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibrdataTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        exe = os.path.join(self.cpp.build.bindirs[0], "test_librdata")
        # 走 conanrun：被测产物的运行期依赖（含静态内链的后端）由 Conan 注入
        self.run(exe, env="conanrun")
