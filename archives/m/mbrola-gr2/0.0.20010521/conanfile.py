#!/usr/bin/env python3
"""Conan 2 recipe for the MBROLA Greek GR2 voice database."""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class MbrolaGr2Conan(ConanFile):
    name = "mbrola-gr2"
    version = "0.0.20010521"
    description = "Greek male diphone voice database for MBROLA"
    license = "LicenseRef-MBROLA-GR2"
    homepage = "https://github.com/numediart/MBROLA-voices"
    url = "https://github.com/numediart/MBROLA-voices"
    package_type = "unknown"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # GR2 is architecture-independent voice data and has no build system.
        apply_conandata_patches(self)

    def package(self):
        voice_dir = os.path.join(self.package_folder, "share", "mbrola", "gr2")
        doc_dir = os.path.join(
            self.package_folder, "share", "doc", "mbrola-gr2"
        )

        copy(
            self,
            "gr2",
            src=self.source_folder,
            dst=voice_dir,
            keep_path=False,
        )
        copy(
            self,
            "*.PHO",
            src=os.path.join(self.source_folder, "TEST"),
            dst=os.path.join(voice_dir, "TEST"),
            keep_path=False,
        )
        copy(
            self,
            "README.txt",
            src=self.source_folder,
            dst=doc_dir,
            keep_path=False,
        )
        copy(
            self,
            "license.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share"]
