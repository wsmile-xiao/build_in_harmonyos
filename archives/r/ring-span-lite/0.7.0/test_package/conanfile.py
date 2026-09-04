#!/usr/bin/env python3
"""Conan test_package — ring-span-lite 0.7.0 (header-only) consumer test.

真实调用被测包 API（R34）：test_ring_span_lite.cpp 使用 nonstd::ring_span /
nonstd::ring 构造、capacity/size/full、push_back/pop_front、迭代器与数据自有
ring，非空壳 print 测试。CI 通过 conan create 自动执行。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building


class RingSpanLiteTestConan(ConanFile):
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_ring_span_lite"), env="conanrun")