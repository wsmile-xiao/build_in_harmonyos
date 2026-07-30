#!/usr/bin/env python3
"""Conan recipe — wcstools 3.9.7

WCSTools is a set of command-line utilities to create, display, and
manipulate the world coordinate system of FITS/IRAF images.
Makefile-based project (no autotools configure).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class WcstoolsConan(ConanFile):
    name = "wcstools"
    version = "3.9.7"
    description = "WCSTools: world coordinate system tools for FITS/IRAF images"
    license = "GPL-2.0-or-later"
    homepage = "http://tdc-www.harvard.edu/wcstools/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Upstream uses a plain Makefile (no configure).
        # CFLAGS: -fPIC for shared lib compatibility, -O2 for optimization
        # BIN=$(package_bin) sets the output directory for all 51 tools
        # Get C compiler from Conan conf (tools.build:compiler_executables),
        # fallback to 'clang' if not configured
        compilers = self.conf_info.get("tools.build:compiler_executables", {})
        cc = (compilers or {}).get("c") or "clang"
        bin_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        self.run(
            "make all "
            f"CFLAGS='-fPIC -O2 -D_FILE_OFFSET_BITS=64' "
            f"CC={cc} "
            f"BIN={bin_dir}",
            cwd=self.source_folder,
        )

    def package(self):
        # Copy all 51 binaries and the wcstools script to package bin/
        src_bin = os.path.join(self.build_folder, "bin")
        dst_bin = os.path.join(self.package_folder, "bin")
        copy(self, "*", src=src_bin, dst=dst_bin)
        # Also copy the wcstools shell script if it exists (help summary)
        wcstools_script = os.path.join(self.source_folder, "wcstools")
        if os.path.isfile(wcstools_script):
            copy(self, "wcstools", src=self.source_folder, dst=dst_bin)

    def package_info(self):
        # Command-line tool package: no libraries to link against
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
