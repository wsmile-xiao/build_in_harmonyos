#!/usr/bin/env python3
"""Conan recipe for Source Han Serif OTC 2.003."""

import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, download, mkdir


class AdobeSourceHanSerifOtcConan(ConanFile):
    name = "adobe-source-han-serif-otc"
    version = "2.003"
    description = "Source Han Serif Pan-CJK OpenType Collection fonts"
    license = "OFL-1.1"
    homepage = "https://github.com/adobe-fonts/source-han-serif"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch"

    _source_dir = "OTC"
    _resource_dir = os.path.join("share", "fonts", "adobe-source-han-serif-otc")

    def export_sources(self):
        pass

    def layout(self):
        pass

    def source(self):
        mirror = self.conan_data["sources"]["mirror"]
        font_dir = os.path.join(self.source_folder, self._source_dir)
        mkdir(self, font_dir)
        for font in mirror["files"]:
            download(
                self,
                font["url"],
                os.path.join(font_dir, font["filename"]),
                sha256=font["sha256"],
            )
        license_file = mirror["license"]
        download(
            self,
            license_file["url"],
            os.path.join(self.source_folder, license_file["filename"]),
            sha256=license_file["sha256"],
        )

    def build(self):
        apply_conandata_patches(self)
        expected = {font["filename"] for font in self.conan_data["sources"]["mirror"]["files"]}
        actual = {
            os.path.basename(path)
            for path in glob.glob(os.path.join(self.source_folder, self._source_dir, "*.ttc"))
        }
        if actual != expected:
            missing = sorted(expected - actual)
            unexpected = sorted(actual - expected)
            raise ConanInvalidConfiguration(
                f"Unexpected Source Han Serif OTC inventory; missing={missing}, unexpected={unexpected}"
            )

    def package(self):
        copy(
            self,
            "*.ttc",
            os.path.join(self.source_folder, self._source_dir),
            os.path.join(self.package_folder, self._resource_dir),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE.txt",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.resdirs = [self._resource_dir]
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []

    def package_id(self):
        self.info.clear()
