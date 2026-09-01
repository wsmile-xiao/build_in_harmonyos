#!/usr/bin/env python3
"""Conan recipe — advancescan 1.18 (Autotools)"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AdvancescanConan(ConanFile):
    name = "advancescan"
    version = "1.18"
    description = "Command-line tool for scanning and verifying MAME ROM collections, with diff support"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/amadvance/advancescan"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Prevent make from trying to re-run automake-1.17 (not installed):
        # set source files older than generated files so make skips regeneration
        import time
        now = time.time()
        old = now - 120
        for f in ("Makefile.am", "configure.ac", "configure.in"):
            p = os.path.join(self.source_folder, f)
            if os.path.exists(p):
                os.utime(p, (old, old))
        for f in ("Makefile.in", "aclocal.m4", "configure", "config.h.in",
                  "config.guess", "config.sub", "install-sh", "missing", "compile"):
            p = os.path.join(self.source_folder, f)
            if os.path.exists(p):
                os.utime(p, (now, now))
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["z"]
