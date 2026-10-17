#!/usr/bin/env python3
"""Conan recipe for fzy 1.1 — a fast fuzzy text selector for the terminal."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class FzyConan(ConanFile):
    name = "fzy"
    version = "1.1"
    description = "A fast, simple fuzzy text selector for the terminal"
    license = "MIT"
    homepage = "https://github.com/jhawthorn/fzy"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self, src_folder=".")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        cc = "clang"
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        if compilers and isinstance(compilers, dict):
            cc = compilers.get("c", cc)
        self.run(f'make -C "{self.source_folder}" CC="{cc}" -j1')

    def package(self):
        copy(self, "fzy", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "fzy.1", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
