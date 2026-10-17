#!/usr/bin/env python3
"""Conan test_package for libpfm 4.13.0.

Consumer-side L1 test: compiles a real consumer against the packaged
libpfm and runs it on the target. Uses the public pfm_* API from
<perfmon/pfmlib.h> — no empty-shell test (R34).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibpfmTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.build()
        # run the real consumer binaries (L0d requires self.run execution)
        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "test_libpfm"), env="conanrun")
        self.run(os.path.join(bindir, "test_libpfm_harmonyos"), env="conanrun")
