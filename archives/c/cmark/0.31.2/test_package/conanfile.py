#!/usr/bin/env python3
"""Conan test_package — cmark L1 official test."""

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class CmarkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

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
            self.output.info("cross-building：跳过目标架构二进制运行")
            return
        # 直接运行可执行文件，避免 OHOS 上 /bin/bash 不存在导致的执行失败
        self.run("./test_cmark", env="conanrun")
