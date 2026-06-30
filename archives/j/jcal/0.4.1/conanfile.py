#!/usr/bin/env python3
"""Conan recipe for jcal 0.4.1 — Jalali calendar library and terminal tools.

This recipe enforces R26: static linking for terminal tools.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class JcalConan(ConanFile):
    name = "jcal"
    version = "0.4.1"
    description = "Jalali calendar library and terminal tools (jcal, jdate)"
    license = "GPL-3.0-or-later"
    homepage = "https://nongnu.org/jcal"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=False)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--enable-static")
        tc.extra_ldflags.append("-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.autoreconf()
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["jalali"]
