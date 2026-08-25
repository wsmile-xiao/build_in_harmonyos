#!/usr/bin/env python3
"""Conan recipe — libsquish 1.15 (CMake)

libsquish is an open-source DXT/S3TC texture compression library.

A portability patch raises ``cmake_minimum_required`` from 2.8.3 to 3.5 so the
project configures under CMake 4.x (which dropped compatibility with
cmake_minimum_required < 3.5).

For OpenHarmony aarch64 (ARM), the x86-only SSE2 and Altivec SIMD back-ends
are disabled at CMake configure time (``BUILD_SQUISH_WITH_SSE2=OFF`` etc.);
the library falls back to the portable scalar implementation in
``simd_float.h``.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class LibsquishConan(ConanFile):
    name = "libsquish"
    version = "1.15"
    description = "Open source DXT/S3TC compression library"
    license = "MIT"
    homepage = "https://sourceforge.net/projects/libsquish/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # The upstream SourceForge tarball is a flat archive (files in the
        # archive root with no single top-level directory), so strip_root is
        # not used — get() extracts the files straight into the source folder.
        get(self, **self.conan_data["sources"])
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # ARM / OpenHarmony aarch64 target: disable x86-only SSE2 and the
        # PowerPC-only Altivec back-end, and disable the optional OpenMP
        # parallelism (avoids a libomp dependency).  The library falls back
        # to the portable scalar implementation (simd_float.h).
        tc.variables["BUILD_SQUISH_WITH_SSE2"] = False
        tc.variables["BUILD_SQUISH_WITH_ALTIVEC"] = False
        tc.variables["BUILD_SQUISH_WITH_OPENMP"] = False
        tc.variables["BUILD_SQUISH_EXTRA"] = False
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["squish"]
