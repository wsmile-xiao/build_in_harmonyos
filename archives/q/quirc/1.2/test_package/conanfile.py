#!/usr/bin/env python3
"""Conan test_package — quirc 1.2 (Conan L1 consumer test).

test.c feeds a fixed known QR symbol into the public quirc API and
asserts the decoded payload and metadata; exit code decides pass/fail.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class QuircTestConan(ConanFile):
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
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_quirc'", env="conanrun")
