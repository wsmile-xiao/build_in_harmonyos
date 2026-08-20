#!/usr/bin/env python3
"""Conan recipe — iat 0.1.7 (Autotools)

iat (Iso9660 Analyzer Tool) is a command-line tool for detecting
the structure of DVD/CD-ROM image files.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class IatConan(ConanFile):
    name = "iat"
    version = "0.1.7"
    description = "Iso9660 Analyzer Tool — detect and convert DVD/CD-ROM image formats"
    license = "GPL-2.0"
    homepage = "https://iat.berlios.org"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

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
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
