#!/usr/bin/env python3
"""Conan test_package for snappy 1.1.7 — Conan L1 consumer test.

Compresses and decompresses a string using the snappy C API, verifying
the library works end to end.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.build import can_run


class SnappyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # OHOS hmmac blocks /bin/sh (E346): use Ninja to bypass the shell.
        self.conf.define("tools.cmake.cmaketoolchain:generator", "Ninja")
        cmake_deps = CMakeDeps(self)
        cmake_deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_MAKE_PROGRAM"] = "/data/service/hnp/bin/ninja"
        tc.generate()

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_snappy")
            self.run(bin_path, env="conanrun")
