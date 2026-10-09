#!/usr/bin/env python3
"""test_package for openal/1.24.1 (OpenAL Soft).

Builds and runs:
  * upstream_basic      — dependency-free port of the upstream
                          tests/example.t.cpp "ExampleTest.Basic" case.
  * test_openal_consumer — end-to-end consumer: null backend device/context/
                          buffer/source workflow plus ALC_SOFT_loopback
                          rendering of a 220 Hz tone.
"""
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class OpenalTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        if not can_run(self):
            return
        bindir = self.cpp.build.bindirs[0]
        # Upstream compilation case (ported from tests/example.t.cpp).
        self.run(f"{bindir}/upstream_basic")
        # Consumer workflow: null backend + loopback rendering assertions.
        self.run(f"{bindir}/test_openal_consumer")
