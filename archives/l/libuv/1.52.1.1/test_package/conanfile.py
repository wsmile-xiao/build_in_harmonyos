#!/usr/bin/env python3
"""Conan test_package — libuv 1.52.1

R34: 实质依赖被测包 API（调用 uv_version_string / uv_default_loop / uv_timer_init）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class LibuvTestConan(ConanFile):
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
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        cmake = CMake(self)
        cmake.test()
        self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_libuv')}", env="conanrun")
