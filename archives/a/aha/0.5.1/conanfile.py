#!/usr/bin/env python3
"""Conan recipe for aha (ANSI HTML Adapter).

aha converts ANSI terminal escape sequences to HTML.
Source: https://github.com/theZiz/aha
Build system: Makefile (no configure needed)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, chdir
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class AhaConan(ConanFile):
    name = "aha"
    version = "0.5.1"
    description = "ANSI HTML Adapter - converts ANSI terminal escape sequences to HTML"
    license = "LGPL-2.1-or-later", "MPL-1.1"
    homepage = "https://github.com/theZiz/aha"
    url = ""  # CI fills this

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

    # R33: Use GnuToolchain to inject CC/CXX/CFLAGS from Conan profile
    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # The Makefile is in the source folder; basic_layout uses a separate build dir
        with chdir(self, self.source_folder):
            # R9: Always use -j1
            self.run("make -j1")

    def package(self):
        copy(self, "aha", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "aha.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

