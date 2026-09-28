#!/usr/bin/env python3
"""Conan recipe — kdbindings 1.1.0 (header-only C++17 reactive data binding library).

KDBindings is a header-only INTERFACE library (KDAB, MIT). Nothing is compiled:
the public headers under src/kdbindings plus the generated kdbindings_version.h
and the KDBindings CMake package config are installed.

R32 note: no settings.os branch is needed — the OHOS-adapted conan maps
os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS via CMakeToolchain.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KdbindingsConan(ConanFile):
    name = "kdbindings"
    version = "1.1.0"
    description = "KDBindings - reactive data binding and property system for C++17 (header-only)"
    license = "MIT"
    homepage = "https://github.com/KDAB/KDBindings"
    url = "https://github.com/KDAB/KDBindings"  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # header-only, no runtime dependencies
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Header-only library: tests/examples are not part of the installed recipe
        tc.variables["KDBindings_TESTS"] = "OFF"
        tc.variables["KDBindings_EXAMPLES"] = "OFF"
        tc.variables["KDBindings_DOCS"] = "OFF"
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
        # header-only: no libraries to link, headers + CMake config installed
        self.cpp_info.set_property("cmake_file_name", "KDBindings")
        self.cpp_info.set_property("cmake_target_name", "KDAB::KDBindings")
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []