#!/usr/bin/env python3
"""Conan recipe for zpl 9.8.0 — single-header C99 foundational library.

zpl is a header-only library: consumers define `ZPL_IMPLEMENTATION` in exactly
ONE source file BEFORE including <zpl.h> (stb-style embedding). The repository
ships the amalgamated code/zpl.h plus the optional modules zpl_math.h and
zpl_image.h (which require zpl.h to be included first). No compilation is
needed for the library itself; this recipe copies the public headers into the
package include directory.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class ZplConan(ConanFile):
    name = "zpl"
    version = "9.8.0"
    description = (
        "A C99 single-header foundational library: memory allocators, "
        "collections, strings, files, time, JSON5, options parsing and more."
    )
    license = "Unlicense AND Apache-2.0"
    homepage = "https://github.com/zpl-c/zpl"
    url = ""  # CI fills this
    topics = ("header-only", "c99", "collections", "string", "json5", "utilities")

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
        # Header-only library: nothing to compile. The amalgamated zpl.h
        # shipped in the official tag is used as-is (no regeneration needed).

    def package(self):
        # Core public header: code/zpl.h -> include/zpl.h
        copy(
            self,
            "zpl.h",
            src=os.path.join(self.source_folder, "code"),
            dst=os.path.join(self.package_folder, "include"),
        )
        # Optional companion modules (require zpl.h included first):
        for header in ("zpl_math.h", "zpl_image.h"):
            copy(
                self,
                header,
                src=os.path.join(self.source_folder, "code"),
                dst=os.path.join(self.package_folder, "include"),
            )
        # License file: dual Unlicense / Apache-2.0
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_id(self):
        self.info.clear()  # header-only: single package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "zpl")
        self.cpp_info.set_property("cmake_target_name", "zpl::zpl")
