#!/usr/bin/env python3
"""Conan recipe for semver 0.3.0 — header-only C++17 semantic versioning library.

semver (Neargye/semver) is a header-only C++17 library for Semantic
Versioning 2.0.0 (parsing, validation, comparison, range matching).
No compilation is needed. The recipe downloads the official source
tarball and copies the single header into the package.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class SemverConan(ConanFile):
    name = "semver"
    version = "0.3.0"
    description = "Semantic Versioning 2.0.0 library for C++ (header-only)"
    license = "MIT"
    homepage = "https://github.com/Neargye/semver"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only library: no compilation needed for the library itself.
        apply_conandata_patches(self)

    def package(self):
        # Copy headers
        copy(self, "*",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "semver")
        self.cpp_info.set_property("cmake_target_name", "semver::semver")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # Header-only library: no libs to link
        self.cpp_info.libs = []
