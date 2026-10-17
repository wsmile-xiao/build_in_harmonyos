#!/usr/bin/env python3
"""Conan recipe for libmcfp 1.4.2 — header-only C++ command-line parsing library.

libmcfp is a header-only INTERFACE library (CMake: add_library(mcfp INTERFACE)).
It requires C++20 and has no external dependencies.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibmcfpConan(ConanFile):
    name = "libmcfp"
    version = "1.4.2"
    description = "A modern C++ library for command-line argument parsing"
    license = "BSD-2-Clause"
    homepage = "https://github.com/mhekkel/libmcfp"
    url = "https://github.com/mhekkel/libmcfp"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Header-only library; disable tests to avoid fetching Catch2
        tc.variables["BUILD_TESTING"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # Header-only library: only include directories matter
        self.cpp_info.includedirs = ["include"]
