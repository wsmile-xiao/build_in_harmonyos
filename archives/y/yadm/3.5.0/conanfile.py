#!/usr/bin/env python3
"""Conan recipe — yadm 3.5.0 (script/makefile)."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches
from conan.tools.layout import basic_layout


class YadmConan(ConanFile):
    name = "yadm"
    version = "3.5.0"
    description = "Yet Another Dotfiles Manager — manage dotfiles using Git"
    license = "GPL-3.0-only"
    homepage = "https://yadm.io"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # yadm is a pure bash script, no compilation needed
        pass

    def package(self):
        copy(self, "yadm", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "yadm.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "share", "doc", "yadm"))
        copy(self, "CHANGES", self.source_folder, os.path.join(self.package_folder, "share", "doc", "yadm"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
