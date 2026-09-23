#!/usr/bin/env python3
"""Conan recipe for h3 4.4.1 (CMake build)."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class H3Conan(ConanFile):
    name = "h3"
    version = "4.4.1"
    description = "H3 is a hierarchical hexagonal geospatial indexing system"
    license = "Apache-2.0"
    homepage = "https://h3geo.org"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

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
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Fuzzers require afl/libFuzzer and are not needed for packaging.
        tc.variables["BUILD_FUZZERS"] = "OFF"
        # Benchmarks are not part of the shipped library or its tests.
        tc.variables["BUILD_BENCHMARKS"] = "OFF"
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
        self.cpp_info.libs = ["h3"]
