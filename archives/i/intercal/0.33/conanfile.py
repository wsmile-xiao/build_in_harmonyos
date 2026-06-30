#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Intercal, intercal, 0.33, intercal 0.33, MIT,
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class IntercalConan(ConanFile):
    name = "intercal"
    version = "0.33"
    description = "Esoteric, parody programming language"
    license = "GPL-2.0-or-later"
    homepage = "http://catb.org/~esr/intercal/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        tc.configure_args.append("--disable-dependency-tracking")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix umask 077 causing Permission denied on HMDFS (E007-related)
        import subprocess
        subprocess.run(["sed", "-i", "s/umask 077/umask 022/g", "configure"],
                       cwd=self.source_folder, check=True)
        # Remove GCC-specific -fno-toplevel-reorder unsupported by clang
        subprocess.run(["sed", "-i", "/-fno-toplevel-reorder/d",
                        "buildaux/Makefile.am", "buildaux/Makefile.in"],
                       cwd=self.source_folder, check=True)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["ick", "ickmt", "ickec", "yuk"]
