#!/usr/bin/env python3
"""Conan recipe for osinfo-db — a pure data package.

osinfo-db is a database of operating system, platform, and device
information used by libosinfo. It contains only XML/JSON data files
and requires no compilation.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class OsinfoDBConan(ConanFile):
    name = "osinfo-db"
    version = "20250124"
    description = "OS information database — XML/JSON data files describing operating systems, platforms, and devices"
    license = "GPL-2.0-or-later"
    homepage = "https://libosinfo.org/"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        dst = os.path.join(self.package_folder, "share", "osinfo")
        copy(self, "*", src=self.source_folder, dst=dst, excludes=".*")

    def package_info(self):
        self.cpp_info.resdirs = ["share/osinfo"]
