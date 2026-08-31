#!/usr/bin/env python3
"""Conan recipe for stb_image_write — Header-only image writing library.

stb_image_write is a single-header public domain library for writing images
in PNG, BMP, TGA, JPEG, and HDR formats.
"""
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os


class StbImageWriteConan(ConanFile):
    name = "stb_image_write"
    version = "1.16"
    description = "Single-file public domain library for writing images to PNG/BMP/TGA/JPEG/HDR"
    license = "Public Domain OR MIT"
    homepage = "https://github.com/nothings/stb"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"]["1.16"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Header-only library, no build step

    def package_id(self):
        self.info.clear()

    def package(self):
        copy(self, "stb_image_write.h",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"),
             keep_path=False)
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
