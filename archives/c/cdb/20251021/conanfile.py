#!/usr/bin/env python3
"""Conan recipe for cdb (D.J. Bernstein's constant database).

cdb uses DJB's custom build system (not autotools):
- conf-cc: compiler command for .c files
- conf-ld: linker command for .o -> executable
- conf-home: installation prefix
- make: builds all tools
- No configure script; no shared libraries

R26: Terminal tools must be statically linked (BUILD_SHARED_LIBS=OFF).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, replace_in_file, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CdbConan(ConanFile):
    name = "cdb"
    version = "20251021"
    description = "Cdb is a fast, reliable, simple package for creating and reading constant databases"
    license = "LicenseRef-Homebrew-cannot-represent"
    homepage = "https://cr.yp.to/cdb.html"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R26: Terminal tools must be statically linked
        # DJB build system uses conf-ld for linker flags, set in build()
        pass

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder

        # Fix: error.h declares `extern int errno;` which fails on modern systems.
        # Replace with `#include <errno.h>` which provides errno as a macro.
        replace_in_file(self, os.path.join(src, "error.h"),
                        "extern int errno;", "#include <errno.h>")

        # Configure DJB build system via conf-* files
        cc = "clang"
        # conf-cc: compiler for .c files
        with open(os.path.join(src, "conf-cc"), "w") as f:
            f.write(f"{cc} -O2\n")
        # conf-ld: linker with static flag (R26)
        with open(os.path.join(src, "conf-ld"), "w") as f:
            f.write(f"{cc} -static\n")
        # conf-home: installation prefix (used by hier.c/install)
        with open(os.path.join(src, "conf-home"), "w") as f:
            f.write(os.path.join(self.package_folder, "") + "\n")

        # Build all targets (DJB Makefile in source dir)
        self.run("make -j1", cwd=src)

    def package(self):
        # cdb produces command-line tools, not libraries
        # Copy all cdb tools to bin/
        src = self.source_folder
        for tool in ["cdbget", "cdbmake", "cdbdump", "cdbstats",
                      "cdbtest", "cdbmake-12", "cdbmake-sv"]:
            copy(self, tool, src=src,
                 dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # cdb is a command-line tool package; expose bin/ directory
        self.cpp_info.bindirs = ["bin"]
        # R26: BUILD_SHARED_LIBS=OFF — cdb has no shared libraries
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
