#!/usr/bin/env python3
"""Conan recipe for bitflags 1.5.0 — header-only C++11/14/17 flag library.

bitflags (m-peko/bitflags) is a single-header header-only C++ library for
managing sets of auto-generated type-safe flags. No compilation is needed.
The recipe downloads the official source tarball (tag v1.5.0, sha256 pinned)
and copies the header into the package.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class BitflagsConan(ConanFile):
    name = "bitflags"
    version = "1.5.0"
    description = "Header-only C++ library for sets of auto-generated type-safe flags"
    license = "MIT"
    homepage = "https://github.com/m-peko/bitflags"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Header-only library with no third-party runtime dependencies.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only library: no compilation needed for the library itself.
        apply_conandata_patches(self)

    def package(self):
        # Copy headers (include/bitflags/bitflags.hpp)
        copy(self, "bitflags.hpp",
             src=os.path.join(self.source_folder, "include", "bitflags"),
             dst=os.path.join(self.package_folder, "include", "bitflags"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "bitflags")
        self.cpp_info.set_property("cmake_target_name", "bitflags::bitflags")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # Header-only library: no libs to link
        self.cpp_info.libs = []