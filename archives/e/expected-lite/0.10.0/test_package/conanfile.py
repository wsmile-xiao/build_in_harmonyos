#!/usr/bin/env python3
"""Test package for expected-lite 0.10.0 (header-only C++ expected library)

消费者测试使用 HarmonyOS 专项测试 test_expected_lite_harmonyos.cpp：
覆盖 OHOS aarch64 平台断言 + sysconf/getuid 等 OHOS libc 接口集成 + monadic 链。
"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building


class ExpectedLiteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake does not recognize OHOS as a target platform.
        # OHOS 的 Conan arch=armv8 不能直接作为 CMAKE_SYSTEM_PROCESSOR，需映射为 aarch64；
        # Linux 保留实际架构值（str(self.settings.arch)），与主 conanfile.py 保持一致。
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        elif self.settings.os == "Linux":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: skip runtime test")
            return
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_expected_lite_harmonyos"), env="conanrun")
