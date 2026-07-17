#!/usr/bin/env python3
"""Conan recipe for BibTool 2.68 — a BibTeX database manipulation tool.

BibTool uses a Makefile-based build system (makefile.unx).
The autotools configure script fails on OHOS due to temp file permission issues,
so we use makefile.unx directly with modifications for clang and DESTDIR support.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BibtoolConan(ConanFile):
    name = "bib-tool"
    version = "2.68"
    description = "A tool for manipulating BibTeX databases - pretty-printing, sorting, searching, field rewriting"
    license = "GPL-2.0-or-later"
    homepage = "https://ctan.org/pkg/bibtool"
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

        # Copy makefile.unx to Makefile and apply OHOS adaptations
        makefile_src = os.path.join(self.source_folder, "makefile.unx")
        makefile_dst = os.path.join(self.source_folder, "Makefile")
        shutil.copy(makefile_src, makefile_dst)

        # Read and modify the Makefile
        with open(makefile_dst, "r") as f:
            content = f.read()

        # Fix 1: CC = gcc -> CC = clang
        content = content.replace("CC         = gcc", "CC         = clang")

        # Fix 2: CFLAGS = -> CFLAGS = -fPIC -O2
        content = content.replace(
            "CFLAGS  =\n# CFLAGS  = -O",
            "CFLAGS  = -fPIC -O2\n# CFLAGS  = -O",
        )

        # Fix 3: check(OBJ) -> check$(OBJ) (original makefile has a typo)
        content = content.replace("check(OBJ)", "check$(OBJ)")

        # Fix 4: Add DESTDIR support for staging installation
        content = content.replace(
            "BINDIR     = /usr/local/bin",
            "BINDIR     = $(DESTDIR)/usr/local/bin",
        )
        content = content.replace(
            "MANDIR     = /usr/local/man",
            "MANDIR     = $(DESTDIR)/usr/local/man",
        )
        content = content.replace(
            "LIBDIR     = /usr/local/lib/BibTool",
            "LIBDIR     = $(DESTDIR)/usr/local/lib/BibTool",
        )
        content = content.replace(
            "INCLUDEDIR = /usr/local/include/BibTool",
            "INCLUDEDIR = $(DESTDIR)/usr/local/include/BibTool",
        )

        # Fix 5: BIBTOOL_DEFAULT should use runtime path without DESTDIR
        # Use regex with line anchor — content.replace() silently fails if
        # the Makefile's quote escaping differs, and unanchored regex would
        # also match RSC_BIBTOOL_DEFAULT (a different C define)
        content = re.sub(
            r'(?m)^BIBTOOL_DEFAULT\s*=\s*.*',
            'BIBTOOL_DEFAULT   = \\".:/usr/local/lib/BibTool\\"',
            content,
        )

        with open(makefile_dst, "w") as f:
            f.write(content)

        # Build
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install to staging directory using DESTDIR
        self.run(
            f"make install DESTDIR={self.package_folder}",
            cwd=self.source_folder,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["usr/local/bin"]
        self.cpp_info.libdirs = ["usr/local/lib/BibTool"]
