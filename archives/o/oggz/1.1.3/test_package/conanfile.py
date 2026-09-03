#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/oggz/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class OggzTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # oggz.h pulls in <ogg/ogg.h>; the libogg recipe (cmake_layout) does not
        # advertise include dirs to CMakeDeps, so hand the folder to CMake.
        tc = CMakeToolchain(self)
        ogg = self.dependencies["libogg"]
        if ogg.package_folder:
            tc.variables["LIBOGG_INCLUDE_DIR"] = os.path.join(
                ogg.package_folder, "include"
            )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Alternatively, run the binary directly:
        # self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_oggz')}", env="conanrun")
