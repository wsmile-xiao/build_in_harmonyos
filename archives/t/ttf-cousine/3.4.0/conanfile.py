#!/usr/bin/env python3
"""Conan recipe for ttf-cousine 3.4.0 (font package).

This is a pure font resource package — no compilation needed.
The package bundles 12 Nerd Font patched Cousine TTF files.

License: Apache-2.0 (Cousine by Steve Matteson, Nerd Fonts patches by Ryan L).
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, get


class TtfcousineConan(ConanFile):
    name = "ttf-cousine"
    version = "3.4.0"
    description = "Cousine Nerd Font — monospace font with programming glyphs"
    license = "Apache-2.0"
    homepage = "https://github.com/ryanoasis/nerd-fonts"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Font resource package — no compilation, no libs, no binaries.
    # Conan 2.30 valid package_type list does not include "font", so we use
    # "unknown" and declare the font directory via cpp_info.resdirs.
    package_type = "unknown"
    # R32: os judgement must be in ("Linux", "OHOS"). Font package is
    # architecture-independent but kept settings for recipe compatibility.
    settings = "os", "arch"

    # Font resource directory relative to package_folder
    _font_subdir = os.path.join("share", "fonts", "truetype", "cousine-nerd")

    def export_sources(self):
        # No patches for font packages
        pass

    def layout(self):
        # Font packages use basic layout — no build dir needed
        pass

    def source(self):
        # Download the Cousine Nerd Font release zip and extract.
        # Cousine.zip flattens all .ttf into the archive root (no wrapping
        # dir), so strip_root must be False.
        get(self, **self.conan_data["sources"], strip_root=False)
        # Font packages carry no patches; apply_conandata_patches is a no-op
        # here but called for recipe uniformity with the SKILL framework.
        apply_conandata_patches(self)

    def build(self):
        # Font packages require no compilation — just verify TTF files exist
        ttf_files = glob.glob(os.path.join(self.source_folder, "*.ttf"))
        if not ttf_files:
            raise ConanException("No .ttf files found in source directory")
        # Cousine Nerd Font ships 12 TTF files (4 styles × 3 variants)
        if len(ttf_files) < 12:
            raise ConanException(
                f"Expected at least 12 TTF files, found {len(ttf_files)}"
            )

    def package(self):
        # Install all TTF files into share/fonts/truetype/cousine-nerd/
        dest_font_dir = os.path.join(self.package_folder, self._font_subdir)
        copy(self, "*.ttf", self.source_folder, dest_font_dir)
        # Also copy LICENSE for redistribution compliance
        copy(self, "LICENSE.txt", self.source_folder, dest_font_dir)

    def package_info(self):
        # R38: Font package — no libs, no bindirs, no commands.json
        # resdirs points consumers (fc-list, fontconfig) at the font directory
        self.cpp_info.resdirs = [self._font_subdir]
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
