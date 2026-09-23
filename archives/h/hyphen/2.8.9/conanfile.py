#!/usr/bin/env python3
"""Conan recipe — hyphen 2.8.9 (Autotools, libhyphen hyphenation library)."""
# -*- coding: utf-8 -*-

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class HyphenConan(ConanFile):
    name = "hyphen"
    version = "2.8.9"
    description = "hyphen 2.8.9 — hyphenation library (libhyphen) from Hunspell project"
    license = "LGPL-2.1-or-later AND GPL-2.0-or-later AND MPL-1.1"
    homepage = "https://github.com/hunspell/hyphen"
    url = "https://github.com/hunspell/hyphen"

    package_type = "library"

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
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
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
        self.cpp_info.libs = ["hyphen"]
