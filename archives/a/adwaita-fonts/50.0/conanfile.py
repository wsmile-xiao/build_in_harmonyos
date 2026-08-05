#!/usr/bin/env python3
"""Conan recipe — adwaita-fonts 50.0 (font data package).

This is a pure font data package. The .ttf files are pre-built upstream;
no compilation is needed. Meson is only used for install_data().
"""

from conan import ConanFile
from conan.tools.files import copy, get, save, export_conandata_patches, apply_conandata_patches
import os


class AdwaitaFontsConan(ConanFile):
    name = "adwaita-fonts"
    version = "50.0"
    description = "Adwaita fonts (Sans + Mono) for GNOME desktop"
    license = "OFL-1.1"
    homepage = "https://gitlab.gnome.org/GNOME/adwaita-fonts"

    package_type = "application"

    settings = "os", "arch"

    def requirements(self):
        pass

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Font data package: .ttf files are pre-built upstream, no compilation needed.
        pass

    def package(self):
        """Install 6 pre-built .ttf files to share/fonts/Adwaita/."""
        font_dir = os.path.join(self.package_folder, "share", "fonts", "Adwaita")
        copy(self, "AdwaitaMono-*.ttf",
             os.path.join(self.source_folder, "mono"), font_dir,
             keep_path=False)
        copy(self, "AdwaitaSans-*.ttf",
             os.path.join(self.source_folder, "sans"), font_dir,
             keep_path=False)

    def package_info(self):
        # Font data package — no cpp_info needed
        pass