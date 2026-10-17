#!/usr/bin/env python3
"""Conan test_package — sciplot 0.3.1 (C++ header-only).

消费者视角验证: find_package(sciplot) + 链接 sciplot::sciplot 并实际运行，
调用公开 API (Plot2D::drawCurve / Canvas::save / saveplotdata) 校验输出产物。
"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building


class SciplotTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self, build_folder="$TMP")

    def generate(self):
        tc = CMakeToolchain(self)
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
        # L0d: test() 内实际运行消费者二进制（非空壳）
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_sciplot"), env="conanrun")
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_ohos_special"), env="conanrun")
