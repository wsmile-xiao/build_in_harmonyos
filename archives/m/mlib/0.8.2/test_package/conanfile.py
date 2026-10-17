#!/usr/bin/env python3
"""Conan test_package for mlib 0.8.2 — Conan L1 official test.

Builds and runs ``test_mlib`` against the packaged headers, verifying a
downstream consumer can find and use mlib's generic container APIs
(CMakeDeps + find_package) through real workloads.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class MlibTestConan(ConanFile):
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
        # Use bash to wrap binary execution where available.
        bash = os.environ.get("CONFIG_SHELL", "bash")
        self.run(f"{bash} -c './test_mlib'", cwd=self.cpp.build.bindirs[0])
