#!/usr/bin/env python3
"""Conan recipe — ciso 1.0 (Makefile, application)"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CisoConan(ConanFile):
    name = "ciso"
    version = "1.0"
    description = "PSP ISO image compression/decompression tool"
    license = "GPL-2.0"
    homepage = "https://sourceforge.net/projects/ciso/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, not shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")

        self.run(f'make CC="{cc}" LD="{cc}" -j1', cwd=self.source_folder)

    def package(self):
        copy(self, "ciso", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
