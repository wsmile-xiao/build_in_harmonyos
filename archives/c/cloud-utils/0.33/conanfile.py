#!/usr/bin/env python3
"""Conan recipe for cloud-utils 0.33 — Shell/Python cloud utility scripts.

cloud-utils provides utilities for interacting with cloud images and instances.
It is a pure script package (no compilation), installed via a simple Makefile.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CloudutilsConan(ConanFile):
    name = "cloud-utils"
    version = "0.33"
    description = "Utilities for interacting with cloud images and instances"
    license = "GPL-3.0"
    homepage = "https://github.com/canonical/cloud-utils"

    package_type = "application"
    settings = ("os", "arch")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        pkg = self.package_folder
        self.run(
            f"make -C {self.source_folder} install"
            f" BINDIR={pkg}/bin"
            f" MANDIR={pkg}/share/man/man1"
            f" DOCDIR={pkg}/share/doc/cloud-utils"
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
