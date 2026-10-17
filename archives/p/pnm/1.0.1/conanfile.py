#!/usr/bin/env python3
"""Conan recipe for pnm 1.0.1, a header-only PNM image I/O library."""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class PnmConan(ConanFile):
    name = "pnm"
    version = "1.0.1"
    description = "Header-only C++ reader and writer for PBM, PGM and PPM images"
    license = "MIT"
    homepage = "https://github.com/ToruNiina/pnm"
    url = "https://github.com/ToruNiina/pnm"
    topics = ("pnm", "image", "header-only", "cpp")
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        if hasattr(self.settings, "os") and hasattr(self.settings.os, "version"):
            self.settings.rm_safe("os.version")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Keep the standard patch hook for reproducible, patch-free releases.
        apply_conandata_patches(self)

    def package(self):
        copy(self, "pnm.hpp", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "pnm")
        self.cpp_info.set_property("cmake_target_name", "pnm::pnm")
