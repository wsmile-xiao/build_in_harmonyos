#!/usr/bin/env python3
"""Conan test_package — debugbreak 1.0 consumer test.

Builds test.c with CMake and runs it via ctest. On OHOS,
/system/bin/sh (mksh) cannot execute ELF binaries directly, so ctest is
launched through the build-environment bash (CONFIG_SHELL), same pattern
as ableton-link.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class DebugbreakTestConan(ConanFile):
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
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'{bash} -c "ctest --output-on-failure"', env="conanrun")
