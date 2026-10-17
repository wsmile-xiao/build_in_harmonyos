#!/usr/bin/env python3
"""Installed-package consumer tests for libnoise 1.0.0.

Builds and runs one program that links against the packaged library and
exercises the public API contract:

* deterministic, finite, coherent coherent-noise sampling (Perlin),
* parameter setters honoured by the configured generator,
* the Billow and RidgedMulti multifractal generators,
* module graph wiring through ScaleBias (exact scale*bias arithmetic),
* the documented ExceptionNoModule contract of unconnected source modules,
* the Sphere/Cylinder/Plane/Line model layer, and
* the LatLonToXYZ geographic helper.

Upstream 1.0.0 ships no test suite, so these checks are the verification for
the package - see test_package/MANIFEST.yml and ../notes.md.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


TEST_EXECUTABLES = ("test_libnoise",)


class LibnoiseTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.cpp"

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
                "libnoise consumer binaries cannot run on this platform"
            )
        for name in TEST_EXECUTABLES:
            executable = os.path.join(self.cpp.build.bindir, name)
            self.run(f'"{executable}"', env="conanrun")
