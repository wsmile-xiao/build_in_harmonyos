#!/usr/bin/env python3
"""Conan recipe — dsdcc 1.9.6 (CMake project, library + dsdccx CLI tool).

dsdcc (Digital Speech Decoder C++ library) by f4exb.
Optional upstream deps: mbelib (USE_MBELIB), serialdv (SerialDV) —
not enabled in this adaptation (self-contained default build).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class DsdccConan(ConanFile):
    name = "dsdcc"
    version = "1.9.6"
    description = "Digital Speech Decoder (DSD) C++ library for P25/DMR/D-Star/YSF/NXDN decoding"
    license = "MIT"
    homepage = "https://github.com/f4exb/dsdcc"
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
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TOOL"] = "ON"
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
        self.cpp_info.libs = ["dsdcc"]
        # headers installed to include/dsdcc/ by upstream CMake;
        # keep default include/ root so consumers use <dsdcc/dsd_decoder.h>
        self.cpp_info.bindirs = ["bin"]
