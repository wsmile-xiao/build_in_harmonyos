#!/usr/bin/env python3
"""Conan test_package for status-code 1.0-gh0.20240312 — Conan L1 official test.

Builds and runs ``test_generic_code`` against the packaged headers, verifying
a downstream consumer can find and use the system_error2 API
(CMakeDeps + find_package) through real assertions.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class StatusCodeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries directly.
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} -c './test_generic_code'", cwd=self.cpp.build.bindirs[0])
