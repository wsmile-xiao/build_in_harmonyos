#!/usr/bin/env python3
"""Conan recipe — adw-gtk3 6.5 (GTK3 theme data package).

adw-gtk3 is an unofficial GTK3 port of the libadwaita theme. This is a
pure data/theme package: it installs the pre-built GTK3/GTK4 CSS theme
data (adw-gtk3 and adw-gtk3-dark variants) under share/themes/ plus the
LGPL-2.1 license.

Source: the official upstream v6.5 release tarball
(adw-gtk3v6.5.tar.xz). It already contains the compiled theme data
(gtk-3.0/gtk-4.0 gtk.css / gtk-dark.css / libadwaita-tweaks.css /
libadwaita.css, assets/ and index.theme) built by the upstream CI with
sass. No compilation is needed (sass is unavailable on the OHOS build
host, matching upstream's own distribution model). The release tarball
does not ship a LICENSE, so the LGPL-2.1 license is fetched separately
from the official repository v6.5 tag.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, download, save, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class AdwGtk3Conan(ConanFile):
    name = "adw-gtk3"
    version = "6.5"
    description = "The theme from libadwaita ported to GTK-3"
    license = "LGPL-2.1"
    homepage = "https://github.com/lassekongo83/adw-gtk3"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        theme = self.conan_data["sources"]["theme"]
        get(self, url=theme["url"], sha256=theme["sha256"])
        lic = self.conan_data["sources"]["license"]
        download(self, url=lic["url"], filename="LICENSE", sha256=lic["sha256"])

    def build(self):
        apply_conandata_patches(self)
        # Theme data package: files are pre-built upstream, no compilation needed.
        pass

    def package(self):
        themes_dir = os.path.join(self.package_folder, "share", "themes")
        # Two theme variants: adw-gtk3 (light) and adw-gtk3-dark
        for variant in ("adw-gtk3", "adw-gtk3-dark"):
            src = os.path.join(self.source_folder, variant)
            dst = os.path.join(themes_dir, variant)
            shutil.copytree(src, dst, symlinks=True)
        # License
        lic_dir = os.path.join(self.package_folder, "share", "licenses", "adw-gtk3")
        os.makedirs(lic_dir, exist_ok=True)
        shutil.copy2(os.path.join(self.source_folder, "LICENSE"),
                     os.path.join(lic_dir, "LICENSE"))

    def package_info(self):
        # Theme data package: no cpp_info (no libs/headers/binaries).
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
