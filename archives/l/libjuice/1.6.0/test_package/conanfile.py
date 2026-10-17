#!/usr/bin/env python3
"""Conan test_package for libjuice — Conan L1 official test + HarmonyOS 专项测试.

CI runs this automatically via `conan create` (which invokes test_package).
test_libjuice: consumer smoke test (crc32/base64/agent 真实 API 调用).
test_ohos: HarmonyOS 平台专项测试（agent 生命周期在 OHOS 上运行）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibjuiceTestConan(ConanFile):
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
        # 显式运行两个测试二进制（不经 ctest 也能验证）
        bindir = os.path.join(self.cpp.build.bindirs[0])
        self.run(os.path.join(bindir, "test_libjuice"), env="conanrun")
        self.run(os.path.join(bindir, "test_ohos"), env="conanrun")