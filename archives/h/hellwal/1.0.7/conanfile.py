#!/usr/bin/env python3
"""Conan recipe for hellwal — a fast, extensible palette generator (Makefile)."""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class HellwalConan(ConanFile):
    name = "hellwal"
    version = "1.0.7"
    description = "Fast, extensible palette generator — generates terminal color schemes from images or theme files"
    license = "MIT"
    homepage = "https://github.com/danihek/hellwal"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, never from raw shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")

        # R9: Always use -j1
        self.run(f"make CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        # hellwal produces a single executable binary
        copy(self, "hellwal", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
