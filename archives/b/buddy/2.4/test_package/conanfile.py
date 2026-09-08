#!/usr/bin/env python3
"""Consumer-side API test for buddy 2.4 (BuDDy BDD package).

Builds a real Conan consumer against the packaged headers and library, then
runs it.  The consumer exercises the C core (bdd_*), the C++ wrapper classes
(bdd), the finite-domain extensions (fdd_*) and bit-vector arithmetic
(bvec_*), so both the packaged headers and the linked library are verified.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class BuddyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross build: buddy consumer was built; run it on the "
                "HarmonyOS PC target."
            )
            return
        executable = os.path.join(self.cpp.build.bindirs[0], "test_buddy")
        self.run(executable, env="conanrun")
