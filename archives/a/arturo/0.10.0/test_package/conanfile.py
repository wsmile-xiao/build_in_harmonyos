#!/usr/bin/env python3
"""Conan test_package for Arturo 0.10.0.

R34: Test must actually execute the tested package's binary.
This test finds the arturo binary from the Conan dependency info,
passes its path to CMake as a compile definition, and the C test
program executes `arturo --version` to verify the binary works.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ArturoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        # Find the arturo binary path from Conan dependency info
        arturo_bin = ""
        arturo_dep = self.dependencies["arturo"]
        for bindir in arturo_dep.cpp_info.bindirs:
            path = os.path.join(bindir, "arturo")
            if os.path.exists(path):
                arturo_bin = path
                break
        if not arturo_bin:
            raise Exception("arturo binary not found in dependency bindirs")
        self.output.info(f"Found arturo binary at: {arturo_bin}")
        cmake.configure(variables={"ARTURO_BIN_PATH": arturo_bin})
        cmake.build()

    def test(self):
        # R34: Execute the test binary which calls arturo --version
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_arturo")
        self.run(f'"{test_bin}"', env="conanrun")
