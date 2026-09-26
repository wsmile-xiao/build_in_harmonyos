#!/usr/bin/env python3
"""Conan test_package — consumer test for boolinq 3.0.4 (header-only).

Builds a downstream-style consumer that includes <boolinq/boolinq.h> through
the packaged include dir and exercises the public API; test() executes the
binary for real (R34).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class BoolinqTestPackageConan(ConanFile):
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
            executable = os.path.join(self.cpp.build.bindir, "test_boolinq")
            self.run(executable, env="conanrun")
        else:
            self.output.info(
                "Cross-building: test_package execution is covered by the HDC device test"
            )
