#!/usr/bin/env python3
"""Conan recipe — asahi-audio v3.4 (makefile, pure data package)"""

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AsahiAudioConan(ConanFile):
    name = "asahi-audio"
    version = "v3.4"
    description = "Apple Silicon Linux audio DSP configuration package"
    license = "MIT"
    homepage = "https://github.com/AsahiLinux/asahi-audio"

    package_type = "unknown"
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Generate alias JSON files using sed (no C/C++ compilation)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install data files: wav/json/lua/conf to share/asahi-audio/, share/wireplumber/, share/pipewire/
        self.run(f"make install DESTDIR={self.package_folder} PREFIX=/", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.libs = []
