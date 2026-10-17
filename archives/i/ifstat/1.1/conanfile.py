#!/usr/bin/env python3
"""Conan recipe for ifstat 1.1 (interface bandwidth statistics)."""

import os
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain


class IfstatConan(ConanFile):
    name = "ifstat"
    version = "1.1"
    package_type = "application"

    description = "Tool for reporting network interface bandwidth"
    license = "GPL-2.0"
    homepage = "https://gael.roualland.free.fr/ifstat/"
    topics = ("network", "bandwidth")

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # No upstream make check target available

    def package(self):
        copy(self, "ifstat", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
