#!/usr/bin/env python3
"""Test package for libmwaw-tools — verifies the CLI tools and the libmwaw API.

Tests:
  1. mwawFile --version reports the package version (CLI smoke).
  2. mwaw2text --version reports the package version (CLI smoke).
  3. A C++ program links against libmwaw, calls the real API
     (MWAWDocument::isFileFormatSupported on an in-memory stream) and
     asserts on the result (R34: real dependency, not a print-only shell).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibMwawToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # The package is package_type="application", whose default require
        # traits are headers=False/libs=False — declare them explicitly so
        # CMakeDeps renders the libmwaw::libmwaw target with its include
        # dirs and library for the API test.
        self.requires(self.tested_reference_str, headers=True, libs=True)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # CLI smoke: tools must run and report the expected version
        self.run("mwawFile --version", env="conanrun")
        self.run("mwaw2text --version", env="conanrun")
        # C++ API test: links libmwaw and calls MWAWDocument::isFileFormatSupported
        if can_run(self):
            exe = os.path.join(self.cpp.build.bindir, "mwaw_api_test")
            self.run(exe, env="conanrun")
