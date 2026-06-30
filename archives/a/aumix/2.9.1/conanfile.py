#!/usr/bin/env python3
"""Conan recipe — aumix 2.9.1 (Autotools).

aumix: Ncurses-based audio mixer for OSS sound systems.
License: GPL-2.0
Homepage: http://www.jpj.net/~trevor/aumix.html
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AumixConan(ConanFile):
    name = "aumix"
    version = "2.9.1"
    description = "Ncurses-based audio mixer for OSS sound systems"
    license = "GPL-2.0"
    homepage = "http://www.jpj.net/~trevor/aumix.html"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--without-gtk")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
