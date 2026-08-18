#!/usr/bin/env python3
"""Conan recipe for ait (Small but mighty GNU Emacs style editor).

ait is a terminal text editor written in C (Kevin Bloom).
Source: https://notabug.org/nuclearkev/ait/
Build system: plain Makefile (no configure needed)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, chdir
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class AitConan(ConanFile):
    name = "ait"
    version = "1.15"
    description = "Small but mighty GNU Emacs style editor"
    license = "BSD-3-Clause"
    homepage = "https://notabug.org/nuclearkev/ait/"
    url = "https://notabug.org/nuclearkev/ait/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: settings.os must be Linux or OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # R33: Use GnuToolchain to inject CC/CFLAGS from Conan profile
    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # makefile uses ?= so it picks up CC/CFLAGS injected by GnuToolchain
        # (R33: never read ${CC} from shell env; Conan toolchain provides it)
        with chdir(self, self.source_folder):
            # R9: Always use -j1
            self.run("make -j1")

    def package(self):
        copy(self, "ait", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "ait.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))
        # Auxiliary helper scripts shipped upstream (makefile install-scripts)
        for s in ("align", "ff", "fgf", "fgt", "gff", "gg", "ggt", "spell"):
            copy(self, s, os.path.join(self.source_folder, "scripts"), os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
