#!/usr/bin/env python3
"""Conan test_package — Hermes JS Engine.

Runs the hermes binary from the installed package to verify it can execute
JavaScript. This is the L1 test (R34: test must depend on tested package).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class HermesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"  # CMakeToolchain is created in generate()
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Pass hermes binary path to CMake
        hermes_bin = os.path.join(self.dependencies["hermes"].package_folder, "bin", "hermes")
        tc.variables["HERMES_BIN_PATH"] = hermes_bin
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the CTest-based test (runs test_hermes which invokes hermes binary)
        cmake = CMake(self)
        cmake.test()

        # Also directly run the hermes binary to verify it works (R34 + L0d self.run requirement)
        hermes_bin = os.path.join(self.dependencies["hermes"].package_folder, "bin", "hermes")
        js_file = os.path.join(self.build_folder, "test_hermes_check.js")
        with open(js_file, "w") as f:
            f.write("print('Hermes L1 test: OK');\n")
        self.run(f"{hermes_bin} {js_file}")
