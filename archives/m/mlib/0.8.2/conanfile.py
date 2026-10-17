#!/usr/bin/env python3
"""Conan recipe — mlib 0.8.2 (header-only C99 generic containers & algorithms).

mlib (M** library) by Patrick Pelissier — a library of generic and efficient
C algorithms and data structures (arrays, lists, dicts, rbtree, bptree,
strings, serialization, ...), implemented as C99 headers (m-*.h). The 0.8.2
tarball ships no library build system (the root Makefile only drives
tests/doc/example), so the recipe packages the headers as-is.
"""
import os

from conan import ConanFile
from conan.tools.cmake import cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class MlibConan(ConanFile):
    name = "mlib"
    version = "0.8.2"
    description = "mlib — a library of generic and efficient C algorithms and data structures, header-only C99"
    license = "BSD-2-Clause"
    homepage = "https://github.com/P-p-H-d/mlib"
    url = "https://github.com/P-p-H-d/mlib"
    topics = ("containers", "algorithms", "header-only", "c99", "generic")

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
        # header-only libraries without a CMake/meson/autotools project).
        pass

    def package(self):
        # All public headers live at the tarball root as m-*.h and include
        # each other by bare name, so they must be copied together.
        copy(self, "m-*.h",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "mlib")
        self.cpp_info.set_property("cmake_target_name", "mlib::mlib")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # Header-only library: no libs to link.
        self.cpp_info.libs = []
