#!/usr/bin/env python3
"""Conan recipe for brunsli v0.1 — JPEG Brunsli compression codec.

brunsli embeds brotli v1.0.7 and googletest as git submodules.
Since GitHub release tarballs do not include submodule content,
they are downloaded separately in source().
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BrunsliConan(ConanFile):
    name = "brunsli"
    version = "v0.1"
    description = "JPEG Brunsli compression codec (Brotli-based JPEG recompression)"
    license = "MIT"
    homepage = "https://github.com/google/brunsli"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Use custom build folder to avoid conflict with Bazel BUILD file
        # (case-insensitive filesystem treats BUILD and build as same)
        cmake_layout(self, build_folder="cmake-build")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Download brotli v1.0.7 submodule (required by brunsli, not in GitHub tarball)
        get(self, **self.conan_data["brotli"], strip_root=True,
            destination=os.path.join(self.source_folder, "third_party", "brotli"))
        # Download googletest release-1.10.0 submodule (for brunsli test infrastructure)
        get(self, **self.conan_data["googletest"], strip_root=True,
            destination=os.path.join(self.source_folder, "third_party", "googletest"))

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMAKE_POLICY_VERSION_MINIMUM must be a -D argument, not in toolchain file,
        # because cmake_minimum_required() runs before the toolchain is loaded
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream install only installs shared libs and headers;
        # manually copy executables and static libraries
        copy(self, "cbrunsli", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "dbrunsli", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        # brunsli static libs are in build root; brotli static libs are in third_party/brotli/
        # use keep_path=False to flatten all .a files into lib/
        copy(self, "*brunsli*static*.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*brotli*static*.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # brunsli always builds both shared (.so) and static (.a) libraries.
        # C API wrappers (DecodeBrunsli, EncodeBrunsli) are only in the shared
        # libs (brunslidec-c, brunslienc-c); C++ implementation is in static libs.
        # Include both so consumers can use the C API regardless of shared option.
        if self.options.shared:
            self.cpp_info.libs = ["brunslienc-c", "brunslidec-c"]
        else:
            self.cpp_info.libs = [
                "brunslienc-static", "brunslidec-static", "brunslicommon-static",
                "brotlienc-static", "brotlidec-static", "brotlicommon-static",
                "brunslienc-c", "brunslidec-c",
            ]
