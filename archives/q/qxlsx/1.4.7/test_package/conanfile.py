#!/usr/bin/env python3
"""Conan test_package for QXlsx 1.4.7 — L1 test.

Verifies that the QXlsx library can be linked and basic Excel operations work:
  - Create a document
  - Write cells (string, number, float)
  - Apply formatting
  - Save to xlsx file
  - Load and read back

File location: archives/q/QXlsx/1.4.7/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class QXlsxTestConan(ConanFile):
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
        # Set TMPDIR for the test binary (E002: /tmp is read-only on OpenHarmony)
        import os
        os.environ["TMPDIR"] = os.environ.get("TMPDIR", "/storage/Users/currentUser")
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_QXlsx")
        self.run(cmd, env="conanrun")
