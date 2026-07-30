#!/usr/bin/env python3
"""Conan recipe for otf-atkinson 1.006 — Atkinson Hyperlegible OTF font package."""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class OtfAtkinsonConan(ConanFile):
    name = "otf-atkinson"
    version = "1.006"
    description = (
        "Atkinson Hyperlegible font family — OTF format. "
        "A typeface focused on legibility and readability for low vision readers, "
        "published by the Braille Institute under the SIL Open Font License."
    )
    license = "OFL-1.1"
    homepage = "https://github.com/googlefonts/atkinson-hyperlegible"
    url = ""
    package_type = "application"

    settings = "os", "arch"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        otf_src = os.path.join(self.source_folder, "fonts", "otf")
        otf_dst = os.path.join(self.package_folder, "share", "fonts", "OTF")
        copy(self, "*.otf", src=otf_src, dst=otf_dst, keep_path=False)
        copy(self, "OFL.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share/fonts/OTF"]
        self.user_info.font_dir = "share/fonts/OTF"
