#!/usr/bin/env python3
"""Conan test_package — tl-expected 1.1.0 (C++ header-only).

消费者视角验证: find_package(tl-expected) + 链接 tl::expected 并运行。
"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building


class TlExpectedTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # E225: 使用 Conan 2 管理的临时 test-package 布局，避免 source 生成物污染
        cmake_layout(self, build_folder="$TMP")

    def generate(self):
        tc = CMakeToolchain(self)
        # E225: 阻止 CMakeUserPresets.json 写回 test_package source
        tc.user_presets_path = False
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
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_tl_expected"), env="conanrun")