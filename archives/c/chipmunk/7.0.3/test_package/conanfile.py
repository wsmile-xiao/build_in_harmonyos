#!/usr/bin/env python3
"""Consumer test for chipmunk/7.0.3.

Builds the C++ consumer against the installed package and runs it
directly (the verdict is taken from the executable's exit code; ctest
registration stays for interactive use).
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.cmake import CMake, cmake_layout


class ChipmunkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # Neutralize ambient LD_LIBRARY_PATH (some CI workers point it at
        # a /usr/local/lib whose incompatible libxml2.so.16 breaks the
        # SDK's lld on every link — CI-021 build #48068).
        environment = Environment()
        environment.define("LD_LIBRARY_PATH", "")
        with environment.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        exe = os.path.join(self.cpp.build.bindir, "test_chipmunk")
        self.run(f'"{exe}"', env="conanrun")
