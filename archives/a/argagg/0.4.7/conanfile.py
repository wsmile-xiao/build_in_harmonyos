#!/usr/bin/env python3
"""Conan recipe for argagg 0.4.7 — header-only C++11 command-line argument parser.

argagg is a header-only library. No compilation is needed for the library
itself. The recipe copies header files to the package folder.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class ArgaggConan(ConanFile):
    name = "argagg"
    version = "0.4.7"
    description = "A C++11 command-line argument aggregation parser (header-only)"
    license = "MIT"
    homepage = "https://github.com/vietjtnguyen/argagg"
    url = ""  # CI fills this

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
        copy(
            self,
            "*.hpp",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
            keep_path=True,
        )

    def package_info(self):
        self.cpp_info.libs = []
