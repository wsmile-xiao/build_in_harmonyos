#!/usr/bin/env python3
"""Conan recipe for libccp4 8.0.0 — CCP4 core C library (cmake build)."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class Libccp4Conan(ConanFile):
    name = "libccp4"
    version = "8.0.0"
    description = "CCP4 core C library (ccp4c): crystallographic computing library used by PDB-REDO"
    license = "LGPL-3.0"
    homepage = "https://gitlab.com/CCP4/libccp4"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("ccp4", "crystallography", "xray", "ccp4c")

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS PC has no Fortran compiler and mmdb2 is not published yet.
        # ccp4f (Fortran library) is not required by downstream C/C++ consumers
        # (libpdb-redo only links ccp4c), so disable it (option FORTRAN_LIB).
        tc.variables["FORTRAN_LIB"] = "OFF"
        # OHOS has no Platform/HarmonyOS.cmake, so CMake cannot derive the
        # shared-library SONAME flag; without it the built .so has no DT_SONAME
        # and the L5 soname gate fails (knowledge E383).
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["ccp4c"]

        # Upstream installs its own ccp4-config.cmake (a find-module for
        # find_package(CCP4 COMPONENTS ...)). Expose it so downstream
        # (e.g. libpdb-redo / clipper) can locate it via builddirs.
        self.cpp_info.builddirs = ["lib/cmake/ccp4"]

        # pkg-config metadata (ccp4c.pc) is installed under lib/pkgconfig.
        self.cpp_info.set_property("pkg_config_name", "ccp4c")
