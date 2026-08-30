#!/usr/bin/env python3
"""Conan recipe for hypatia — header-only math library for 2D/3D graphics.

hypatia is a single-file-header, pure-C math library for graphics programming.
No compilation needed, just copy hypatia.h to include directory.
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class HypatiaConan(ConanFile):
    name = "hypatia"
    version = "2.0.0"
    description = "Single-file header-only C math library for 2D/3D graphics"
    license = "MIT"
    homepage = "https://github.com/dagostinelli/hypatia"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package_id(self):
        self.info.clear()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "hypatia.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
