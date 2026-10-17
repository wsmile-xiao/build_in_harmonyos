#!/usr/bin/env python3
"""Conan test_package for icu/76.1 — L1 consumer test.

Builds and runs a C consumer that calls the ICU C API (ucol_strcoll,
ucal_get, u_getVersion) with real assertions, proving the packaged
static libraries (icuuc/icui18n/icudata) are complete and linkable.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class IcuTestConan(ConanFile):
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
        # Run the consumer binary directly. env="" avoids sourcing the
        # conanbuild/conanrun aggregated scripts (on OHOS a broken /bin/sh
        # environment can SIGSEGV the wrapper — E064); the binary is fully
        # statically linked, so no PATH/LD_LIBRARY_PATH is needed.
        test_bin = os.path.join(self.cpp.build.bindir, "test_icu")
        self.run(f"chmod +x {test_bin} 2>/dev/null; {test_bin}", env="")
