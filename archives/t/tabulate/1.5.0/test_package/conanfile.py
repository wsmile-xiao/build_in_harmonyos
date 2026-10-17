#!/usr/bin/env python3
"""Conan test_package — tabulate 1.5.0 (header-only CMake consumer test).

The consumer test (test.cpp) is the HarmonyOS-specific test: it includes
<tabulate/table.hpp>, builds a Table, applies column formatting and dumps
Markdown via MarkdownExporter, asserting the rendered output contains the
expected headers/cells/table separators. Exit code 0 = all assertions passed.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TabulateTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # L0d gate requires an explicit self.run() in test(). Build the test
        # binary (above) then execute it under the conanrun environment.
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_tabulate"),
                 env="conanrun")