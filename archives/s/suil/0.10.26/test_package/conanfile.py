#!/usr/bin/env python3
"""Conan test_package for suil/0.10.26."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SuilTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def requirements(self):
        # suil.h 递归 #include <lv2/core/lv2.h>（上游公共头契约），
        # 消费者构建需同时可见 lv2 头文件；suil-0 的 CMakeDeps target
        # 已链 lv2，但 include 路径需 lv2 包自身提供。
        self.requires(self.tested_reference_str)
        self.requires("lv2/1.18.11-git")

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
        if can_run(self):
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_suil"), env="conanrun")
        else:
            self.output.info("cross-building: skip runtime test")
