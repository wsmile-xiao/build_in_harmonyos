#!/usr/bin/env python3
"""Conan recipe for Source Han Serif CN 2.003."""

import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get


class AdobeSourceHanSerifCnConan(ConanFile):
    name = "adobe-source-han-serif-cn"
    version = "2.003"
    description = "Source Han Serif Simplified Chinese regional OpenType fonts"
    license = "OFL-1.1"
    homepage = "https://github.com/adobe-fonts/source-han-serif"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch"

    _source_dir = os.path.join("OTF", "SimplifiedChinese")
    _resource_dir = os.path.join("share", "fonts", "adobe-source-han-serif-cn")

    def export_sources(self):
        pass

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=False)

    def build(self):
        apply_conandata_patches(self)
        fonts = glob.glob(os.path.join(self.source_folder, self._source_dir, "*.otf"))
        if len(fonts) != 7:
            raise ConanInvalidConfiguration(
                f"Unexpected Source Han Serif CN inventory: expected 7 OTF files, got {len(fonts)}"
            )

    def package(self):
        copy(self, "*.otf", os.path.join(self.source_folder, self._source_dir),
             os.path.join(self.package_folder, self._resource_dir), keep_path=False)
        copy(self, "LICENSE.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.resdirs = [self._resource_dir]
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []

    def package_id(self):
        self.info.clear()
