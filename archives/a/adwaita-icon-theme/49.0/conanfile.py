#!/usr/bin/env python3
"""Conan recipe — adwaita-icon-theme 49.0 (icon theme, data-only, meson).

adwaita-icon-theme is the GNOME project's official icon theme.
It is a data-only meson project: no C/C++ compilation, only installation
of icon files (PNG/SVG), cursor symlinks, a pkg-config .pc file, and licenses.

The only patch makes gtk-update-icon-cache optional (not available on OHOS).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class AdwaitaIconThemeConan(ConanFile):
    name = "adwaita-icon-theme"
    version = "49.0"
    description = "A collection of icons used as the basis for GNOME themes"
    license = "CC-BY-SA-3.0, LGPL-3.0-only"
    homepage = "https://gitlab.gnome.org/GNOME/adwaita-icon-theme"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "unknown"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        # Pure data package — all configurations share the same binary
        self.info.clear()

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

        icons_dir = os.path.join(self.package_folder, "share", "icons")
        self.buildenv_info.define("ADWAITA_ICON_THEME_DIR",
                                  os.path.join(icons_dir, "Adwaita"))
