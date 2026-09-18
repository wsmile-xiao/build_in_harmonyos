#!/usr/bin/env python3
"""Conan test_package — dds2tar 2.5.2 消费者测试（CMake 构建 + popen 直读断言）。"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class Dds2TarTestConan(ConanFile):
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
        if not can_run(self):
            self.output.info("cross-building: dds2tar runtime checks deferred to OHOS runner")
            return
        pkg = self.dependencies["dds2tar"].package_folder
        bins = [os.path.join(pkg, "bin", x) for x in ("dds2tar", "dds2index", "ddstool")]
        exe = os.path.join(self.cpp.build.bindir, "test_dds2tar")
        self.run(f'"{exe}" ' + " ".join(f'"{b}"' for b in bins))
