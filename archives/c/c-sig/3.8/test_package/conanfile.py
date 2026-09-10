#!/usr/bin/env python3
"""Conan consumer test for c-sig 3.8 (libsigc++ 3.8.0) — signals/slots."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class CSigTestConan(ConanFile):
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
        if can_run(self):
            bindir = self.cpp.build.bindir
            for exe in ("test_c_sig", "test_c_sig_observer"):
                self.run(os.path.join(bindir, exe), env="conanrun")
        else:
            self.output.info("cross-building: compile-only consumer test")
