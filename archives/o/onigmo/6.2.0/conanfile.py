#!/usr/bin/env python3
"""Conan recipe for Onigmo 6.2.0 using the release Autotools files."""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OnigmoConan(ConanFile):
    name = "onigmo"
    version = "6.2.0"
    description = "Regular expressions library forked from Oniguruma"
    license = "MIT"
    homepage = "https://github.com/k-takata/Onigmo"
    url = "https://github.com/k-takata/Onigmo"
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        autotools.make(target="check", args=["-j1"])
        autotools.make(target="test_enc_utf8", args=["-j1"])
        self.run("./test_enc_utf8")

    def package(self):
        Autotools(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["onigmo"]
