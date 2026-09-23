#!/usr/bin/env python3
"""Test package for easyflash 4.1.0 — consumer-side runtime verification.

Builds test.c + ef_port_ram.c against the installed libeasyflash and runs
the resulting binary, exercising the public ENV (key-value) API on OHOS.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class EasyflashTestConan(ConanFile):
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
            self.output.info("cross-building: skip runtime test")
            return
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_easyflash"), env="conanrun")
        self.run(os.path.join(self.cpp.build.bindirs[0], "ohos_env_test"), env="conanrun")
