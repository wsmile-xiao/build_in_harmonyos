#!/usr/bin/env python3
"""Consumer test for the installed Artistic Style library."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class AStyleTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    exports_sources = "CMakeLists.txt", "test.cpp"
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
            self.output.info("Skipping runtime test while cross-building")
            return
        executable = os.path.join(self.cpp.build.bindirs[0], "astyle_consumer")
        self.run(executable, env="conanrun")
