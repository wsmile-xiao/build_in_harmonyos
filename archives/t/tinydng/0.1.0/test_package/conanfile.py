#!/usr/bin/env python3
"""Test package for tinydng 0.1.0 (header-only DNG loader/writer).

消费者测试：用 tinydngwriter 写一张已知像素的 DNG，再用 tinydng loader
读回，断言尺寸/位深/采样格式与像素字节逐位一致。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building


class TinydngTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: skip runtime test")
            return
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_tinydng"), env="conanrun")
