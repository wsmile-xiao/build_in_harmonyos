#!/usr/bin/env python3
"""Conan recipe — libtar, a C library for manipulating POSIX tar files."""

import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibtarConan(ConanFile):
    name = "libtar"
    version = "1.2.20"
    description = "C library for manipulating POSIX tar files"
    license = "NCSA"
    homepage = "https://repo.or.cz/libtar.git"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # CI workers lack automake/libtoolize; ship pre-generated autotools
        # files (configure, Makefile.in, ltmain.sh, etc.) alongside patches.
        copy(self, "prebuilt.tar.gz",
             src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # Source tarball is a git snapshot without pre-generated configure.
        # CI workers lack automake/libtoolize, so pre-generated autotools
        # files (configure, Makefile.in, ltmain.sh, etc.) are shipped via
        # exports and extracted here instead of running autoreconf.
        self.run("tar xzf {} -C {}".format(
            os.path.join(self.source_folder, "prebuilt.tar.gz"), src))
        if self.settings.os == "OHOS":
            # Fix shebangs (no /bin/sh or /bin/bash on OpenHarmony)
            for f in ["configure", "autoconf/compile", "autoconf/missing",
                       "autoconf/install-sh", "autoconf/config.sub",
                       "autoconf/config.guess"]:
                path = os.path.join(src, f)
                if os.path.exists(path):
                    self.run(f"sed -i '1s|^#!.*|#!/data/service/hnp/bin/bash|' {path}")
            # Remove umask 077 from temp dir creation (HMDFS blocks file
            # creation in 700-permission directories)
            self.run("sed -i 's|umask 077 && mktemp|mktemp|g; "
                     "s|umask 077 && mkdir|mkdir|g' configure", cwd=src)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["tar"]
        self.cpp_info.bindirs = ["bin"]
