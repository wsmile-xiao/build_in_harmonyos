#!/usr/bin/env python3
"""Conan test_package for gdnsd 3.8.2.

Verifies that the gdnsd binary is installed and reports the correct version.
R34: test must actually exercise the packaged binary.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GdnsdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # VirtualRunEnv puts the package's bindirs (bin/, sbin/) on PATH so the
    # test program's popen("gdnsd --version") can find the packaged binary,
    # and exports LD_LIBRARY_PATH for its shared-library dependencies.
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
        # Run the test binary which calls gdnsd --version
        bin_path = os.path.join(self.cpp.build.bindir, "test_gdnsd")
        self.run(f'"{bin_path}"', env="conanrun")
