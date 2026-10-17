#!/usr/bin/env python3
"""Test package for cbp2make 147 (Code::Blocks to makefile converter, CLI tool)"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Cbp2makeTestConan(ConanFile):
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
        driver = os.path.join(self.cpp.build.bindirs[0], "test_consumer")
        cbp2make_bin = os.path.join(
            self.dependencies["cbp2make"].cpp_info.bindirs[0], "cbp2make")
        # 生成的 Makefile 硬编码 gcc，需以 profile 编译器显式覆盖
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = (compilers or {}).get("c", "cc")
        self.run('"%s" "%s" "%s"' % (driver, cbp2make_bin, cc), env="conanrun")
