#!/usr/bin/env python3
"""Conan recipe for carburetor 4.5.1.

Carburetor is a GTK/libadwaita frontend for the Tractor torrent anonymity project.
This is a pure Python application using meson for packaging (meson.build created as patch).
No C/C++ compilation occurs — meson only installs Python modules, data files, and an entry point script.

Homepage: https://framagit.org/tractor/carburetor
License: GPL-3.0
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain


class CarburetorConan(ConanFile):
    name = "carburetor"
    version = "4.5.1"
    description = "GTK/libadwaita frontend for the Tractor torrent anonymity project"
    license = "GPL-3.0"
    homepage = "https://framagit.org/tractor/carburetor"
    url = "https://framagit.org/tractor/carburetor"

    # Pure Python application — produces an executable entry point script
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Manual meson layout (meson_layout not available in OHOS-adapted conan)
        self.folders.build = "build"
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        # Application: declares the binary directory for the entry point script
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
