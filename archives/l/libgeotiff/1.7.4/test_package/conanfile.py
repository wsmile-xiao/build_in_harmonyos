#!/usr/bin/env python3
"""Conan test_package — libgeotiff L1 functional test.

Tests that libgeotiff's core API (GTIFNew, GTIFKeySet, GTIFWriteKeys,
GTIFKeyGet, GTIFFree) works correctly by creating and reading a GeoTIFF file.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class LibgeotiffTestConan(ConanFile):
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
        if cross_building(self):
            self.output.info("cross-building: only checking compile+link")
            return
        self.run("ctest --output-on-failure", env="conanrun")
