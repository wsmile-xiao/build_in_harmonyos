#!/usr/bin/env python3
"""Conan recipe — cppitertools 2.3 (CMake, header-only).

cppitertools is a header-only C++17 range library inspired by Python's
itertools and builtins. Upstream CMake `install()` only installs the
`cppitertools` header directory plus a CMake package config; no compiled
library is produced. It is a pure interface target (cxx_std_17), so this
package ships as a header-library with an empty libdir/bindir.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get


class CppIterToolsConan(ConanFile):
    name = "cppitertools"
    version = "2.3"
    description = "Range-based for-loop add-ons inspired by the Python builtins and itertools (header-only)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/ryanhaining/cppitertools"
    url = "https://github.com/ryanhaining/cppitertools"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        # NOTE: upstream ships a Bazel `BUILD` file at repo root; on
        # case-insensitive filesystems the default "build" folder collides
        # with it (NotADirectoryError). Use a distinct folder name.
        cmake_layout(self, build_folder="build_dir")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Header-only: expose the include dir and the upstream CMake target
        # name cppitertools::cppitertools (exported by upstream CMakeLists.txt).
        self.cpp_info.set_property("cmake_file_name", "cppitertools")
        self.cpp_info.set_property("cmake_target_name", "cppitertools::cppitertools")
        self.cpp_info.requires = []
        self.cpp_info.cxxflags = []