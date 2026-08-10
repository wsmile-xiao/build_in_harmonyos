#!/usr/bin/env python3
"""Conan recipe — adobe-source-code-pro 2.042u (font data package).

Source Code Pro is a pure font data package: the upright .ttf files are
pre-built upstream (Adobe release 2.042R-u, i.e. Upright fonts version 2.042).
No compilation is needed.
"""

from conan import ConanFile
from conan.tools.files import copy, get, export_conandata_patches, apply_conandata_patches
import os


class AdobeSourceCodeProConan(ConanFile):
    name = "adobe-source-code-pro"
    version = "2.042u"
    description = "Source Code Pro, Adobe's open-source monospaced typeface for coding"
    license = "OFL-1.1"
    homepage = "https://github.com/adobe-fonts/source-code-pro"

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
        """Install 7 pre-built upright TTF files to share/fonts/SourceCodePro/
        and the OFL-1.1 license to licenses/."""
        font_dir = os.path.join(self.package_folder, "share", "fonts", "SourceCodePro")
        # Upright faces only (2.042u); exclude *It.ttf (italic faces are a separate 1.062 release)
        copy(self, "SourceCodePro-*.ttf",
             os.path.join(self.source_folder, "TTF"), font_dir,
             keep_path=False, excludes=["*It.ttf"])
        copy(self, "LICENSE.md", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Font data package — no libs/includes; declare font resource dir
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share/fonts/SourceCodePro"]
        self.user_info.font_dir = "share/fonts/SourceCodePro"
