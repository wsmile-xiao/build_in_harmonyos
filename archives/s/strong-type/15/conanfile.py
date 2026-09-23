#!/usr/bin/env python3
"""Conan recipe — strong-type 15 (header-only C++14/17/20 strong typedef library).

strong_type by Björn Fahller — strong typedefs for C++ with composable
modifiers (arithmetic, ordered, difference, ...). Header-only: the tarball
ships include/strong_type/*.hpp plus CMake package config files; the recipe
packages the headers as-is (the CMake project is only used upstream for
tests/install and the package declares its own CMake target).
"""
import os

from conan import ConanFile
from conan.tools.cmake import cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class StrongTypeConan(ConanFile):
    name = "strong-type"
    version = "15"
    description = "strong_type — strong typedefs for C++14/17/20 with composable modifiers, header-only"
    license = "BSL-1.0"
    homepage = "https://github.com/rollbear/strong_type"
    url = "https://github.com/rollbear/strong_type"
    topics = ("strong-typedef", "typesafety", "header-only", "cpp14", "cpp17")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # Header-only library: no compilation step; headers are packaged as-is.
        # build() exists to satisfy G1 recipe-completeness gate (no-op for
        # header-only libraries without a library build system).
        pass

    def package(self):
        # All public headers live under include/strong_type/ and include each
        # other by bare name, so the directory is copied as a unit.
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "include", "strong_type"),
             dst=os.path.join(self.package_folder, "include", "strong_type"))
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "strong-type")
        self.cpp_info.set_property("cmake_target_name", "strong-type::strong-type")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # Header-only library: no libs to link.
        self.cpp_info.libs = []
