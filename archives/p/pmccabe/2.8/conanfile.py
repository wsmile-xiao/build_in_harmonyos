#!/usr/bin/env python3
"""Conan recipe for pmccabe 2.8 — plain Makefile project (no configure).

pmccabe is a McCabe-style complexity analysis tool for C/C++ source code.
Build system: plain Makefile (not autotools — no configure script).
License: GPL-2.0-or-later
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PmccabeConan(ConanFile):
    name = "pmccabe"
    version = "2.8"
    description = "McCabe-style complexity analysis for C/C++ source code"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.com/pmccabe/pmccabe"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # No external dependencies

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R26: Terminal tools must be statically linked
        # pmccabe has no shared libs — only executables linked to system libc
        # BUILD_SHARED_LIBS=OFF is implicitly satisfied (no libraries built)
        pass

    def build(self):
        apply_conandata_patches(self)
        # Plain Makefile — no configure step needed
        # CC/CXX passed explicitly since system has no cc/gcc symlinks (R-iron)
        # Run in source folder since basic_layout may use a build subfolder
        self.run("make CC=clang CXX=clang++", cwd=self.source_folder)

    def package(self):
        # Install with DESTDIR and override INSTALL to avoid -o root -g root
        self.run(f'make install DESTDIR="{self.package_folder}" INSTALL="install"',
                 cwd=self.source_folder)
        # Reorganize from usr/bin layout to Conan standard bin/ layout
        usr_bin = os.path.join(self.package_folder, "usr", "bin")
        pkg_bin = os.path.join(self.package_folder, "bin")
        if os.path.isdir(usr_bin):
            os.makedirs(pkg_bin, exist_ok=True)
            for f in os.listdir(usr_bin):
                shutil.move(os.path.join(usr_bin, f), os.path.join(pkg_bin, f))
        # Move man pages to share/man/man1
        usr_share = os.path.join(self.package_folder, "usr", "share")
        pkg_share = os.path.join(self.package_folder, "share")
        if os.path.isdir(usr_share):
            os.makedirs(pkg_share, exist_ok=True)
            for f in os.listdir(usr_share):
                shutil.move(os.path.join(usr_share, f), os.path.join(pkg_share, f))
        # Clean up usr directory
        shutil.rmtree(os.path.join(self.package_folder, "usr"), ignore_errors=True)

    def package_info(self):
        # Tool-only package: no libraries to link against
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
