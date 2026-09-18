#!/usr/bin/env python3
"""Conan test_package — bcc 0.37.0 (Conan L1 official test).

Runs a consumer binary that links libbcc and calls its public C API.
Uses VirtualRunEnv so LD_LIBRARY_PATH points at the packaged libbcc.so
(libbcc.so.0 has DT_SONAME, so the loader must find the package lib dir).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BccTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_bcc")
        # VirtualRunEnv injects dependency runtimes, but not the tested
        # package's own lib dir; add it so libbcc.so.0 (DT_SONAME) loads.
        pkg_lib = os.path.join(
            self.dependencies["bcc"].package_folder, "lib")
        self.run(
            f'export LD_LIBRARY_PATH="{pkg_lib}:$LD_LIBRARY_PATH" && "{test_bin}"',
            env="conanrun", cwd=self.build_folder)
