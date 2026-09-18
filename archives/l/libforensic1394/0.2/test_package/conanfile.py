#!/usr/bin/env python3
"""Installed-package consumer tests for libforensic1394 0.2.

Runs two programs that link against the packaged library:

* forensic1394_api_surface   - the whole exported surface must resolve with
                               the exact header-declared signatures, and the
                               public result enum must map to the documented
                               strings.
* forensic1394_bus_lifecycle  - the bus handle lifecycle (alloc, user data,
                               device enumeration, SBP-2 enable, destroy) must
                               behave as documented without FireWire hardware.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


TEST_EXECUTABLES = ("forensic1394_api_surface", "forensic1394_bus_lifecycle")


class Libforensic1394TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException(
                "libforensic1394 consumer binaries cannot run on this platform"
            )
        for name in TEST_EXECUTABLES:
            executable = os.path.join(self.cpp.build.bindir, name)
            self.run(f'"{executable}"', env="conanrun")
