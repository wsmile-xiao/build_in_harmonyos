#!/usr/bin/env python3
"""Conan recipe for metis 5.1.0 — graph partitioning library.

METIS is a set of serial programs for partitioning graphs, partitioning
finite element meshes, and computing fill-reducing orderings of sparse matrices.

R32: settings.os check uses `in ("Linux", "OHOS")`
R33: build() does not depend on undefined shell environment variables
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MetisConan(ConanFile):
    name = "metis"
    version = "5.1.0"
    description = "METIS - Serial Graph Partitioning and Fill-reducing Matrix Ordering"
    license = "Apache-2.0"
    homepage = "https://karypis.github.io/glaros/software/metis/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # metis has no runtime dependencies (R1: minimal)
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: Build static library by default (metis is not a system-name library
        # but static is the upstream default and safer for OHOS)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # CMake compatibility fix for old cmake_minimum_required(VERSION 2.8)
        # Use cache_variables so it's passed as -D on the cmake command line
        # (tc.variables goes into the toolchain file which is processed too late)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # GKLIB_PATH must be set to the absolute path of the GKlib directory
        # R33: Use self.source_folder instead of shell variable $BUILD_SRC_DIR
        tc.cache_variables["GKLIB_PATH"] = f"{self.source_folder}/GKlib"
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
        self.cpp_info.libs = ["metis"]
        # metis installs executables too (gpmetis, ndmetis, etc.)
        # These are declared in commands.json at the software-level
