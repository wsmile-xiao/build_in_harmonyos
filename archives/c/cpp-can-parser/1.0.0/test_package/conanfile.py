#!/usr/bin/env python3
"""cpp-can-parser 1.0.0 test_package — 消费者验证 + HarmonyOS 专项测试。

编译并运行两个真实可执行用例：
  1. test_consumer         — 通过 CppCAN::CANDatabase::fromString 解析内嵌 DBC，
                             校验帧/信号 API（真实调用被测库 API 并断言）。
  2. harmonyos_specific_test — OHOS 平台专项：核验 __OHOS__/__aarch64__ 宏并实际
                             调用库 API 解析 DBC（非空壳、非只打印）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CppCanParserTestConan(ConanFile):
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
        bin_dir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bin_dir, "test_consumer"), env="conanrun")
        self.run(os.path.join(bin_dir, "harmonyos_specific_test"), env="conanrun")
