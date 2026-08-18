#!/usr/bin/env python3
# bvi 1.5.0 — OHOS aarch64 build recipe
"""Conan recipe — bvi 1.5.0 (Binary Visual Editor).

A vi-like hex editor for editing binary files.
Produces executables: bvi, bmore, bview (symlink), bvedit (symlink).

Build system: autotools (configure + make)
License: GPL-3.0-or-later
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.env import Environment
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BviConan(ConanFile):
    name = "bvi"
    version = "1.5.0"
    description = "Binary Visual Editor - vi-like hex editor for binary files"
    license = "GPL-3.0-or-later"
    homepage = "http://bvi.sourceforge.net/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        # ncurses: pass include/lib paths from Conan dependency to configure
        ncurses = self.dependencies["ncurses"]
        ncurses_inc = os.path.join(ncurses.package_folder, "include")
        ncurses_lib = os.path.join(ncurses.package_folder, "lib")
        tc.extra_cflags.append(f"-I{ncurses_inc}")
        tc.extra_ldflags.append(f"-L{ncurses_lib}")
        # Force build triplet for HarmonyOS platform detection
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()
        # ncurses package provides libncursesw.a (wide-char); configure's
        # AC_SEARCH_LIBS looks for -lncurses (without 'w'). Set LIBS so
        # the linker finds initscr in libncursesw.a.
        env = Environment()
        env.append("LIBS", "-lncursesw")
        env.vars(self).save_script("bvi_libs")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        # Manual install: out-of-source build breaks make install's file paths
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share/man/man1")
        helpdir = os.path.join(self.package_folder, "share/bvi")
        for d in [bindir, mandir, helpdir]:
            os.makedirs(d, exist_ok=True)
        # Binaries from build dir
        copy(self, "bvi", self.build_folder, bindir)
        copy(self, "bmore", self.build_folder, bindir)
        # Symlinks bview -> bvi, bvedit -> bvi
        for name in ["bview", "bvedit"]:
            link = os.path.join(bindir, name)
            if os.path.lexists(link):
                os.remove(link)
            os.symlink("bvi", link)
        # Man pages and help file from source dir
        copy(self, "bvi.1", self.source_folder, mandir)
        copy(self, "bmore.1", self.source_folder, mandir)
        copy(self, "bmore.help", self.source_folder, helpdir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
