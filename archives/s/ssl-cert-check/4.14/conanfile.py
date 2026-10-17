#!/usr/bin/env python3
"""Conan recipe for ssl-cert-check 4.14 — pure shell script tool.

ssl-cert-check is a Bourne shell script that reports on expiring SSL
certificates. No compilation is needed; the build step only applies the
Makefile patch. Installation copies the script and documentation via
conan.tools.files.copy().
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SslCertCheckConan(ConanFile):
    name = "ssl-cert-check"
    version = "4.14"
    description = "Bourne shell script to report on expiring SSL certificates"
    license = "MIT"
    homepage = "https://github.com/Matty9191/ssl-cert-check"
    url = ""  # CI fills this

    package_type = "application"

    # CI L0p requires all four settings for OHOS profile compatibility
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches (creates Makefile for reference, but we use copy() for install).
        apply_conandata_patches(self)

    def package(self):
        # Install the script and documentation directly.
        copy(self, "ssl-cert-check", self.source_folder, os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "share", "doc", "ssl-cert-check"), keep_path=False)
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "share", "licenses", "ssl-cert-check"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
