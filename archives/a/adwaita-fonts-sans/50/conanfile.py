#!/usr/bin/env python3
"""Conan recipe — adwaita-fonts-sans 50 (Adwaita Sans font package).

This is a data-only package: it installs the Adwaita Sans .ttf font files
under share/fonts/Adwaita/. No binaries or libraries are produced.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class AdwaitaFontsSansConan(ConanFile):
    name = "adwaita-fonts-sans"
    version = "50"
    description = "Adwaita Sans font — a variation of Inter for GNOME"
    license = "OFL-1.1"
    homepage = "https://gitlab.gnome.org/GNOME/adwaita-fonts"
    url = ""  # CI fills this

    package_type = "application"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27: No external Conan dependencies — data-only package
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # No compilation needed — this is a data-only font package
        apply_conandata_patches(self)

    def package(self):
        # Install the sans font files to share/fonts/Adwaita/
        fonts_dir = os.path.join(self.package_folder, "share", "fonts", "Adwaita")
        os.makedirs(fonts_dir, exist_ok=True)

        sans_dir = os.path.join(self.source_folder, "sans")
        for item in os.listdir(sans_dir):
            if item.endswith(".ttf"):
                src = os.path.join(sans_dir, item)
                dst = os.path.join(fonts_dir, item)
                shutil.copy2(src, dst)

        # Install the upstream license file (SIL Open Font License 1.1)
        license_dir = os.path.join(self.package_folder, "share", "licenses", "adwaita-fonts-sans")
        os.makedirs(license_dir, exist_ok=True)
        license_src = os.path.join(self.source_folder, "LICENSE")
        if os.path.isfile(license_src):
            shutil.copy2(license_src, os.path.join(license_dir, "LICENSE"))

    def package_info(self):
        # Data-only package: no libraries to link
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
        # Fonts are installed to share/fonts/Adwaita/
        self.cpp_info.set_property("fontdir", "share/fonts/Adwaita")