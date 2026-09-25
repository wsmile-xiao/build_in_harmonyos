#!/usr/bin/env python3
"""Conan recipe — ffc.h 26.07.01 (Header-only C library).

ffc.h is a single-file (amalgamated) header-only C library for fast
float/parse conversion, published as a CMake INTERFACE target.  There is
no compiled library artifact, so this recipe follows the header-only
package variant (package_type = header-library): copy the public header
into include/ and expose the include path via cpp_info.  The amalgamated
ffc.h at the repo root is the installed public header (see upstream
CMakeLists install(FILES ffc.h ...)).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class FfcHConan(ConanFile):
    name = "ffc.h"
    version = "26.07.01"
    description = (
        "ffc.h: fast, dependency-free C parsing of floating point numbers, "
        "integers and booleans from text (header-only)."
    )
    license = "MIT"
    homepage = "https://github.com/kolemannix/ffc.h"
    url = "https://github.com/kolemannix/ffc.h"

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
        # Header-only: nothing to compile. Patches are applied here so the
        # recipe keeps the standard patch pipeline (no fake build logs).
        apply_conandata_patches(self)

    def package(self):
        # Variant A: header-only library — public header at repo root.
        copy(self, "ffc.h",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"),
             keep_path=False)
        copy(self, "LICENSE*",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_id(self):
        self.info.clear()  # header-only: single package_id

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "ffc")
        self.cpp_info.set_property("cmake_target_name", "ffc::ffc")