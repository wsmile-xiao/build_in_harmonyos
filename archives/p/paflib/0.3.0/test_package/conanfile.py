#!/usr/bin/env python3
"""Conan test_package for paflib 0.3.0.

Builds and runs a C consumer that exercises the installed headers and both
static libraries: the portable Time Base and DSCR field helpers, the graceful
DSCR/PPR degradation and the EBB API contract on OHOS/aarch64.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout

CHECKS = 19


class PaflibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
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
        if can_run(self):
            exe = os.path.join(self.cpp.build.bindirs[0], "test_paflib")
            self.run('"%s"' % exe, env="conanrun")
            print("PAFLIB_CONSUMER_CHECKS=%d" % CHECKS)
