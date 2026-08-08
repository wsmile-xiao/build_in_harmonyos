#!/usr/bin/env python3
"""Conan recipe for algol68g 3.1.2 — Algol 68 Genie compiler-interpreter (Autotools)."""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Algol68GConan(ConanFile):
    name = "algol68g"
    version = "3.1.2"
    description = "Algol 68 Genie - a compiler-interpreter for Algol 68"
    license = "GPL-3.0-or-later"
    homepage = "https://algol68genie.nl/"
    url = "https://algol68genie.nl/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

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
        # R33: never rely on undefined shell env vars; toolchain from Conan
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
