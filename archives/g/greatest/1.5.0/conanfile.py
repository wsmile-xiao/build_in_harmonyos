#!/usr/bin/env python3
"""Conan recipe for greatest — header-only C/C++ testing framework.

greatest is a single-header testing library (greatest.h) with no build system,
no dependencies, and no separate compilation.
"""
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout
import os


class GreatestConan(ConanFile):
    name = "greatest"
    version = "1.5.0"
    description = "A testing system for C, contained in 1 header file"
    license = "MIT"
    homepage = "https://github.com/silentbicycle/greatest"
    url = ""  # CI fills this
    topics = ("testing", "unit-test", "header-only")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"]["1.5.0"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
