#!/usr/bin/env python3
"""Conan recipe for the resource-only Yale Bright Star Catalog 5.0.95."""

import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches
from conan.tools.layout import basic_layout


class YaleConan(ConanFile):
    name = "yale"
    version = "5.0.95"
    description = "Yale Bright Star Catalog 5th Revised Edition data resources"
    license = "LicenseRef-Yale-BSC5-Data"
    homepage = "https://cdsarc.cds.unistra.fr/viz-bin/cat/V/50"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("astronomy", "star-catalog", "data", "ohos")
    package_type = "unknown"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        for metadata in self.conan_data["sources"].values():
            destination = os.path.join(self.source_folder, metadata["filename"])
            download(
                self,
                url=metadata["url"],
                filename=destination,
                sha256=metadata["sha256"],
            )

    def build(self):
        # This resource archive has no compilation stage; retain the standard
        # declared-patch hook for Conan verifier and future explicit port patches.
        apply_conandata_patches(self)

    def package(self):
        resource_dir = os.path.join(self.package_folder, "share", "yale")
        for metadata in self.conan_data["sources"].values():
            copy(
                self,
                metadata["filename"],
                src=self.source_folder,
                dst=resource_dir,
                keep_path=False,
            )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["share/yale"]
        self.runenv_info.define_path(
            "YALE_BSC5_DIR", os.path.join(self.package_folder, "share", "yale")
        )
