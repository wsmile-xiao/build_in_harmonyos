#!/usr/bin/env python3
"""Conan test_package — consumer test for greg7mdp-gtl 1.2.0 (header-only).

Builds a downstream-style consumer that pulls the packaged headers through
`find_package(gtl)` only, then exercises the public API for real and asserts
on the returned values (R34: no stubs, no print-only checks).  `test()`
executes the binary.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class GtlTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            executable = os.path.join(self.cpp.build.bindir, "test_gtl")
            self.run(executable, env="conanrun")
        else:
            self.output.info(
                "Cross-building: test_package execution is covered by the HDC device test")
