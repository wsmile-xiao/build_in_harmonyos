#!/usr/bin/env python3
"""Conan recipe for coordgenlibs 3.0.2 — CMake project.

Upstream: https://github.com/schrodinger/coordgenlibs (v3.0.2)
Build: CMake; library target `coordgen` (shared or static, controlled by
COORDGEN_BUILD_SHARED_LIBS). OHOS adaptation:
  - COORDGEN_RIGOROUS_BUILD=OFF: upstream default -Wall -Wextra -Werror
    conflicts with clang/libc++ headers (-Wsign-compare on unsigned vs int
    in boost test assertions) under the OHOS toolchain.
  - Upstream tests/example require maeparser + Boost; they are NOT required
    to build/install the library itself, so they are disabled in the recipe
    (tested separately, see notes.md ledger).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class CoordgenlibsConan(ConanFile):
    name = "coordgenlibs"
    version = "3.0.2"
    description = "2D coordinate generation for small molecules (Schrodinger)"
    license = "MIT"
    homepage = "https://github.com/schrodinger/coordgenlibs"
    url = "https://github.com/schrodinger/coordgenlibs"

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
        # Upstream CMakeLists.txt declares cmake_minimum_required(VERSION 3.2);
        # CMake >= 3.5 removed compatibility with < 3.5, so pin the policy floor.
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Library-only build: upstream tests/example need maeparser + Boost,
        # which are not dependencies of the library itself.
        tc.variables["COORDGEN_BUILD_TESTS"] = "OFF"
        tc.variables["COORDGEN_BUILD_EXAMPLE"] = "OFF"
        tc.variables["COORDGEN_RIGOROUS_BUILD"] = "OFF"
        tc.variables["COORDGEN_BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["COORDGEN_USE_MAEPARSER"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMAKE_POLICY_VERSION_MINIMUM must be visible when the top-level
        # cmake_minimum_required(VERSION 3.2) is evaluated, i.e. it must be a
        # command-line -D, not a toolchain-file set (toolchain loads later).
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["coordgen"]
        self.cpp_info.includedirs = ["include"]
