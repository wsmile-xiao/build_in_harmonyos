#!/usr/bin/env python3
"""Conan test_package — libppd 2.1.1.

Verifies that libppd can be found via pkg-config and that a
test program linking against libppd compiles and runs.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibppdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "build"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # ppd.h include <cups/raster.h>，需显式声明传递依赖
        # 让 CMakeDeps 生成 cups/libcupsfilters 的 target
        self.requires("cups/2.4.19")
        self.requires("libcupsfilters/2.2.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 显式 self.run() 执行测试二进制（L0d 门禁要求）
        self.run(os.path.join(self.cpp.build.bindir, "test_libppd"), env="conanrun")
