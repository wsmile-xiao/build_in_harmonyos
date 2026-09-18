#!/usr/bin/env python3
"""test_package for tinydir 1.2.4 (header-only C library).

消费者测试使用 HarmonyOS 专项测试 test_tinydir_harmonyos.c：
覆盖 OHOS aarch64 平台断言 + tinydir 公开 API（open/readfile/next/close/
open_sorted/readfile_n/open_subdir_n/file_open/扩展名提取）的消费者视角验证。
"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building


class TinydirTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS 的 Conan arch=armv8 不能直接作为 CMAKE_SYSTEM_PROCESSOR，
        # 需映射为 aarch64；Linux 保留实际架构值。
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_tinydir_harmonyos"),
                 env="conanrun")
