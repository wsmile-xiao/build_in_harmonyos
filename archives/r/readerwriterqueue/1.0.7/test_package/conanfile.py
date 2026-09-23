#!/usr/bin/env python3
"""Conan test_package — readerwriterqueue 1.0.7 (消费者验证)

E225: 使用 cmake_layout(build_folder="$TMP") 让 Conan 管理每次调用唯一临时构建根，
并在 generate() 关闭 user_presets_path，阻止 CMakeToolchain 向 source 写入
CMakeUserPresets.json（零 source 生成物，标准 conan create 可直接运行）。
"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ReaderwriterqueueTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self, build_folder="$TMP")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.user_presets_path = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Alternatively, run the binary directly:
        # self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_readerwriterqueue')}", env="conanrun")
