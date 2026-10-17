#!/usr/bin/env python3
"""Conan consumer test for the installed unqlite package (CMake)."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class UnqliteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self, build_folder="$TMP")

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        toolchain.user_presets_path = False
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 消费者用例：内存库 KV + Jx9 文档存储（12 项断言）
        self.run(os.path.join(self.cpp.build.bindir, "test_unqlite"),
                 env="conanrun")
        # HarmonyOS 专项测试：磁盘文件持久化语义（12 项断言）
        self.run(os.path.join(self.cpp.build.bindir, "test_unqlite_ohos"),
                 env="conanrun")