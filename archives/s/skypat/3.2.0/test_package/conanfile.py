#!/usr/bin/env python3
"""Conan test_package for skypat — consumer-perspective L1 test.

CI runs this via `conan create` (which invokes test_package).  The test program
links against the packaged library, registers skypat test cases, runs them and
verifies the framework API and the PERFORM() runtime behavior (including the
graceful degradation when perf_event_open is denied by the kernel).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class SkypatTestConan(ConanFile):
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
        executable = os.path.join(self.cpp.build.bindirs[0], "test_skypat")
        self.run(executable, env="conanrun")
