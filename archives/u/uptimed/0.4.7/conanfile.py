#!/usr/bin/env python3
"""Conan recipe — uptimed 0.4.7 (autotools).

Utility to track your highest uptimes.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UptimedConan(ConanFile):
    name = "uptimed"
    version = "0.4.7"
    description = "Utility to track your highest uptimes"
    license = "MIT"
    homepage = "https://github.com/rpodgorny/uptimed"
    url = ""

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
        # R26: Terminal tools must be statically linked (BUILD_SHARED_LIBS=OFF equivalent)
        tc.extra_ldflags.append("-static")
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--enable-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # uptimed ships configure.ac + autogen.sh, not a pre-generated configure
        # Run autoreconf in source folder to generate configure script
        self.run("AUTOM4TE=autom4te autoreconf -fi || "
                 "(libtoolize --automake --copy --force && AUTOM4TE=autom4te autoreconf -fi)",
                 cwd=self.source_folder)
        # HMDFS platform fix: umask 077 creates dirs with 0700 perms which
        # prevents file creation on this filesystem. Change to 022 (0755 dirs).
        self.run("sed -i 's/umask 077/umask 022/g' configure",
                 cwd=self.source_folder)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["uptimed"]
        # uptimed does not install public headers
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
