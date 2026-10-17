#!/usr/bin/env python3
"""Conan recipe for adwaita-fonts-mono 50.0 (font package).

This is a pure font resource package — no compilation needed.
The package bundles 4 Adwaita Mono TTF files (Bold, BoldItalic, Italic, Regular).

Only Mono fonts are installed; Sans fonts from upstream are excluded
per the package name "adwaita-fonts-mono". See notes.md for details.

License: SIL Open Font License 1.1
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, get, export_conandata_patches
from conan.tools.layout import basic_layout


class AdwaitaFontsMonoConan(ConanFile):
    name = "adwaita-fonts-mono"
    version = "50"
    description = "Adwaita Mono — monospace font from the GNOME Adwaita font family"
    license = "OFL-1.1"
    homepage = "https://gitlab.gnome.org/GNOME/adwaita-fonts"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Font resource package — no compilation, no libs, no binaries.
    package_type = "unknown"

    # Font packages are architecture-independent; no settings needed.
    # R32: skipped for data-only packages (no compilation, no settings.os check).

    # Font resource directory relative to package_folder
    _font_subdir = os.path.join("share", "fonts", "AdwaitaMono")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # Font packages require no compilation — just verify Mono TTF files exist
        mono_dir = os.path.join(self.source_folder, "mono")
        ttf_files = glob.glob(os.path.join(mono_dir, "AdwaitaMono-*.ttf"))
        if not ttf_files:
            raise ConanException("No AdwaitaMono TTF files found in source directory")
        if len(ttf_files) < 4:
            raise ConanException(
                f"Expected 4 AdwaitaMono TTF files, found {len(ttf_files)}: {ttf_files}"
            )

    def package(self):
        # Install Mono TTF files into share/fonts/AdwaitaMono/
        mono_dir = os.path.join(self.source_folder, "mono")
        dest_font_dir = os.path.join(self.package_folder, self._font_subdir)
        copy(self, "AdwaitaMono-*.ttf", mono_dir, dest_font_dir)

    def package_info(self):
        # Font package — no libs, no bindirs, no commands.json
        # resdirs points consumers (fontconfig, fc-list) at the font directory
        self.cpp_info.resdirs = [self._font_subdir]
        self.cpp_info.libs = []