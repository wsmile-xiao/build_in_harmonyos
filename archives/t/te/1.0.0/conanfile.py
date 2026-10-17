#!/usr/bin/env python3
"""Conan recipe — te (boost-ext/te) 1.0.0, header-only C++17 type erasure library.

te is a header-only library: the whole public API lives in include/boost/te.hpp.
No compilation is required; the recipe only installs headers (variant A of the
header-only template) and a test_package that includes and exercises the header.
"""
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout
import os


class TeConan(ConanFile):
    name = "te"
    version = "1.0.0"
    description = "te: C++17 type erasure library (boost-ext/te)"
    license = "BSL-1.0"
    homepage = "https://github.com/boost-ext/te"
    url = "https://github.com/boost-ext/te"

    package_type = "header-library"

    # Header-only: no compiled artifacts, but keep structural consistency
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only: nothing to compile; only patches may be applied.
        apply_conandata_patches(self)

    def package(self):
        # te is a single-header library: include/boost/te.hpp
        copy(self, "te.hpp",
             src=os.path.join(self.source_folder, "include", "boost"),
             dst=os.path.join(self.package_folder, "include", "boost"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()  # header-only: single package_id across configs

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
