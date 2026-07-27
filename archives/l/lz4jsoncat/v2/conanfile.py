#!/usr/bin/env python3
"""Conan recipe — lz4jsoncat v2 (Mozilla lz4 JSON decompressor CLI tool).

Build system: pure Makefile (no configure script).
R38: includes lz4jsoncat CLI tool → commands.json required.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Lz4JsoncatConan(ConanFile):
    name = "lz4jsoncat"
    version = "v2"
    description = "lz4json decompressor"
    license = "GPL-2.0"
    homepage = "https://github.com/andikleen/lz4json"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lz4/1.10.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Get lz4 package folder (has include/ and lib/ subdirs)
        lz4 = self.dependencies["lz4"]
        lz4_prefix = lz4.package_folder
        # CC is set by Conan's build environment from the profile
        # R9: Always use -j1
        self.run(
            f"make PREFIX={lz4_prefix} -j1",
            cwd=self.source_folder,
        )

    def package(self):
        # Copy the executable to bin/
        copy(self, "lz4jsoncat", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
