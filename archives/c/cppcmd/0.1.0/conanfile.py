#!/usr/bin/env python3
"""Conan recipe — cppcmd 0.1.0 (header-only C++ library).

cppcmd is a simple header-only C++ command interpreter library
(https://github.com/remysalim/cppcmd). The upstream build system is CMake
(INTERFACE library target cppcmd, install() copies include/ only), so this
recipe follows the header-only variant: no compile stage, package() copies
the public headers and license.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class CppcmdConan(ConanFile):
    name = "cppcmd"
    version = "0.1.0"
    description = "A simple header-only C++ command interpreter library"
    license = "MIT"
    homepage = "https://github.com/remysalim/cppcmd"
    url = "https://github.com/remysalim/cppcmd"

    package_type = "header-library"  # Conan 2 header-only type (no shared option needed)

    # Header-only: settings kept for structural consistency; package_id cleared
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
        # Header-only library: nothing to compile. No compile log is faked
        # (R34) — the public headers are installed verbatim in package().
        pass

    def package(self):
        # Variant A: header-only library — keep the include/cppcmd/ hierarchy
        copy(self, "**/*.hpp", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()  # no build deps → single package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
