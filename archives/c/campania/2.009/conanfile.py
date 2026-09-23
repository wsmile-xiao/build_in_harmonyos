#!/usr/bin/env python3
"""Conan recipe for the Campania music-theory font resource package."""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class CampaniaConan(ConanFile):
    name = "campania"
    version = "2.009"
    description = "Campania font for Roman numeral analysis in music theory"
    license = "OFL-1.1"
    homepage = "https://github.com/MarcSabatella/Campania"
    url = "https://archive.linux.duke.edu/pub/debian/pool/main/c/campania/campania_2.009.orig.tar.gz"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Campania is a prebuilt font resource package; there is no code build.
        apply_conandata_patches(self)

    def package(self):
        fonts_dir = os.path.join(self.package_folder, "fonts")
        docs_dir = os.path.join(self.package_folder, "licenses")
        features_dir = os.path.join(self.package_folder, "features")
        copy(self, "*.otf", src=self.source_folder, dst=fonts_dir, keep_path=False)
        copy(self, "*.ttf", src=self.source_folder, dst=fonts_dir, keep_path=False)
        copy(self, "*.woff", src=self.source_folder, dst=fonts_dir, keep_path=False)
        copy(self, "LICENSE", src=self.source_folder, dst=docs_dir, keep_path=False)
        copy(self, "README.md", src=self.source_folder, dst=docs_dir, keep_path=False)
        copy(self, "*.fea", src=self.source_folder, dst=features_dir, keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["fonts"]
