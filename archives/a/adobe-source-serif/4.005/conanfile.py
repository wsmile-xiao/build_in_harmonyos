#!/usr/bin/env python3
"""Conan recipe for the Adobe Source Serif 4.005 desktop fonts."""

import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get


class AdobeSourceSerifConan(ConanFile):
    name = "adobe-source-serif"
    version = "4.005"
    description = "Adobe open-source serif typeface family Source Serif 4"
    license = "OFL-1.1"
    homepage = "https://github.com/adobe-fonts/source-serif"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "unknown"
    settings = "os", "arch"

    _source_root = "source-serif-4.005_Desktop"
    _resource_dir = os.path.join("share", "fonts", "adobe-source-serif")

    def export_sources(self):
        pass

    def layout(self):
        pass

    def source(self):
        # The official Desktop zip also contains a top-level __MACOSX folder,
        # so Conan cannot safely strip a single archive root.
        get(self, **self.conan_data["sources"], strip_root=False)

    def build(self):
        apply_conandata_patches(self)
        source_root = os.path.join(self.source_folder, self._source_root)
        static_otf = glob.glob(os.path.join(source_root, "OTF", "*.otf"))
        static_ttf = glob.glob(os.path.join(source_root, "TTF", "*.ttf"))
        variable = glob.glob(os.path.join(source_root, "VAR", "*.*tf"))
        if (len(static_otf), len(static_ttf), len(variable)) != (60, 60, 4):
            raise ConanInvalidConfiguration(
                "Unexpected Source Serif release inventory: expected "
                "60 OTF, 60 TTF and 4 variable fonts"
            )

    def package(self):
        root = os.path.join(self.package_folder, self._resource_dir)
        source_root = os.path.join(self.source_folder, self._source_root)
        copy(self, "*.otf", os.path.join(source_root, "OTF"),
             os.path.join(root, "otf"), keep_path=False)
        copy(self, "*.ttf", os.path.join(source_root, "TTF"),
             os.path.join(root, "ttf"), keep_path=False)
        copy(self, "*.otf", os.path.join(source_root, "VAR"),
             os.path.join(root, "variable"), keep_path=False)
        copy(self, "*.ttf", os.path.join(source_root, "VAR"),
             os.path.join(root, "variable"), keep_path=False)
        copy(self, "LICENSE.md", source_root,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.resdirs = [self._resource_dir]
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []

    def package_id(self):
        self.info.clear()
