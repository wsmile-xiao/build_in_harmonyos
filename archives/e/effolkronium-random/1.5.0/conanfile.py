#!/usr/bin/env python3
"""Conan recipe for effolkronium-random 1.5.0 — header-only C++11 random utility.

effolkronium::random (random_static / random_thread_local / random_local) is a
header-only library: the whole API lives in the single public header
`effolkronium/random.hpp` (C++11, no dependencies). The upstream CMake target
is an INTERFACE library named `effolkronium_random` which only exposes the
include path; no compilation is needed for the library itself.

This recipe mirrors the upstream CMake package so consumers can use
find_package(effolkronium_random) + effolkronium_random::effolkronium_random.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class EffolkroniumRandomConan(ConanFile):
    name = "effolkronium-random"
    version = "1.5.0"
    description = "Random for modern C++ with a convenient API (header-only C++11)"
    license = "MIT"
    homepage = "https://github.com/effolkronium/random"
    url = ""  # CI fills this
    topics = ("random", "header-only", "cxx11")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        # Header-only: install the single public header (upstream CMake installs
        # DIRECTORY include/effolkronium -> ${CMAKE_INSTALL_INCLUDEDIR}).
        copy(
            self,
            "random.hpp",
            src=os.path.join(self.source_folder, "include", "effolkronium"),
            dst=os.path.join(self.package_folder, "include", "effolkronium"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        # Mirror the upstream CMake package name/target so consumers can use
        # find_package(effolkronium_random) + effolkronium_random::effolkronium_random.
        self.cpp_info.set_property("cmake_file_name", "effolkronium_random")
        self.cpp_info.set_property("cmake_target_name", "effolkronium_random::effolkronium_random")
        self.cpp_info.set_property("cmake_build_modules", [])
