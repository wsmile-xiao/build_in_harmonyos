#!/usr/bin/env python3
"""Conan recipe — nob.h 3.9.0 (header-only C build-recipe library).

nob.h ("NoBuild") is a single-header C library for writing build recipes:
with nothing but a C compiler you can bootstrap a build system and compile
the rest of the project. Header-only (variant A): only nob.h is shipped,
no compilation step is required.

Upstream dual-licensed under MIT OR Unlicense.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class NobHConan(ConanFile):
    name = "nob.h"
    version = "3.9.0"
    description = "Header only library for writing build recipes in C (NoBuild)"
    license = "MIT OR Unlicense"
    homepage = "https://github.com/tsoding/nob.h"
    url = "https://github.com/tsoding/nob.h"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # Header-only library: no compilation step; headers packaged as-is.
        pass

    def package(self):
        # Variant A: header-only library
        copy(self, "nob.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        # Variant A: header-only, no lib/bin directories
        self.cpp_info.libs = []  # header-only: no libraries
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "nob.h")
        self.cpp_info.set_property("cmake_target_name", "nob.h::nob.h")
