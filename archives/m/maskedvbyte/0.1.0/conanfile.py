#!/usr/bin/env python3
"""Conan recipe — MaskedVByte 0.1.0 (CMake project).

Fast vectorized VByte integer compression library (Apache-2.0 upstream).
AArch64 uses a self-contained NEON shim (include/sse_to_neon.h) that restores
the header the upstream v0.1.0 tag references but never ships.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MaskedvbyteConan(ConanFile):
    name = "maskedvbyte"
    version = "0.1.0"
    description = "maskedvbyte 0.1.0 - Fast vectorized VByte integer compression"
    license = "Apache-2.0"
    homepage = "https://github.com/lemire/MaskedVByte"
    url = "https://github.com/lemire/MaskedVByte"

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
        self.cpp_info.libs = ["maskedvbyte"]