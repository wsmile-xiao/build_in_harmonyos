#!/usr/bin/env python3
"""Consumer test for the packaged hamlib library.

Builds test.c against the installed libhamlib and runs it (CMake/CTest):
the binary asserts the library version, enumerates the compiled-in backend
rig models through the public API, drives the dummy rig through a full
init/open/set_freq/get_freq/close/cleanup round-trip and checks the
mode parsing helpers.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class HamlibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
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
        # Official CTest entry point (single registered test).
        cmake = CMake(self)
        cmake.test()
        # R34: also invoke the assertion binary directly so the individual
        # PASS/FAIL lines of test.c are part of the conan test log.
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_hamlib"),
            env="conanrun",
        )
