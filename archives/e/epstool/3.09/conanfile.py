#!/usr/bin/env python3
"""Conan recipe — epstool 3.09 (custom makefile, no configure script).

epstool is a command-line EPS preview manipulation tool. It uses a custom
makefile (src/unixcom.mak + src/common.mak) with no configure/config.guess.
The makefile hard-codes CC=gcc; we override via make variables.

Key points:
  - package_type = "application" (produces bin/epstool executable, no library)
  - build() calls make directly with CC/CLINK/LINK from Conan conf (R33)
  - install uses prefix= + EPSTOOL_ROOT= to control install root
  - No external library dependencies (X11 is a preprocessor macro only)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class EpstoolConan(ConanFile):
    name = "epstool"
    version = "3.09"
    description = "Command-line tool for editing EPS preview images and bitmaps"
    license = "Aladdin Free Public License"
    homepage = "https://github.com/ArtifexSoftware/ghostpdl"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: Get compiler from Conan conf, never from shell env vars.
        # epstool makefile hard-codes CC=gcc; we override via make variables.
        pass

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler path from Conan conf (CI workers may not have $CC set)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        # CFLAGS: add -fPIC and -O2 for OHOS
        cflags = "-fPIC -O2"
        # The makefile file is named "makefile" (lowercase), run from source folder
        # CC/CLINK/LINK/CCAUX all need to be clang (makefile defaults to gcc)
        self.run(f'make -f makefile CC={cc} CLINK={cc} LINK={cc} CCAUX={cc} '
                 f'CFLAGS="{cflags}" -j1', cwd=self.source_folder)

    def package(self):
        # Install using prefix= + EPSTOOL_ROOT= to place files under package_folder
        # EPSTOOL_BASE = $(prefix)$(EPSTOOL_ROOT), so prefix=self.package_folder + EPSTOOL_ROOT empty
        pf = self.package_folder.replace(" ", "\\ ")
        self.run(f'make -f makefile install prefix={pf} EPSTOOL_ROOT=',
                 cwd=self.source_folder)
        # Copy the binary explicitly to ensure it's in bin/
        copy(self, "epstool", os.path.join(self.source_folder, "bin"),
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Application package — no libs, just bindir
        self.cpp_info.bindirs = ["bin"]
