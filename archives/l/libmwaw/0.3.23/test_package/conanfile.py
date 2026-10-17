#!/usr/bin/env python3
"""Test package for libmwaw — exercises the library API.

A C++ program links against libmwaw, calls the real API
(MWAWDocument::isFileFormatSupported on in-memory streams) and asserts on
the result (R34: real dependency, not a print-only shell).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibMwawTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libmwaw headers include librevenge headers and the static libmwaw
        # references librevenge symbols: declare it directly so CMakeDeps
        # renders usable include dirs/libs through the tested_reference chain
        # (transitive cpp_info is dropped there; precedent cpr/1.12.0).
        self.requires("librevenge/0.0.5")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # C++ API test: links libmwaw and calls
        # MWAWDocument::isFileFormatSupported on in-memory streams.
        if can_run(self):
            exe = os.path.join(self.cpp.build.bindir, "mwaw_api_test")
            self.run(exe, env="conanrun")
