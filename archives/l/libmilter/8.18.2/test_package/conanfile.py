#!/usr/bin/env python3
"""Test package for libmilter — CMake + CTest validation of the milter filter API."""
from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibmilterTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

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
        if cross_building(self):
            self.output.info("cross-building: compile+link validation only")
            return
        # Native OHOS build: run the API smoke test on-device.
        # TMPDIR must point at the sandbox tmp (unix socket bind is only
        # permitted there; /tmp is read-only, user dirs give EPERM).
        self.run("./test_milter", env=["TMPDIR"])
