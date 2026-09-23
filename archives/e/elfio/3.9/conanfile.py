#!/usr/bin/env python3
"""Conan recipe for ELFIO 3.9 — a C++ header-only library for reading/writing ELF files.

ELFIO is a header-only library (no compiled library artifacts). It uses CMake
as its build system and installs only header files plus CMake config files.
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class ElfioConan(ConanFile):
    name = "elfio"
    version = "3.9"
    description = "ELFIO is a C++ header-only library for reading and writing ELF files"
    license = "MIT"
    homepage = "https://github.com/serge1/ELFIO"

    # Header-only library: no binary artifact, no shared/static distinction
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ELFIO_BUILD_EXAMPLES"] = False
        tc.variables["ELFIO_BUILD_TESTS"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Copy license — ELFIO 3.9 tarball ships COPYING (no LICENSE.txt)
        for lic in ("COPYING", "LICENSE.txt"):
            copy(self, lic, src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Header-only: no libs, but set includedirs so consumers get headers
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
