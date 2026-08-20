#!/usr/bin/env python3
"""Conan recipe — paperkey 1.6 (Autotools)

paperkey is a CLI tool for extracting OpenPGP secret keys to paper backup.
Pure C, no external dependencies (gnulib internal modules only).
Build system: autotools (Autoconf 2.66).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PaperkeyConan(ConanFile):
    name = "paperkey"
    version = "1.6"
    description = "OpenPGP secret key paper backup tool"
    license = "GPL-2.0-or-later"
    homepage = "https://www.jabberwocky.com/software/paperkey/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        self.tool_requires("automake/1.18")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
