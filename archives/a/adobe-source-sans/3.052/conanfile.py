#!/usr/bin/env python3
"""Conan recipe — adobe-source-sans 3.052 (font data package).

Source Sans 3 is a pure font data package: the .ttf files are pre-built
upstream (Adobe release 3.052R). No compilation is needed.
"""

from conan import ConanFile
from conan.tools.files import copy, get, export_conandata_patches, apply_conandata_patches
import os


class AdobeSourceSansConan(ConanFile):
    name = "adobe-source-sans"
    version = "3.052"
    description = "Source Sans 3, Adobe's open-source sans-serif typeface for UI environments"
    license = "OFL-1.1"
    homepage = "https://github.com/adobe-fonts/source-sans"

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
        """Install 14 pre-built TTF files + OFL license to share/fonts/SourceSans3/."""
        font_dir = os.path.join(self.package_folder, "share", "fonts", "SourceSans3")
        copy(self, "SourceSans3-*.ttf",
             os.path.join(self.source_folder, "TTF"), font_dir,
             keep_path=False)
        copy(self, "LICENSE.md", self.source_folder, font_dir, keep_path=False)

    def package_info(self):
        # Font data package — no cpp_info needed
        pass
