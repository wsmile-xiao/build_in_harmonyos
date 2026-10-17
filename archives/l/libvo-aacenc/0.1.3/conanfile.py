#!/usr/bin/env python3
"""Conan recipe for libvo-aacenc 0.1.3."""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibvoaacencConan(ConanFile):
    name = "libvo-aacenc"
    version = "0.1.3"
    description = "VisualOn AAC encoder library"
    license = "Apache-2.0"
    homepage = "https://opencore-amr.sourceforge.net/"
    url = ""  # CI fills this
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--enable-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        if not cross_building(self):
            autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["vo-aacenc"]
        self.cpp_info.set_property("pkg_config_name", "vo-aacenc")
