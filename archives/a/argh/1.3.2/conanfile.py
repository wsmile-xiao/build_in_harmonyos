#!/usr/bin/env python3
"""Conan recipe for argh 1.3.2 — C++11 header-only argument parser.

argh is a header-only, single-file C++11 library for parsing command-line
arguments. No build step is required; the package simply installs argh.h.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ArghConan(ConanFile):
    name = "argh"
    version = "1.3.2"
    description = "C++11 header-only minimalistic argument parser (single-file)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/adishavit/argh"
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
        copy(self, "argh.h", self.source_folder,
             os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
