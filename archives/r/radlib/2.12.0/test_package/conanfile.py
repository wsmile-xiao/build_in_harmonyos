#!/usr/bin/env python3
"""Conan test_package - radlib consumer test (L1).

Builds a real consumer program against the packaged library (public
headers h/*.h + static radlib) and runs it. The program exercises the
exported SHA-1/SHA-256 API against FIPS test vectors and asserts the
results; its exit code decides the test result (R34: no print-only stub).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class RadlibTestConan(ConanFile):
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
        # radlib is consumed as a static library here (default shared=False),
        # so no runtime library search path is needed.
        self.run("ctest --output-on-failure", cwd=self.build_folder, env="conanbuild")
