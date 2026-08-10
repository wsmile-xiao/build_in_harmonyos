#!/usr/bin/env python3
"""Conan recipe for libatomic_ops 7.8.2.

libatomic_ops provides atomic memory operation interfaces, portable across
multiple platforms.  It builds two static libraries: atomic_ops (core) and
atomic_ops_gpl (stack + malloc, GPL-2.0).

Build system: CMake.
No external dependencies (only needs system pthreads).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibatomicopsConan(ConanFile):
    name = "libatomic_ops"
    version = "7.8.2"
    description = "Atomic memory access operations library"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ivmai/libatomic_ops"
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
        tc.variables["build_tests"] = "OFF"
        tc.variables["enable_docs"] = "OFF"
        tc.variables["enable_gpl"] = "ON"
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
        self.cpp_info.libs = ["atomic_ops", "atomic_ops_gpl"]
